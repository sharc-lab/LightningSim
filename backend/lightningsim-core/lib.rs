use std::collections::{HashMap, VecDeque};
use std::{cmp, iter, ops};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::AsPyPointer;

use rustworkx_core::petgraph::algo;
use rustworkx_core::petgraph::prelude::*;

type ClockCycle = u64;
type SimulationStage = u64;
type AxiAddress = u64;

const SHIFT_REGISTER_RAW_DELAY: ClockCycle = 1;
const SHIFT_REGISTER_WAR_DELAY: ClockCycle = 1;
const RAM_RAW_DELAY: ClockCycle = 2;
const RAM_WAR_DELAY: ClockCycle = 1;
const AXI_READ_OVERHEAD: ClockCycle = 12;
const AXI_WRITE_OVERHEAD: ClockCycle = 7;
const MAX_RCTL_DEPTH: usize = 16;

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

#[derive(FromPyObject, Clone, Copy, PartialEq, Eq, Hash)]
struct Fifo {
    id: u32,
}

enum FifoType {
    ShiftRegister,
    Ram,
}

#[derive(FromPyObject, Clone, Copy, PartialEq, Eq, Hash)]
struct AxiInterface {
    address: AxiAddress,
}

struct SubcallEvent {
    py_event: PyObject,
    start_stage: SimulationStage,
    stall_stage: SimulationStage,
    start_delay: ClockCycle,
    trace: Trace,
}

struct FifoEvent {
    stall_stage: SimulationStage,
    fifo: Fifo,
}

#[derive(Clone, Copy)]
struct AxiGenericIoRange {
    offset: AxiAddress,
    length: AxiAddress,
}

impl AxiGenericIoRange {
    fn burst_count(&self) -> usize {
        (((self.offset + self.length - 1) / 4096) - (self.offset / 4096) + 1)
            .try_into()
            .unwrap()
    }
}

struct AxiGenericEvent {
    stall_stage: SimulationStage,
    interface: AxiInterface,
    range: AxiGenericIoRange,
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

impl<'a> FromPyObject<'a> for ResolvedEvent {
    fn extract(event: &'a PyAny) -> PyResult<Self> {
        let event_type = event.getattr(intern!(event.py(), "type"))?.extract()?;
        let metadata = event.getattr(intern!(event.py(), "metadata"))?;
        match event_type {
            "call" => {
                fn is_pipeline(region: &PyAny) -> PyResult<bool> {
                    Ok(!region.getattr(intern!(region.py(), "ii"))?.is_none())
                }
                fn is_dataflow(region: &PyAny) -> PyResult<bool> {
                    Ok(!region.getattr(intern!(region.py(), "dataflow"))?.is_none())
                }

                let region = event
                    .getattr(intern!(event.py(), "instruction"))?
                    .getattr(intern!(event.py(), "basic_block"))?
                    .getattr(intern!(event.py(), "region"))?;
                let start_stage = event
                    .getattr(intern!(event.py(), "start_stage"))?
                    .extract()?;
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let trace = metadata.getattr(intern!(event.py(), "trace"))?.extract()?;
                let has_start_delay = !is_pipeline(region)? && !is_dataflow(region)?;
                let start_delay = if has_start_delay { 1 } else { 0 };
                Ok(ResolvedEvent::Subcall(SubcallEvent {
                    py_event: event.into(),
                    start_stage,
                    stall_stage,
                    start_delay,
                    trace,
                }))
            }
            "fifo_read" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let fifo = metadata.getattr(intern!(event.py(), "fifo"))?.extract()?;
                Ok(ResolvedEvent::FifoRead(FifoEvent { stall_stage, fifo }))
            }
            "fifo_write" => {
                let stall_stage = event.getattr(intern!(event.py(), "end_stage"))?.extract()?;
                let fifo = metadata.getattr(intern!(event.py(), "fifo"))?.extract()?;
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
                    range: AxiGenericIoRange { offset, length },
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
                    range: AxiGenericIoRange { offset, length },
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
                    range: AxiGenericIoRange { offset, length },
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
                    range: AxiGenericIoRange { offset, length },
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

#[derive(Clone, Default)]
struct FifoIoNodes {
    writes: Vec<NodeIndex>,
    reads: Vec<NodeIndex>,
}

#[derive(Clone, Copy)]
struct AxiGenericIoNode {
    node: NodeIndex,
    range: AxiGenericIoRange,
}

#[derive(Clone, Default)]
struct AxiInterfaceIoNodes {
    readreqs: Vec<AxiGenericIoNode>,
    reads: Vec<AxiGenericIoNode>,
    writereqs: Vec<AxiGenericIoNode>,
    writes: Vec<AxiGenericIoNode>,
    writeresps: Vec<NodeIndex>,
}

#[derive(Clone, Copy)]
struct NodeWithDelay {
    node: NodeIndex,
    delay: ClockCycle,
}

impl NodeWithDelay {
    fn resolve<T>(&self, graph: &DiGraph<ClockCycle, T>) -> ClockCycle {
        graph[self.node] + self.delay
    }
}

impl ops::Add<ClockCycle> for NodeWithDelay {
    type Output = Self;

    fn add(self, rhs: ClockCycle) -> Self::Output {
        NodeWithDelay {
            node: self.node,
            delay: self.delay + rhs,
        }
    }
}

#[derive(Clone)]
struct ModuleInvocation {
    py_trace: PyObject,
    start: NodeWithDelay,
    end: NodeWithDelay,
    submodules: Vec<ModuleInvocation>,
}

#[derive(Clone, Default)]
struct NodeMappings {
    fifo_nodes: HashMap<Fifo, FifoIoNodes>,
    axi_interface_nodes: HashMap<AxiInterface, AxiInterfaceIoNodes>,
}

#[pyclass]
#[derive(Clone)]
struct GlobalModel {
    graph: DiGraph<ClockCycle, ClockCycle>,
    node_mappings: NodeMappings,
    top_module: ModuleInvocation,
    has_fifo_depths: bool,
    has_axi_delays: bool,
    has_updated_node_latencies: bool,
}

#[pyclass]
#[derive(Clone)]
struct Simulation {
    #[pyo3(get)]
    trace: PyObject,
    #[pyo3(get)]
    start: ClockCycle,
    #[pyo3(get)]
    end: ClockCycle,
    #[pyo3(get)]
    submodules: Vec<Simulation>,
}

impl Simulation {
    fn new<T>(graph: &DiGraph<ClockCycle, T>, module: &ModuleInvocation) -> Self {
        Simulation {
            trace: module.py_trace.clone(),
            start: module.start.resolve(graph),
            end: module.end.resolve(graph),
            submodules: module
                .submodules
                .iter()
                .map(|submodule| Simulation::new(graph, submodule))
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
impl Simulation {
    fn __repr__(&self, py: Python<'_>) -> String {
        format!(
            "<Simulation of {}: cycles {}-{}>",
            self.get_function_name(py)
                .unwrap_or_else(|_| "(unknown function)".into()),
            self.start,
            self.end
        )
    }
}

#[pymethods]
impl GlobalModel {
    #[new]
    fn new(trace: Trace) -> PyResult<Self> {
        fn build_cfg(
            graph: &mut DiGraph<u64, u64>,
            node_mappings: &mut NodeMappings,
            trace: &Trace,
            start: NodeWithDelay,
        ) -> PyResult<ModuleInvocation> {
            let mut unreaped_submodules = HashMap::new();
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
                    let submodule = build_cfg(graph, node_mappings, &subcall.trace, subcall_start)?;
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
                    let node = graph.add_node(0);
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
                                .entry(fifo_write.fifo)
                                .or_default()
                                .writes
                                .push(node),
                            ResolvedEvent::FifoRead(fifo_read) => node_mappings
                                .fifo_nodes
                                .entry(fifo_read.fifo)
                                .or_default()
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
            Ok(ModuleInvocation {
                py_trace: trace.py_trace.clone(),
                start,
                end: current,
                submodules,
            })
        }

        let mut graph = DiGraph::new();
        let mut node_mappings = NodeMappings::default();
        let start_node = graph.add_node(0);
        let start = NodeWithDelay {
            node: start_node,
            delay: 0,
        };
        let top_module = build_cfg(&mut graph, &mut node_mappings, &trace, start)?;

        Ok(GlobalModel {
            graph,
            node_mappings,
            top_module,
            has_fifo_depths: false,
            has_axi_delays: false,
            has_updated_node_latencies: false,
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
        self.has_updated_node_latencies = false;
        Ok(())
    }

    fn set_axi_delays(&mut self, axi_delays: HashMap<AxiInterface, u64>) -> PyResult<()> {
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
            let mut consumed: u64 = 0;
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
            let mut consumed: u64 = 0;
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
        self.has_updated_node_latencies = false;
        Ok(())
    }

    fn get_latency(&mut self) -> PyResult<ClockCycle> {
        self.update_latencies()?;
        Ok(self.top_module.end.resolve(&self.graph))
    }

    fn get_latencies(&mut self) -> PyResult<Simulation> {
        self.update_latencies()?;
        Ok(Simulation::new(&self.graph, &self.top_module))
    }

    fn clone(&self) -> PyResult<Self> {
        Ok(Clone::clone(self))
    }
}

impl GlobalModel {
    fn update_latencies(&mut self) -> PyResult<()> {
        if self.has_updated_node_latencies {
            return Ok(());
        }

        let nodes = match algo::toposort(&self.graph, None) {
            Ok(nodes) => nodes,
            Err(_) => {
                return Err(PyValueError::new_err(
                    "simulation will deadlock. Please check FIFO depths",
                ))
            }
        };
        for node in nodes {
            self.graph[node] = self
                .graph
                .edges_directed(node, Direction::Incoming)
                .map(|edge| self.graph[edge.source()] + edge.weight())
                .max()
                .unwrap_or(0);
        }

        self.has_updated_node_latencies = true;
        Ok(())
    }
}

#[pymodule]
fn _core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<GlobalModel>()?;
    Ok(())
}
