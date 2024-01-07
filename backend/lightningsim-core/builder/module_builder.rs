use rustc_hash::FxHashMap;
use slab::Slab;

use pyo3::{exceptions::PyValueError, prelude::*};

use crate::{axi_interface::AxiInterface, node::NodeWithDelay, ClockCycle, CompiledModule};

use super::{axi_rctl::AxiRctl, event::Event, node::NodeTime};

pub type ModuleKey = usize;

#[derive(Clone, Default)]
pub struct ModuleBuilder {
    committed: Vec<Option<CommittedModule>>,
    uncommitted: Slab<UncommittedModule>,
}

impl ModuleBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert_module(
        &mut self,
        parent: Option<ModuleKey>,
        start_delay: ClockCycle,
        inherit_ap_continue: bool,
    ) -> ModuleKey {
        let index = self.committed.len();
        let name_placeholder = String::new();
        self.committed.push(None);
        if let Some(parent) = parent {
            self.uncommitted[parent].submodule_indices.push(index);
        }
        self.uncommitted.insert(UncommittedModule::new(
            index,
            name_placeholder,
            start_delay,
            inherit_ap_continue,
        ))
    }

    pub fn update_module_name(&mut self, key: ModuleKey, name: String) {
        self.uncommitted[key].name = name;
    }

    pub fn update_module_end(&mut self, key: ModuleKey, end: NodeTime) {
        self.uncommitted[key].end = end;
    }

    pub fn defer_event(&mut self, key: ModuleKey, delay: ClockCycle, event: Event) {
        self.uncommitted[key].events.push((delay, event));
    }

    pub fn get_axi_rctl_mut(&mut self, key: ModuleKey) -> &mut FxHashMap<AxiInterface, AxiRctl> {
        &mut self.uncommitted[key].axi_rctl
    }

    /// Given a module key and the parent node of the module with that key,
    /// commit the module.
    ///
    /// Returns an iterator over nodes and events that were deferred on this
    /// module.
    pub fn commit_module(
        &mut self,
        key: ModuleKey,
        parent: NodeWithDelay,
    ) -> impl Iterator<Item = (NodeWithDelay, Event)> {
        let UncommittedModule {
            index,
            name,
            start_delay,
            end,
            inherit_ap_continue,
            submodule_indices,
            events,
            axi_rctl: _,
        } = self.uncommitted.remove(key);
        let start = parent + start_delay;
        let end = end.resolve(start);
        self.committed[index] = Some(CommittedModule {
            name,
            start,
            end,
            inherit_ap_continue,
            submodule_indices,
        });
        events
            .into_iter()
            .map(move |(position, event)| (start + position, event))
    }

    fn try_resolve_module(&mut self, module: CommittedModule) -> Option<CompiledModule> {
        let CommittedModule {
            name,
            start,
            end,
            inherit_ap_continue,
            submodule_indices,
        } = module;
        let submodules: Option<_> = submodule_indices
            .into_iter()
            .map(|index| {
                self.committed[index]
                    .take()
                    .and_then(|submodule| self.try_resolve_module(submodule))
            })
            .collect();
        submodules.map(|submodules| CompiledModule {
            name,
            start,
            end,
            submodules,
            inherit_ap_continue,
        })
    }
}

impl TryFrom<ModuleBuilder> for CompiledModule {
    type Error = PyErr;

    fn try_from(mut value: ModuleBuilder) -> Result<Self, Self::Error> {
        let top_module = value.committed.first_mut().ok_or_else(|| {
            PyValueError::new_err("kernel did not run. Did the testbench call it?")
        })?;
        let top_module = top_module
            .take()
            .ok_or_else(|| PyValueError::new_err("top module was not committed"))?;
        value
            .try_resolve_module(top_module)
            .ok_or_else(|| PyValueError::new_err("not all modules were committed"))
    }
}

#[derive(Clone)]
struct CommittedModule {
    name: String,
    start: NodeWithDelay,
    end: NodeWithDelay,
    inherit_ap_continue: bool,
    submodule_indices: Vec<usize>,
}

#[derive(Clone)]
struct UncommittedModule {
    index: usize,
    name: String,
    start_delay: ClockCycle,
    end: NodeTime,
    inherit_ap_continue: bool,
    submodule_indices: Vec<usize>,
    events: Vec<(ClockCycle, Event)>,
    axi_rctl: FxHashMap<AxiInterface, AxiRctl>,
}

impl UncommittedModule {
    pub fn new(
        index: usize,
        name: String,
        start_delay: ClockCycle,
        inherit_ap_continue: bool,
    ) -> Self {
        Self {
            index,
            name,
            start_delay,
            end: NodeTime::RelativeToStart(0),
            inherit_ap_continue,
            submodule_indices: Vec::new(),
            events: Vec::new(),
            axi_rctl: FxHashMap::default(),
        }
    }
}
