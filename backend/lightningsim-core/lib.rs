mod builder;
mod simulation;
mod node;
mod edge;
mod axi_interface;
mod fifo;

use std::collections::{HashMap, VecDeque};
use std::{cmp, iter};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyIterator};
use pyo3::AsPyPointer;

use rustc_hash::FxHashMap;
use smallvec::SmallVec;

use simulation::{ClockCycle, SimulationStage, AxiAddress, FifoId, NodeIndex, NodeWithDelay};

struct Trace {
    py_trace: PyObject,
    blocks: Vec<ResolvedBlock>,
}

impl FromPyObject<'_> for Trace {
    fn extract(trace: &'_ PyAny) -> PyResult<Self> {
        let blocks = trace.extract()?;
        Ok(Trace {
            py_trace: trace.into(),
            blocks,
        })
    }
}

struct SortedTrace<'a> {
    sorted_stalls: Box<[&'a ResolvedEvent]>,
    sorted_subcalls: Box<[&'a SubcallEvent]>,
    end_stage: SimulationStage,
}

struct SortedTraceIterator<'a: 'b, 'b> {
    remaining_stalls: &'b [&'a ResolvedEvent],
    remaining_subcalls: &'b [&'a SubcallEvent],
    end_stage: SimulationStage,
    done: bool,
}

struct SortedTraceGroup<'a: 'b, 'b> {
    stage: SimulationStage,
    stalls: &'b [&'a ResolvedEvent],
    subcalls: &'b [&'a SubcallEvent],
}

impl<'a> SortedTrace<'a> {
    fn new(blocks: &'a Vec<ResolvedBlock>) -> Self {
        let mut sorted_stalls: Box<_> = blocks
            .iter()
            .flat_map(|block| block.events.iter())
            .collect();
        sorted_stalls.sort_unstable_by_key(|event| event.stall_stage());

        let mut sorted_subcalls: Box<_> = blocks
            .iter()
            .flat_map(|block| {
                block.events.iter().filter_map(|event| match event {
                    ResolvedEvent::Subcall(subcall) => Some(subcall),
                    _ => None,
                })
            })
            .collect();
        sorted_subcalls.sort_unstable_by_key(|subcall| subcall.start_stage);

        let end_stage = blocks
            .iter()
            .map(|block| block.end_stage)
            .max()
            .unwrap_or(0);

        SortedTrace {
            sorted_stalls,
            sorted_subcalls,
            end_stage,
        }
    }
}

impl<'a> IntoIterator for &'a SortedTrace<'a> {
    type Item = SortedTraceGroup<'a, 'a>;
    type IntoIter = SortedTraceIterator<'a, 'a>;

    fn into_iter(self) -> Self::IntoIter {
        SortedTraceIterator {
            remaining_stalls: &self.sorted_stalls,
            remaining_subcalls: &self.sorted_subcalls,
            end_stage: self.end_stage,
            done: false,
        }
    }
}

impl<'a: 'b, 'b> Iterator for SortedTraceIterator<'a, 'b> {
    type Item = SortedTraceGroup<'a, 'b>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.done {
            return None;
        }

        let stage = match self.remaining_stalls.first() {
            Some(stall) => stall.stall_stage(),
            None => {
                self.done = true;
                return Some(SortedTraceGroup {
                    stage: self.end_stage,
                    stalls: &[],
                    subcalls: self.remaining_subcalls,
                });
            }
        };

        let remaining_stalls_split_index = self
            .remaining_stalls
            .iter()
            .position(|stall| stall.stall_stage() > stage)
            .unwrap_or_else(|| self.remaining_stalls.len());
        let stalls;
        (stalls, self.remaining_stalls) =
            self.remaining_stalls.split_at(remaining_stalls_split_index);

        let remaining_subcalls_split_index = self
            .remaining_subcalls
            .iter()
            .position(|subcall| subcall.start_stage > stage)
            .unwrap_or_else(|| self.remaining_subcalls.len());
        let subcalls;
        (subcalls, self.remaining_subcalls) = self
            .remaining_subcalls
            .split_at(remaining_subcalls_split_index);

        Some(SortedTraceGroup {
            stage,
            stalls,
            subcalls,
        })
    }
}

struct SubcallEvent {
    py_event: PyObject,
    start_stage: SimulationStage,
    stall_stage: SimulationStage,
    start_delay: ClockCycle,
    trace: Trace,
    inherit_ap_continue: bool,
}

struct FifoEvent {
    stall_stage: SimulationStage,
    fifo: PyObject,
}

#[derive(Clone, Copy)]
struct AxiAddressRange {
    offset: AxiAddress,
    length: AxiAddress,
}

impl AxiAddressRange {
    fn burst_count(&self) -> usize {
        (((self.offset + self.length - 1) / 4096) - (self.offset / 4096) + 1)
            .try_into()
            .unwrap()
    }
}

struct AxiGenericEvent {
    stall_stage: SimulationStage,
    interface: AxiInterface,
    range: AxiAddressRange,
}

struct AxiWriteResponseEvent {
    stall_stage: SimulationStage,
    interface: AxiInterface,
}

enum ResolvedEvent {
    Subcall(SubcallEvent),
    FifoRead(FifoEvent),
    FifoWrite(FifoEvent),
    AxiReadRequest(AxiGenericEvent),
    AxiRead(AxiGenericEvent),
    AxiWriteRequest(AxiGenericEvent),
    AxiWrite(AxiGenericEvent),
    AxiWriteResponse(AxiWriteResponseEvent),
}

impl ResolvedEvent {
    fn stall_stage(&self) -> SimulationStage {
        match self {
            ResolvedEvent::Subcall(event) => event.stall_stage,
            ResolvedEvent::FifoRead(event) => event.stall_stage,
            ResolvedEvent::FifoWrite(event) => event.stall_stage,
            ResolvedEvent::AxiReadRequest(event) => event.stall_stage,
            ResolvedEvent::AxiRead(event) => event.stall_stage,
            ResolvedEvent::AxiWriteRequest(event) => event.stall_stage,
            ResolvedEvent::AxiWrite(event) => event.stall_stage,
            ResolvedEvent::AxiWriteResponse(event) => event.stall_stage,
        }
    }
}

impl FromPyObject<'_> for ResolvedEvent {
    fn extract(event: &PyAny) -> PyResult<Self> {
        let event_type = event.getattr(intern!(event.py(), "type"))?.extract()?;
        let metadata = event.getattr(intern!(event.py(), "metadata"))?;
        match event_type {
            "call" => {
                let call_inst = event.getattr(intern!(event.py(), "instruction"))?;
                let region = call_inst
                    .getattr(intern!(event.py(), "basic_block"))?
                    .getattr(intern!(event.py(), "region"))?;
                let pipeline_ii = region.getattr(intern!(region.py(), "ii"))?;
                let in_pipeline = !pipeline_ii.is_none();
                let dataflow = region.getattr(intern!(region.py(), "dataflow"))?;
                let in_dataflow = !dataflow.is_none();
                let start_stage = event
                    .getattr(intern!(event.py(), "start_stage"))?
                    .extract()?;
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let trace = metadata.getattr(intern!(event.py(), "trace"))?.extract()?;
                let has_start_delay = !in_pipeline && !in_dataflow;
                let start_delay = if has_start_delay { 1 } else { 0 };
                let is_dataflow_sink = in_dataflow
                    && dataflow
                        .getattr("process_outputs")?
                        .get_item(call_inst)?
                        .len()?
                        == 0;
                let inherit_ap_continue = is_dataflow_sink;
                Ok(ResolvedEvent::Subcall(SubcallEvent {
                    py_event: event.into(),
                    start_stage,
                    stall_stage,
                    start_delay,
                    trace,
                    inherit_ap_continue,
                }))
            }
            "fifo_read" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let fifo = metadata.getattr(intern!(event.py(), "fifo"))?.into();
                Ok(ResolvedEvent::FifoRead(FifoEvent { stall_stage, fifo }))
            }
            "fifo_write" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let fifo = metadata.getattr(intern!(event.py(), "fifo"))?.into();
                Ok(ResolvedEvent::FifoWrite(FifoEvent { stall_stage, fifo }))
            }
            "axi_readreq" => {
                let stall_stage = event
                    .getattr(intern!(event.py(), "start_stage"))?
                    .extract()?;
                let interface = metadata
                    .getattr(intern!(event.py(), "interface"))?
                    .extract()?;
                let offset = metadata.getattr(intern!(event.py(), "offset"))?.extract()?;
                let length = metadata.getattr(intern!(event.py(), "length"))?.extract()?;
                Ok(ResolvedEvent::AxiReadRequest(AxiGenericEvent {
                    stall_stage,
                    interface,
                    range: AxiAddressRange { offset, length },
                }))
            }
            "axi_read" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let interface = metadata
                    .getattr(intern!(event.py(), "interface"))?
                    .extract()?;
                let offset = metadata.getattr(intern!(event.py(), "offset"))?.extract()?;
                let length = metadata.getattr(intern!(event.py(), "length"))?.extract()?;
                Ok(ResolvedEvent::AxiRead(AxiGenericEvent {
                    stall_stage,
                    interface,
                    range: AxiAddressRange { offset, length },
                }))
            }
            "axi_writereq" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let interface = metadata
                    .getattr(intern!(event.py(), "interface"))?
                    .extract()?;
                let offset = metadata.getattr(intern!(event.py(), "offset"))?.extract()?;
                let length = metadata.getattr(intern!(event.py(), "length"))?.extract()?;
                Ok(ResolvedEvent::AxiWriteRequest(AxiGenericEvent {
                    stall_stage,
                    interface,
                    range: AxiAddressRange { offset, length },
                }))
            }
            "axi_write" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let interface = metadata
                    .getattr(intern!(event.py(), "interface"))?
                    .extract()?;
                let offset = metadata.getattr(intern!(event.py(), "offset"))?.extract()?;
                let length = metadata.getattr(intern!(event.py(), "length"))?.extract()?;
                Ok(ResolvedEvent::AxiWrite(AxiGenericEvent {
                    stall_stage,
                    interface,
                    range: AxiAddressRange { offset, length },
                }))
            }
            "axi_writeresp" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let interface = metadata
                    .getattr(intern!(event.py(), "interface"))?
                    .extract()?;
                Ok(ResolvedEvent::AxiWriteResponse(AxiWriteResponseEvent {
                    stall_stage,
                    interface,
                }))
            }
            _ => Err(PyTypeError::new_err(format!(
                "invalid event type: {}",
                event_type
            ))),
        }
    }
}

#[derive(FromPyObject)]
struct ResolvedBlock {
    events: Vec<ResolvedEvent>,
    end_stage: SimulationStage,
}

#[derive(Clone)]
enum UncommittedModuleTiming {
    Constant(ClockCycle),
    Variable {
        /// The first edge in this submodule; its source node defaults to 0 and
        /// should be replaced with the real source node from the parent module
        /// (unless this is the top-level module).
        start_edge_index: usize,
        end: NodeWithDelay,
    },
}

#[derive(Clone)]
struct UncommittedModuleExecution {
    /// The unique identifier of this module execution in the Python interface.
    /// This can be any Python object.
    key: PyObject,
    start_delay: ClockCycle,
    timing: UncommittedModuleTiming,
    submodules: Vec<MaybeCommittedModuleExecution>,
    inherit_ap_continue: bool,
}

#[derive(Clone)]
enum MaybeCommittedModuleExecution {
    Uncommitted(UncommittedModuleExecution),
    Committed(ModuleExecution),
}

#[derive(Clone, Default)]
struct NodeMappings {
    fifo_nodes: FxHashMap<Fifo, FifoIoNodes>,
    axi_interface_nodes: FxHashMap<AxiInterface, AxiInterfaceIoNodes>,
}

enum NodeCommitAction {
    SetEdgeSource {
        edge_index: usize,
    },
    /// This is necessary to handle submodules with timing of type
    /// UncommittedModuleTiming::Constant. In this case, the submodule will
    /// consist of a single edge where neither the source nor destination nodes
    /// are committed at the time the submodule is committed. Once the source
    /// node is committed, the edge must be updated with the committed node
    /// index.
    SetDownstreamEdgeSource {
        /// The number of nodes between this node (the source node) and the
        /// destination node of the edge to be updated.
        offset: SimulationStage,
        /// The index within [UncommittedNode#additional_sources] of the edge
        /// to be updated.
        index: usize,
    },
}

enum NodeIo {
    FifoRead {
        fifo: Fifo,
    },
    FifoWrite {
        fifo: Fifo,
    },
    AxiReadRequest {
        interface: AxiInterface,
        range: AxiAddressRange,
    },
    AxiRead {
        interface: AxiInterface,
        range: AxiAddressRange,
    },
    AxiWriteRequest {
        interface: AxiInterface,
        range: AxiAddressRange,
    },
    AxiWrite {
        interface: AxiInterface,
        range: AxiAddressRange,
    },
    AxiWriteResponse {
        interface: AxiInterface,
    },
}

#[derive(Default)]
struct UncommittedNode {
    actions: SmallVec<[NodeCommitAction; 4]>,
    additional_sources: SmallVec<[NodeWithDelay; 4]>,
    io: SmallVec<[NodeIo; 4]>,
}

impl UncommittedNode {
    fn new() -> Self {
        Default::default()
    }

    fn commit(&self, position: NodeWithDelay) {
        let min_in_degree = self.additional_sources.len() + 1;
        let max_in_degree = min_in_degree + self.io.len();
        let is_own_node = max_in_degree > 1;
    }
}

#[pyclass]
#[derive(Clone)]
struct SimulationBuilder {
    graph: DiGraph<(), ClockCycle>,
    node_mappings: NodeMappings,
    top_module: ModuleExecution,
    has_fifo_depths: bool,
    has_axi_delays: bool,
    is_ap_ctrl_chain: bool,
    num_parameters: u32,
}

/// An edge in the simulation graph.
#[derive(Clone)]
struct Edge {
    /// The source node of this edge.
    u: NodeIndex,
    /// The destination node of this edge.
    v: NodeIndex,
    /// The weight of this edge, representing a minimum delay of some number of
    /// clock cycles in the simulation graph.
    weight: ClockCycle,
}

/// A work-in-progress simulation graph.
#[derive(Clone)]
struct SimulationGraphBuilder {
    total_edge_count: usize,
    node_in_degrees: Vec<DegreeBounds>,
    cfg_edges: Vec<Edge>,
}

impl Default for SimulationGraphBuilder {
    fn default() -> Self {
        SimulationGraphBuilder {
            total_edge_count: 0,
            node_in_degrees: vec![DegreeBounds::default()],
            cfg_edges: Vec::new(),
        }
    }
}

impl SimulationGraphBuilder {
    fn new() -> Self {
        Default::default()
    }

    fn add_node(&mut self) -> usize {
        let index = self.node_in_degrees.len();
        self.node_in_degrees.push(0);
        index
    }

    fn count_edge(&mut self, edge: &Edge) {
        self.total_edge_count += 1;
        self.node_in_degrees[edge.v.index()] += 1;
    }
}

#[pyclass]
#[derive(Clone, Default)]
struct SimulationBuilder2 {
    graph: SimulationGraphBuilder,
    stack: Vec<StackFrame>,
    top_module: Option<ModuleExecution>,
}

impl SimulationBuilder2 {
    // fn commit(&mut self, mut stages: usize) {
    //     let StackFrame { window, module } = self.stack.last_mut().unwrap();
    //     while stages > 0 {
    //         match window.pop_front() {
    //             Some(stage) => {
    //                 stage.commit(&mut self.graph, module);
    //                 stages -= 1;
    //             }
    //             None => {
    //                 module.end.delay += stages as ClockCycle;
    //                 return;
    //             }
    //         }
    //     }
    // }

    // fn call(&mut self, key: PyObject, inherit_ap_continue: bool) {
    //     let start = match self.stack.last() {
    //         Some(StackFrame { module, .. })
    //     };
    //     self.stack.push(StackFrame::new(key, ))
    // }

    // fn r#return(&mut self) {
    //     let StackFrame { window, mut module } = self.stack.pop().unwrap();
    //     for stage in window {
    //         stage.commit(&mut self.graph, &mut module);
    //     }
    //     match self.stack.last_mut() {
    //         Some(StackFrame { module: parent, .. }) => parent.submodules.push(module),
    //         None => self.top_module = Some(module),
    //     }
    // }
}

#[pyclass]
#[derive(Clone)]
struct Simulation {
    node_cycles: Box<[ClockCycle]>,
    node_mappings: NodeMappings,
    #[pyo3(get)]
    top_module: SimulationModule,
}

impl Simulation {
    fn new(builder: &SimulationBuilder) -> PyResult<Self> {
        let mut node_cycles =
            vec![ClockCycle::default(); builder.graph.node_count()].into_boxed_slice();
        let node_mappings = builder.node_mappings.clone();

        let nodes = match algo::toposort(&builder.graph, None) {
            Ok(nodes) => nodes,
            Err(_) => {
                return Err(PyValueError::new_err(
                    "simulation will deadlock. Please check FIFO depths",
                ))
            }
        };

        for node in nodes {
            node_cycles[node.index()] = builder
                .graph
                .edges_directed(node, Direction::Incoming)
                .map(|edge| node_cycles[edge.source().index()] + edge.weight())
                .max()
                .unwrap_or(0);
        }

        let ap_continue = if builder.is_ap_ctrl_chain {
            ApContinue::TopLevel {
                num_parameters: builder.num_parameters,
            }
        } else {
            ApContinue::NotApplicable
        };
        let top_module = SimulationModule::new(&node_cycles, &builder.top_module, ap_continue);

        Ok(Simulation {
            node_cycles,
            node_mappings,
            top_module,
        })
    }
}

#[pymethods]
impl Simulation {
    fn get_latency(&self) -> ClockCycle {
        self.top_module.end
    }

    fn get_observed_fifo_depths<'a>(&self, py: Python<'a>) -> PyResult<&'a PyDict> {
        let result = PyDict::new(py);
        for nodes in self.node_mappings.fifo_nodes.values() {
            let mut depth: usize = 0;
            let mut max_depth: usize = 0;
            let mut write_iter = nodes
                .writes
                .iter()
                .map(|&node| self.node_cycles[node.index()]);
            let mut read_iter = nodes
                .reads
                .iter()
                .map(|&node| self.node_cycles[node.index()]);
            let mut next_write_cycle = write_iter.next();
            let mut next_read_cycle = read_iter.next();

            while let (Some(write_cycle), Some(read_cycle)) = (next_write_cycle, next_read_cycle) {
                if write_cycle < read_cycle {
                    depth += 1;
                    max_depth = max_depth.max(depth);
                    next_write_cycle = write_iter.next();
                } else {
                    depth -= 1;
                    next_read_cycle = read_iter.next();
                }
            }

            result.set_item(nodes.fifo.as_ref(py), max_depth)?;
        }
        Ok(result)
    }
}

#[pyclass]
#[derive(Clone)]
struct SimulationModule {
    #[pyo3(get)]
    trace: PyObject,
    #[pyo3(get)]
    start: ClockCycle,
    #[pyo3(get)]
    end: ClockCycle,
    #[pyo3(get)]
    submodules: Vec<SimulationModule>,
}

#[derive(Clone, Copy)]
enum ApContinue {
    NotApplicable,
    TopLevel { num_parameters: u32 },
    Propagated(ClockCycle),
}

impl SimulationModule {
    fn new(node_cycles: &[ClockCycle], module: &ModuleExecution, ap_continue: ApContinue) -> Self {
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
                // ap_continue is asserted by AESL_axi_slave_control some cycles after it reads ap_done.
                // It checks ap_done every few cycles; we first calculate how often it performs this check.

                // AESL_axi_slave_control is structured as a series of repeated sequential processes.
                // They are:
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

        SimulationModule {
            trace: module.key.clone(),
            start,
            end,
            submodules: module
                .submodules
                .iter()
                .map(|submodule| SimulationModule::new(node_cycles, submodule, ap_continue))
                .collect(),
        }
    }

    fn get_function_name(&self, py: Python<'_>) -> PyResult<String> {
        self.trace
            .as_ref(py)
            .get_item(0)?
            .getattr(intern!(py, "basic_block"))?
            .getattr(intern!(py, "parent"))?
            .getattr(intern!(py, "name"))?
            .extract()
    }
}

#[pymethods]
impl SimulationModule {
    fn __repr__(&self, py: Python<'_>) -> String {
        format!(
            "<SimulationModule for {}: cycles {}-{}>",
            self.get_function_name(py)
                .unwrap_or_else(|_| "(unknown function)".into()),
            self.start,
            self.end
        )
    }
}

#[pymethods]
impl SimulationBuilder {
    #[new]
    fn new(py: Python<'_>, trace: Trace) -> PyResult<Self> {
        fn build_cfg(
            py: Python<'_>,
            graph: &mut DiGraph<(), ClockCycle>,
            node_mappings: &mut NodeMappings,
            trace: &Trace,
            start: NodeWithDelay,
            inherit_ap_continue: bool,
        ) -> PyResult<ModuleExecution> {
            let mut unreaped_submodules = FxHashMap::new();
            let mut submodules = Vec::new();
            let mut previous_stage = 0;
            let mut current = start;

            for SortedTraceGroup {
                stage,
                subcalls,
                stalls,
            } in &SortedTrace::new(&trace.blocks)
            {
                for subcall in subcalls {
                    let subcall_start =
                        current + (subcall.start_stage - previous_stage + subcall.start_delay);
                    let submodule = build_cfg(
                        py,
                        graph,
                        node_mappings,
                        &subcall.trace,
                        subcall_start,
                        subcall.inherit_ap_continue,
                    )?;
                    unreaped_submodules.insert(subcall.py_event.as_ptr(), submodule.end);
                    submodules.push(submodule);
                }

                let delay = current.delay + stage - previous_stage;
                previous_stage = stage;

                if stalls.is_empty() {
                    current = NodeWithDelay {
                        node: current.node,
                        delay,
                    };
                } else {
                    let node = graph.add_node(());
                    graph.add_edge(current.node, node, delay);
                    current = NodeWithDelay { node, delay: 0 };

                    for stall in stalls {
                        match stall {
                            ResolvedEvent::Subcall(subcall) => {
                                let subcall_end = unreaped_submodules
                                    .remove(&subcall.py_event.as_ptr())
                                    .ok_or_else(|| {
                                        PyValueError::new_err("subcall end appears before start")
                                    })?;
                                graph.add_edge(subcall_end.node, node, subcall_end.delay);
                            }
                            ResolvedEvent::FifoWrite(fifo_write) => node_mappings
                                .fifo_nodes
                                .entry(fifo_write.fifo.extract(py)?)
                                .or_insert_with(|| FifoIoNodes::new(fifo_write.fifo.clone_ref(py)))
                                .writes
                                .push(node),
                            ResolvedEvent::FifoRead(fifo_read) => node_mappings
                                .fifo_nodes
                                .entry(fifo_read.fifo.extract(py)?)
                                .or_insert_with(|| FifoIoNodes::new(fifo_read.fifo.clone_ref(py)))
                                .reads
                                .push(node),
                            ResolvedEvent::AxiReadRequest(axi_readreq) => node_mappings
                                .axi_interface_nodes
                                .entry(axi_readreq.interface)
                                .or_default()
                                .readreqs
                                .push(AxiGenericIoNode {
                                    node,
                                    range: axi_readreq.range,
                                }),
                            ResolvedEvent::AxiRead(axi_read) => node_mappings
                                .axi_interface_nodes
                                .entry(axi_read.interface)
                                .or_default()
                                .reads
                                .push(AxiGenericIoNode {
                                    node,
                                    range: axi_read.range,
                                }),
                            ResolvedEvent::AxiWriteRequest(axi_writereq) => node_mappings
                                .axi_interface_nodes
                                .entry(axi_writereq.interface)
                                .or_default()
                                .writereqs
                                .push(AxiGenericIoNode {
                                    node,
                                    range: axi_writereq.range,
                                }),
                            ResolvedEvent::AxiWrite(axi_write) => node_mappings
                                .axi_interface_nodes
                                .entry(axi_write.interface)
                                .or_default()
                                .writes
                                .push(AxiGenericIoNode {
                                    node,
                                    range: axi_write.range,
                                }),
                            ResolvedEvent::AxiWriteResponse(axi_writeresp) => node_mappings
                                .axi_interface_nodes
                                .entry(axi_writeresp.interface)
                                .or_default()
                                .writeresps
                                .push(node),
                        }
                    }
                }
            }

            assert!(unreaped_submodules.is_empty());
            Ok(ModuleExecution {
                key: trace.py_trace.clone(),
                start,
                end: current,
                submodules,
                inherit_ap_continue,
            })
        }

        let mut graph = DiGraph::new();
        let mut node_mappings = NodeMappings::default();
        let start_node = graph.add_node(());
        let start = NodeWithDelay {
            node: start_node,
            delay: 0,
        };
        let top_module = build_cfg(py, &mut graph, &mut node_mappings, &trace, start, true)?;

        let top_ports: &PyIterator = trace
            .py_trace
            .as_ref(py)
            .get_item(0)?
            .getattr(intern!(py, "basic_block"))?
            .getattr(intern!(py, "parent"))?
            .getattr(intern!(py, "ports"))?
            .call_method0(intern!(py, "values"))?
            .iter()?;
        let num_parameters = top_ports.fold(Ok(0), |acc, port| -> PyResult<_> {
            let acc = acc?;
            let interface_type: u32 = port?.getattr(intern!(py, "interface_type"))?.extract()?;
            Ok(acc + (if interface_type == 0 { 1 } else { 0 }))
        })?;

        Ok(SimulationBuilder {
            graph,
            node_mappings,
            top_module,
            has_fifo_depths: false,
            has_axi_delays: false,
            is_ap_ctrl_chain: false,
            num_parameters,
        })
    }

    fn set_fifo_depths(&mut self, fifo_depths: HashMap<Fifo, Option<usize>>) -> PyResult<()> {
        if self.has_fifo_depths {
            return Err(PyValueError::new_err(
                "fifo depths already set for this model",
            ));
        }

        for (fifo, nodes) in &self.node_mappings.fifo_nodes {
            let &depth = fifo_depths.get(fifo).ok_or_else(|| {
                PyValueError::new_err(format!("no depth specified for fifo with id {:?}", fifo.id))
            })?;
            let fifo_type = match depth {
                Some(depth) => {
                    if depth <= 2 {
                        FifoType::ShiftRegister
                    } else {
                        FifoType::Ram
                    }
                }
                None => FifoType::ShiftRegister,
            };

            let raw_delay = match fifo_type {
                FifoType::ShiftRegister => SHIFT_REGISTER_RAW_DELAY,
                FifoType::Ram => RAM_RAW_DELAY,
            };
            for (&write, &read) in iter::zip(&nodes.writes, &nodes.reads) {
                self.graph.add_edge(write, read, raw_delay);
            }

            if let Some(depth) = depth {
                if nodes.writes.len() > depth {
                    let war_delay = match fifo_type {
                        FifoType::ShiftRegister => SHIFT_REGISTER_WAR_DELAY,
                        FifoType::Ram => RAM_WAR_DELAY,
                    };
                    for (&read, &write) in iter::zip(&nodes.reads, &nodes.writes[depth..]) {
                        self.graph.add_edge(read, write, war_delay);
                    }
                }
            }
        }

        self.has_fifo_depths = true;
        Ok(())
    }

    fn set_axi_delays(&mut self, axi_delays: HashMap<AxiInterface, ClockCycle>) -> PyResult<()> {
        if self.has_axi_delays {
            return Err(PyValueError::new_err(
                "axi delays already set for this model",
            ));
        }

        for (axi_interface, nodes) in &self.node_mappings.axi_interface_nodes {
            let &delay = axi_delays.get(axi_interface).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "no delay specified for axi interface with address {:?}",
                    axi_interface.address
                ))
            })?;
            let delay = cmp::max(delay, 1);
            let mut readreq_iter = nodes.readreqs.iter();
            let mut current_readreq: Option<&AxiGenericIoNode> = None;
            let mut consumed: AxiAddress = 0;
            let mut rctl_depth: usize = 0;
            let mut rctl_burst_counts: VecDeque<usize> = VecDeque::with_capacity(MAX_RCTL_DEPTH);
            let mut rctl_tail_nodes: VecDeque<NodeIndex> = VecDeque::with_capacity(MAX_RCTL_DEPTH);

            for &read in &nodes.reads {
                let &readreq = match current_readreq {
                    Some(readreq) => readreq,
                    None => {
                        let readreq = readreq_iter.next().ok_or_else(|| {
                            PyValueError::new_err(format!(
                                "not enough readreqs for reads on axi interface with address {:?}",
                                axi_interface.address
                            ))
                        })?;
                        consumed = 0;

                        let mut blocking_read_node: Option<NodeIndex> = None;
                        while rctl_depth >= MAX_RCTL_DEPTH {
                            rctl_depth -= rctl_burst_counts.pop_front().unwrap();
                            blocking_read_node = Some(rctl_tail_nodes.pop_front().unwrap());
                        }

                        let burst_count = readreq.range.burst_count();
                        rctl_depth += burst_count;
                        rctl_burst_counts.push_back(burst_count);
                        if let Some(blocking_read_node) = blocking_read_node {
                            self.graph.add_edge(
                                blocking_read_node,
                                read.node,
                                delay + AXI_READ_OVERHEAD - AXI_WRITE_OVERHEAD,
                            );
                        }

                        current_readreq = Some(readreq);
                        readreq
                    }
                };

                self.graph
                    .add_edge(readreq.node, read.node, delay + AXI_READ_OVERHEAD);
                consumed += read.range.length;
                if consumed >= readreq.range.length {
                    rctl_tail_nodes.push_back(read.node);
                    current_readreq = None;
                }
            }

            let writereq_iter = nodes.writereqs.iter();
            let writeresp_iter = nodes.writeresps.iter();
            let mut writereqresp_iter = iter::zip(writereq_iter, writeresp_iter);
            let mut current_writereqresp: Option<(&AxiGenericIoNode, &NodeIndex)> = None;
            let mut consumed: AxiAddress = 0;
            for &write in &nodes.writes {
                let (&writereq, &writeresp_node) = match current_writereqresp {
                    Some(writereqresp) => writereqresp,
                    None => {
                        let writereqresp = writereqresp_iter.next().ok_or_else(|| {
                            PyValueError::new_err(format!("not enough writereqs/resps for writes on axi interface with address {:?}", axi_interface.address))
                        })?;
                        consumed = 0;
                        current_writereqresp = Some(writereqresp);
                        writereqresp
                    }
                };

                consumed += write.range.length;
                if consumed >= writereq.range.length {
                    self.graph
                        .add_edge(write.node, writeresp_node, delay + AXI_WRITE_OVERHEAD);
                    current_writereqresp = None;
                }
            }
        }

        self.has_axi_delays = true;
        Ok(())
    }

    fn set_ap_ctrl_chain(&mut self, is_ap_ctrl_chain: bool) {
        self.is_ap_ctrl_chain = is_ap_ctrl_chain;
    }

    fn build(&self) -> PyResult<Simulation> {
        Simulation::new(&self)
    }

    fn clone(&self) -> PyResult<Self> {
        Ok(Clone::clone(self))
    }
}

#[pymodule]
fn _core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<SimulationBuilder>()?;
    Ok(())
}
