mod axi_builder;
mod edge_builder;
mod event;
mod fifo_builder;
mod frame;
mod module_builder;
mod node;
mod tee;

use std::mem;

use axi_builder::{
    AxiBuilder, AxiRequestRange, InsertedAxiRead, InsertedAxiReadReq, InsertedAxiWrite,
    InsertedAxiWriteReq, InsertedAxiWriteResp,
};
use edge_builder::{EdgeBuilder, IncompleteEdgeType};
use event::Event;
use fifo_builder::{FifoBuilder, InsertedFifoRead, InsertedFifoWrite};
use frame::StackFrame;
use module_builder::ModuleBuilder;
use node::{NodeTime, UncommittedNode};

use pyo3::{exceptions::PyValueError, prelude::*};
use rustc_hash::FxHashMap;

use crate::{
    axi_interface::{AxiInterface, AxiInterfaceIoNodes},
    edge::Edge,
    fifo::{Fifo, FifoIoNodes},
    node::{NodeIndex, NodeWithDelay},
    simulation::{ClockCycle, CompiledSimulation, SimulationStage},
};

#[pyclass]
#[derive(Clone)]
pub struct SimulationBuilder {
    edge_builder: EdgeBuilder,
    modules_builder: ModuleBuilder,
    fifo_builders: FxHashMap<Fifo, FifoBuilder>,
    axi_builders: FxHashMap<AxiInterface, AxiBuilder>,
    stack: Vec<StackFrame>,
    start_node: NodeIndex,
    end_node: Option<NodeIndex>,
}

#[pymethods]
impl SimulationBuilder {
    #[new]
    pub fn new() -> Self {
        let mut edge_builder = EdgeBuilder::new();
        let start_node = edge_builder.insert_node();
        let mut modules_builder = ModuleBuilder::new();
        let top_module_key = modules_builder.insert_module(None, 0, true);
        let top_module_start_edge = edge_builder.insert_edge(IncompleteEdgeType::ControlFlow);
        edge_builder.update_source(
            top_module_start_edge,
            NodeWithDelay {
                node: start_node,
                delay: 0,
            },
        );
        let top_frame = StackFrame::new(top_module_key, 0, top_module_start_edge);
        SimulationBuilder {
            edge_builder,
            modules_builder,
            fifo_builders: FxHashMap::default(),
            axi_builders: FxHashMap::default(),
            stack: vec![top_frame],
            start_node,
            end_node: None,
        }
    }

    pub fn add_fifo_write(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        fifo: Fifo,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedFifoWrite { index, raw_edge } =
            self.fifo_builders.entry(fifo).or_default().insert_write();
        let raw_edge = raw_edge.unwrap_or_else(|err| {
            let new_edge = self
                .edge_builder
                .insert_edge(IncompleteEdgeType::FifoRaw(fifo));
            err.provide_next(new_edge);
            new_edge
        });
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::FifoWrite {
                fifo,
                index,
                raw_edge,
            },
        );
    }

    pub fn add_fifo_read(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        fifo: Fifo,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedFifoRead { index, raw_edge } =
            self.fifo_builders.entry(fifo).or_default().insert_read();
        let raw_edge = raw_edge.unwrap_or_else(|err| {
            let new_edge = self
                .edge_builder
                .insert_edge(IncompleteEdgeType::FifoRaw(fifo));
            err.provide_next(new_edge);
            new_edge
        });
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::FifoRead {
                fifo,
                index,
                raw_edge,
            },
        );
    }

    pub fn add_axi_readreq(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        interface: AxiInterface,
        request: AxiRequestRange,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedAxiReadReq {
            index,
            read_edge: read_edge_needed,
            voided_rctl_edges,
        } = self
            .axi_builders
            .entry(interface)
            .or_default()
            .insert_readreq(request);
        let read_edge = self
            .edge_builder
            .insert_edge(IncompleteEdgeType::AxiRead(interface));
        read_edge_needed.provide(read_edge);
        for rctl_edge in voided_rctl_edges {
            self.edge_builder.void_destination(rctl_edge);
        }
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::AxiReadRequest {
                interface,
                index,
                read_edge,
            },
        );
    }

    pub fn add_axi_writereq(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        interface: AxiInterface,
        request: AxiRequestRange,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedAxiWriteReq { index } = self
            .axi_builders
            .entry(interface)
            .or_default()
            .insert_writereq(request);
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::AxiWriteRequest { interface, index },
        );
    }

    pub fn add_axi_read(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        interface: AxiInterface,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedAxiRead {
            index,
            read_edge,
            rctl_out_edge,
            rctl_in_edge,
        } = self
            .axi_builders
            .entry(interface)
            .or_default()
            .insert_read();
        let rctl_out_edge = rctl_out_edge.map(|edge_needed| {
            let new_edge = self
                .edge_builder
                .insert_edge(IncompleteEdgeType::AxiRctl(interface));
            edge_needed.provide(new_edge);
            new_edge
        });
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::AxiRead {
                interface,
                index,
                read_edge,
                rctl_out_edge,
                rctl_in_edge,
            },
        );
    }

    pub fn add_axi_write(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        interface: AxiInterface,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedAxiWrite {
            index,
            writeresp_edge,
        } = self
            .axi_builders
            .entry(interface)
            .or_default()
            .insert_write();
        let writeresp_edge = writeresp_edge.map(|edge_needed| {
            let new_edge = self
                .edge_builder
                .insert_edge(IncompleteEdgeType::AxiWriteResp(interface));
            edge_needed.provide(new_edge);
            new_edge
        });
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::AxiWrite {
                interface,
                index,
                writeresp_edge,
            },
        );
    }

    pub fn add_axi_writeresp(
        &mut self,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        interface: AxiInterface,
    ) {
        let frame = match self.stack.last_mut() {
            Some(frame) => frame,
            None => return,
        };
        let InsertedAxiWriteResp {
            index,
            writeresp_edge,
        } = self
            .axi_builders
            .entry(interface)
            .or_default()
            .insert_writeresp();
        self.add_event(
            frame,
            static_stage,
            dynamic_stage,
            Event::AxiWriteResponse {
                interface,
                index,
                writeresp_edge,
            },
        );
    }

    pub fn call(
        &mut self,
        start_static_stage: SimulationStage,
        start_dynamic_stage: SimulationStage,
        end_dynamic_stage: SimulationStage,
        start_delay: ClockCycle,
        inherit_ap_continue: bool,
    ) {
        let parent = match self.stack.last_mut() {
            Some(parent) => parent,
            None => return,
        };

        let start_edge = self
            .edge_builder
            .insert_edge(IncompleteEdgeType::ControlFlow);
        self.edge_builder.add_delay(start_edge, start_delay);
        let module_key =
            self.modules_builder
                .insert_module(Some(parent.key), start_delay, inherit_ap_continue);
        self.stack
            .push(StackFrame::new(module_key, end_dynamic_stage, start_edge));

        self.add_event(
            parent,
            start_static_stage,
            start_dynamic_stage,
            Event::SubcallStart {
                module_key,
                edge: start_edge,
            },
        );
    }

    pub fn r#return(&mut self, module_name: String) {
        let mut frame = match self.stack.pop() {
            Some(frame) => frame,
            None => return,
        };
        let mut parent = self.stack.last_mut();

        while let Some(uncommitted_node) = frame.window.pop_front() {
            let advance_by = if !frame.window.is_empty() { 1 } else { 0 };
            self.commit_node(&mut frame, uncommitted_node, advance_by);
        }
        if let Some(remaining_stages) = frame.parent_end.checked_sub(frame.offset) {
            let remaining_delay = remaining_stages.into();
            frame.current_time += remaining_delay;
            self.edge_builder
                .add_delay(frame.current_edge, remaining_delay);
        }

        self.modules_builder
            .update_module_name(frame.key, module_name);
        self.modules_builder
            .update_module_end(frame.key, frame.current_time);

        match parent {
            Some(parent) => parent.add_event(
                frame.parent_end - parent.offset,
                Event::SubcallEnd {
                    edge: frame.current_edge,
                },
            ),
            None => {
                self.end_node = Some(self.edge_builder.insert_node());
                self.edge_builder.push_destination(frame.current_edge);
            }
        }
    }

    pub fn finish(&mut self) -> PyResult<CompiledSimulation> {
        mem::take(self).try_into()
    }
}

impl SimulationBuilder {
    fn commit_event(&mut self, event: Event, node: NodeWithDelay) {
        match event {
            Event::SubcallStart { module_key, edge } => {
                let deferred = self.modules_builder.commit_module(module_key, node);
                self.edge_builder.update_source(edge, node);
                for (node, event) in deferred {
                    debug_assert!(!event.has_in_edge());
                    self.commit_event(event, node);
                }
            }
            Event::SubcallEnd { edge } => {
                self.edge_builder.push_destination(edge);
            }
            Event::FifoRead {
                fifo,
                index,
                raw_edge,
            } => {
                self.fifo_builders[&fifo].update_read(index, node);
                self.edge_builder.push_destination(raw_edge);
            }
            Event::FifoWrite {
                fifo,
                index,
                raw_edge,
            } => {
                self.fifo_builders[&fifo].update_write(index, node);
                self.edge_builder.update_source(raw_edge, node);
                if index != 0 {
                    self.edge_builder.push_edge(Edge::FifoWar { fifo, index });
                }
            }
            Event::AxiReadRequest {
                interface,
                index,
                read_edge,
            } => {
                self.axi_builders[&interface].update_readreq(index, node);
                self.edge_builder.update_source(read_edge, node);
            }
            Event::AxiRead {
                interface,
                index,
                read_edge,
                rctl_out_edge,
                rctl_in_edge,
            } => {
                self.axi_builders[&interface].update_read(index, node);
                if let Some(read_edge) = read_edge {
                    self.edge_builder.push_destination(read_edge);
                }
                if let Some(rctl_out_edge) = rctl_out_edge {
                    self.edge_builder.update_source(rctl_out_edge, node);
                }
                if let Some(rctl_in_edge) = rctl_in_edge {
                    self.edge_builder.push_destination(rctl_in_edge);
                }
            }
            Event::AxiWriteRequest { interface, index } => {
                self.axi_builders[&interface].update_writereq(index, node);
            }
            Event::AxiWrite {
                interface,
                index,
                writeresp_edge,
            } => {
                self.axi_builders[&interface].update_write(index, node);
                if let Some(writeresp_edge) = writeresp_edge {
                    self.edge_builder.update_source(writeresp_edge, node);
                }
            }
            Event::AxiWriteResponse {
                interface,
                index,
                writeresp_edge,
            } => {
                self.axi_builders[&interface].update_writeresp(index, node);
                self.edge_builder.push_destination(writeresp_edge);
            }
        }
    }

    fn commit_node(
        &mut self,
        frame: &mut StackFrame,
        uncommitted_node: UncommittedNode,
        advance_by: SimulationStage,
    ) {
        frame.offset += advance_by;
        let delay = advance_by.into();
        let commit_time = if uncommitted_node.is_own_node() {
            let node = self.edge_builder.insert_node();
            self.edge_builder.push_destination(frame.current_edge);
            let node_with_delay = NodeWithDelay { node, delay };
            frame.current_edge = self
                .edge_builder
                .insert_edge(IncompleteEdgeType::ControlFlow);
            frame.current_time = NodeTime::Absolute(node_with_delay);
            self.edge_builder
                .update_source(frame.current_edge, node_with_delay);
            NodeTime::Absolute(NodeWithDelay { node, delay: 0 })
        } else {
            self.edge_builder.add_delay(frame.current_edge, delay);
            mem::replace(&mut frame.current_time, frame.current_time + delay)
        };
        match commit_time {
            NodeTime::Absolute(node) => {
                for event in uncommitted_node.events {
                    self.commit_event(event, node);
                }
            }
            NodeTime::RelativeToStart(delay) => {
                let events = uncommitted_node.events.into_iter();
                self.modules_builder.defer_events(frame.key, delay, events);
            }
        }
    }

    fn commit_until(&mut self, frame: &mut StackFrame, stage: SimulationStage) {
        while frame.offset < stage {
            match frame.window.pop_front() {
                Some(uncommitted_node) => self.commit_node(frame, uncommitted_node, 1),
                None => break,
            };
        }
        if let Some(remaining_stages) = stage.checked_sub(frame.offset) {
            let remaining_delay = remaining_stages.into();
            frame.offset = stage;
            frame.current_time += remaining_delay;
            self.edge_builder
                .add_delay(frame.current_edge, remaining_delay);
        }
    }

    fn add_event(
        &mut self,
        frame: &mut StackFrame,
        static_stage: SimulationStage,
        dynamic_stage: SimulationStage,
        event: Event,
    ) {
        self.commit_until(frame, dynamic_stage - static_stage);
        frame.add_event(static_stage, event);
    }
}

impl Default for SimulationBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl TryFrom<SimulationBuilder> for CompiledSimulation {
    type Error = PyErr;

    fn try_from(mut value: SimulationBuilder) -> Result<Self, Self::Error> {
        for axi_builder in value.axi_builders.values_mut() {
            for incomplete_edge in axi_builder.finish() {
                value.edge_builder.void_destination(incomplete_edge);
            }
        }

        Ok(CompiledSimulation {
            graph: value.edge_builder.try_into()?,
            top_module: value.modules_builder.try_into()?,
            fifo_nodes: value
                .fifo_builders
                .into_iter()
                .map(|(fifo, builder)| builder.try_into().map(|nodes: FifoIoNodes| (fifo, nodes)))
                .collect::<Result<_, _>>()?,
            axi_interface_nodes: value
                .axi_builders
                .into_iter()
                .map(|(axi_interface, builder)| {
                    builder
                        .try_into()
                        .map(|nodes: AxiInterfaceIoNodes| (axi_interface, nodes))
                })
                .collect::<Result<_, _>>()?,
            start_node: value.start_node,
            end_node: value
                .end_node
                .ok_or_else(|| PyValueError::new_err("incomplete trace"))?,
        })
    }
}
