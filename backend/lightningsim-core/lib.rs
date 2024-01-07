mod axi_interface;
mod builder;
mod edge;
mod fifo;
mod node;

use std::{cmp, fmt, iter};

use axi_interface::{AxiAddress, AxiAddressRange, AxiGenericIo, AxiInterfaceIo};
use bitvec::bitvec;
use builder::SimulationBuilder;
use fifo::{FifoId, FifoIo};
use pyo3::{exceptions::PyValueError, prelude::*};
use rustc_hash::FxHashMap;

use crate::{
    axi_interface::{AxiInterface, AxiInterfaceIoNodes},
    edge::Edge,
    fifo::{Fifo, FifoIoNodes},
    node::{NodeIndex, NodeWithDelay},
};

const SAXI_STATUS_UPDATE_OVERHEAD: ClockCycle = 5;
const SAXI_STATUS_READ_DELAY: ClockCycle = 5;
const SAXI_STATUS_WRITE_DELAY: ClockCycle = 6;

pub type ClockCycle = u64;
pub type SimulationStage = u32;
pub(crate) type SimulationResult = Result<Vec<ClockCycle>, SimulationError>;

#[pyclass]
#[derive(Clone)]
pub struct CompiledSimulation {
    pub(crate) graph: SimulationGraph,
    pub(crate) top_module: CompiledModule,
    pub(crate) fifo_nodes: FxHashMap<Fifo, FifoIoNodes>,
    pub(crate) axi_interface_nodes: FxHashMap<AxiInterface, AxiInterfaceIoNodes>,
    pub(crate) end_node: NodeIndex,
}

#[derive(Clone)]
pub(crate) struct SimulationGraph {
    pub node_offsets: Box<[usize]>,
    pub edges: Box<[Edge]>,
}

#[derive(Clone)]
pub(crate) struct CompiledModule {
    pub name: String,
    /// The start node + delay of this module execution.
    pub start: NodeWithDelay,
    /// The end node + delay of this module execution.
    pub end: NodeWithDelay,
    pub submodules: Box<[CompiledModule]>,
    pub inherit_ap_continue: bool,
}

#[derive(Clone, Debug)]
pub(crate) enum SimulationError {
    DeadlockDetected,
    FifoDepthNotProvided(FifoId),
    AxiDelayNotProvided(AxiAddress),
}

#[derive(Clone, FromPyObject)]
pub struct SimulationParameters {
    fifo_depths: FxHashMap<FifoId, Option<usize>>,
    axi_delays: FxHashMap<AxiAddress, ClockCycle>,
    ap_ctrl_chain_top_port_count: Option<u32>,
}

#[pyclass]
#[derive(Clone)]
pub struct Simulation {
    #[pyo3(get)]
    top_module: SimulatedModule,
    #[pyo3(get)]
    fifo_io: FxHashMap<Fifo, FifoIo>,
    #[pyo3(get)]
    axi_io: FxHashMap<AxiInterface, AxiInterfaceIo>,
}

#[pyclass]
#[derive(Clone)]
pub struct SimulatedModule {
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    start: ClockCycle,
    #[pyo3(get)]
    end: ClockCycle,
    #[pyo3(get)]
    submodules: Vec<SimulatedModule>,
}

impl CompiledSimulation {
    fn resolve(&self, parameters: &SimulationParameters) -> SimulationResult {
        let node_count = self.graph.node_offsets.len();
        let mut node_cycles = vec![0; node_count];
        let mut visited = bitvec![0; node_count];
        let mut visiting = bitvec![0; node_count];
        let mut stack = vec![Visit {
            node: self.end_node,
            parent_visit: 0,
            parent_delay: 0,
            preorder: true,
        }];

        while let Some(Visit {
            node,
            parent_visit,
            parent_delay,
            preorder,
        }) = stack.pop()
        {
            let node_usize: usize = node.try_into().unwrap();
            if preorder {
                if visited[node_usize] {
                    let parent_visit_usize: usize = parent_visit.try_into().unwrap();
                    if let Some(Visit {
                        node: parent_node, ..
                    }) = stack.get(parent_visit_usize)
                    {
                        let parent_usize: usize = (*parent_node).try_into().unwrap();
                        node_cycles[parent_usize] = cmp::max(
                            node_cycles[parent_usize],
                            node_cycles[node_usize] + parent_delay,
                        );
                    }
                    continue;
                }
                if visiting[node_usize] {
                    return Err(SimulationError::DeadlockDetected);
                }

                visiting.set(node_usize, true);

                let visit_index = stack.len().try_into().unwrap();
                stack.push(Visit {
                    node,
                    parent_visit,
                    parent_delay,
                    preorder: false,
                });

                for edge in self.graph.in_edges(node_usize) {
                    if let Some(edge) = edge.resolve(self, parameters)? {
                        stack.push(Visit {
                            node: edge.node,
                            parent_visit: visit_index,
                            parent_delay: edge.delay,
                            preorder: true,
                        });
                    }
                }
            } else {
                visiting.set(node_usize, false);
                visited.set(node_usize, true);

                let parent_visit_usize: usize = parent_visit.try_into().unwrap();
                if let Some(Visit {
                    node: parent_node, ..
                }) = stack.get(parent_visit_usize)
                {
                    let parent_usize: usize = (*parent_node).try_into().unwrap();
                    node_cycles[parent_usize] = cmp::max(
                        node_cycles[parent_usize],
                        node_cycles[node_usize] + parent_delay,
                    );
                }
            }
        }

        Ok(node_cycles)
    }
}

#[pymethods]
impl CompiledSimulation {
    fn execute(&self, parameters: SimulationParameters) -> PyResult<Simulation> {
        let node_cycles = self.resolve(&parameters)?;
        let top_module = SimulatedModule::new(
            &node_cycles,
            &self.top_module,
            parameters.ap_ctrl_chain_top_port_count.into(),
        );
        let fifo_io = self
            .fifo_nodes
            .iter()
            .map(|(fifo, nodes)| (*fifo, FifoIo::new(nodes, &node_cycles)))
            .collect();
        let axi_io = self
            .axi_interface_nodes
            .iter()
            .map(|(interface, nodes)| (*interface, AxiInterfaceIo::new(nodes, &node_cycles)))
            .collect();
        Ok(Simulation {
            top_module,
            fifo_io,
            axi_io,
        })
    }

    fn node_count(&self) -> usize {
        self.graph.node_offsets.len()
    }

    fn edge_count(&self) -> usize {
        self.graph.edges.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "CompiledSimulation(graph={:?}, end_node={:?})",
            self.graph, self.end_node
        )
    }
}

impl SimulationGraph {
    fn in_edges(&self, node: usize) -> &[Edge] {
        let start = self.node_offsets[node];
        let end = self
            .node_offsets
            .get(node + 1)
            .copied()
            .unwrap_or(self.edges.len());
        &self.edges[start..end]
    }
}

impl fmt::Debug for SimulationGraph {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_map()
            .entries(
                self.node_offsets
                    .iter()
                    .copied()
                    .zip(
                        self.node_offsets[1..]
                            .iter()
                            .copied()
                            .chain(iter::once(self.edges.len())),
                    )
                    .enumerate()
                    .map(|(node, (start, end))| (node, &self.edges[start..end])),
            )
            .finish()
    }
}

impl SimulationParameters {
    pub(crate) fn get_fifo_depth(&self, fifo: Fifo) -> Result<Option<usize>, SimulationError> {
        self.fifo_depths
            .get(&fifo.id)
            .copied()
            .ok_or(SimulationError::FifoDepthNotProvided(fifo.id))
    }

    pub(crate) fn get_axi_delay(
        &self,
        interface: AxiInterface,
    ) -> Result<ClockCycle, SimulationError> {
        let delay = self
            .axi_delays
            .get(&interface.address)
            .copied()
            .ok_or(SimulationError::AxiDelayNotProvided(interface.address))?;
        Ok(cmp::max(delay, 1))
    }
}

impl SimulatedModule {
    fn new(node_cycles: &[ClockCycle], module: &CompiledModule, ap_continue: ApContinue) -> Self {
        let start = module.start.resolve(node_cycles);
        let ap_done = module.end.resolve(node_cycles);
        let ap_continue = if module.inherit_ap_continue {
            ap_continue
        } else {
            ApContinue::NotApplicable
        };
        let end = match ap_continue {
            ApContinue::NotApplicable => ap_done,
            ApContinue::TopLevel { num_parameters } => {
                // ap_continue is asserted by AESL_axi_slave_control some cycles after it reads
                // ap_done. It checks ap_done every few cycles; we first
                // calculate how often it performs this check.

                // AESL_axi_slave_control is structured as a series of repeated sequential
                // processes. They are:
                // - update_status (process_num = 0), which reads ap_done and writes ap_continue
                // - write_* (process_num = 1, ..., N), which write the top-level parameters
                // - write_start (process_num = N + 1), which writes ap_start(?)
                // Each contributes a cycle to the loop, except update_status, which takes
                // SAXI_STATUS_UPDATE_OVERHEAD cycles.
                let num_parameters: ClockCycle = num_parameters.try_into().unwrap();
                let saxi_status_read_interval = SAXI_STATUS_UPDATE_OVERHEAD + num_parameters + 1;

                // The first status read occurs at cycle SAXI_STATUS_READ_DELAY after ap_start,
                // so we calculate when the update_status process will first read ap_done.
                let saxi_status_ap_done_read_cycle =
                    (ap_done + saxi_status_read_interval - SAXI_STATUS_READ_DELAY - 1)
                        / saxi_status_read_interval
                        * saxi_status_read_interval
                        + SAXI_STATUS_READ_DELAY;

                // ap_continue will be asserted SAXI_STATUS_WRITE_DELAY cycles after that.
                saxi_status_ap_done_read_cycle + SAXI_STATUS_WRITE_DELAY
            }
            ApContinue::Propagated(ap_continue) => ap_continue,
        };
        let ap_continue = match ap_continue {
            ApContinue::TopLevel { .. } => ApContinue::Propagated(end),
            _ => ap_continue,
        };

        SimulatedModule {
            name: module.name.clone(),
            start,
            end,
            submodules: module
                .submodules
                .iter()
                .map(|submodule| SimulatedModule::new(node_cycles, submodule, ap_continue))
                .collect(),
        }
    }
}

impl fmt::Display for SimulationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DeadlockDetected => write!(f, "deadlock detected"),
            Self::FifoDepthNotProvided(fifo_id) => {
                write!(f, "no depth provided for FIFO with id {}", fifo_id)
            }
            Self::AxiDelayNotProvided(interface_address) => write!(
                f,
                "no delay provided for AXI interface with address {:#010x}",
                interface_address
            ),
        }
    }
}

impl From<SimulationError> for PyErr {
    fn from(value: SimulationError) -> Self {
        PyValueError::new_err(value.to_string())
    }
}

struct Visit {
    node: NodeIndex,
    parent_visit: NodeIndex,
    parent_delay: ClockCycle,
    preorder: bool,
}

#[derive(Clone, Copy)]
enum ApContinue {
    NotApplicable,
    TopLevel { num_parameters: u32 },
    Propagated(ClockCycle),
}

impl From<Option<u32>> for ApContinue {
    fn from(value: Option<u32>) -> Self {
        match value {
            Some(num_parameters) => ApContinue::TopLevel { num_parameters },
            None => ApContinue::NotApplicable,
        }
    }
}

#[pymodule]
fn _core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<SimulationBuilder>()?;
    m.add_class::<CompiledSimulation>()?;
    m.add_class::<Simulation>()?;
    m.add_class::<SimulatedModule>()?;
    m.add_class::<Fifo>()?;
    m.add_class::<FifoIo>()?;
    m.add_class::<AxiInterface>()?;
    m.add_class::<AxiInterfaceIo>()?;
    m.add_class::<AxiGenericIo>()?;
    m.add_class::<AxiAddressRange>()?;
    Ok(())
}
