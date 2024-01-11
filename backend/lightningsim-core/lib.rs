mod axi_interface;
mod builder;
mod edge;
mod fifo;
mod node;

use std::{cmp, fmt, iter, sync::Arc};

use bitvec::bitvec;
use pyo3::{exceptions::PyValueError, prelude::*};
use rayon::prelude::*;
use rustc_hash::FxHashMap;

use crate::{
    axi_interface::{
        AxiAddress, AxiAddressRange, AxiGenericIo, AxiInterface, AxiInterfaceIo,
        AxiInterfaceIoNodes,
    },
    builder::SimulationBuilder,
    edge::Edge,
    fifo::{Fifo, FifoId, FifoIo, FifoIoNodes},
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
    pub(crate) fifo_nodes: Arc<FxHashMap<Fifo, FifoIoNodes>>,
    pub(crate) axi_interface_nodes: Arc<FxHashMap<AxiInterface, AxiInterfaceIoNodes>>,
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
    FifoWidthNotProvided(FifoId),
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
    node_cycles: Vec<ClockCycle>,
    #[pyo3(get)]
    top_module: SimulatedModule,
    fifo_nodes: Arc<FxHashMap<Fifo, FifoIoNodes>>,
    axi_interface_nodes: Arc<FxHashMap<AxiInterface, AxiInterfaceIoNodes>>,
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

#[pyclass]
#[derive(Clone)]
pub struct DsePoint {
    #[pyo3(get)]
    latency: Option<ClockCycle>,
    #[pyo3(get)]
    bram_count: usize,
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
    fn execute(&self, py: Python<'_>, parameters: SimulationParameters) -> PyResult<Simulation> {
        py.allow_threads(|| {
            let node_cycles = self.resolve(&parameters)?;
            let top_module = SimulatedModule::new(
                &node_cycles,
                &self.top_module,
                parameters.ap_ctrl_chain_top_port_count.into(),
            );
            Ok(Simulation {
                node_cycles,
                top_module,
                fifo_nodes: self.fifo_nodes.clone(),
                axi_interface_nodes: self.axi_interface_nodes.clone(),
            })
        })
    }

    fn dse(
        &self,
        py: Python<'_>,
        base_config: SimulationParameters,
        fifo_widths: FxHashMap<FifoId, u32>,
        fifo_design_space: Vec<FxHashMap<FifoId, usize>>,
    ) -> PyResult<Vec<DsePoint>> {
        Ok(py.allow_threads(|| {
            fifo_design_space
                .into_par_iter()
                .map(|config| -> Result<DsePoint, SimulationError> {
                    let mut fifo_depths = base_config.fifo_depths.clone();
                    fifo_depths.extend(config.into_iter().map(|(id, depth)| (id, Some(depth))));
                    let bram_count = fifo_depths
                        .iter()
                        .filter_map(|(fifo_id, depth)| depth.map(|depth| (fifo_id, depth)))
                        .try_fold(0, |bram_count, (fifo_id, depth)| {
                            fifo_widths
                                .get(fifo_id)
                                .copied()
                                .ok_or(SimulationError::FifoWidthNotProvided(*fifo_id))
                                .map(|width| bram_count + fifo::get_bram_count(width, depth))
                        })?;
                    let parameters = SimulationParameters {
                        fifo_depths,
                        axi_delays: base_config.axi_delays.clone(),
                        ap_ctrl_chain_top_port_count: base_config.ap_ctrl_chain_top_port_count,
                    };
                    let latency = match self.resolve(&parameters) {
                        Ok(node_cycles) => Ok(Some(self.top_module.end.resolve(&node_cycles))),
                        Err(SimulationError::DeadlockDetected) => Ok(None),
                        Err(error) => Err(error),
                    }?;
                    Ok(DsePoint {
                        latency,
                        bram_count,
                    })
                })
                .collect::<Result<_, _>>()
        })?)
    }

    fn get_fifo_design_space(&self, fifo_ids: Vec<FifoId>, width: u32) -> PyResult<Vec<usize>> {
        let write_count = fifo_ids
            .into_iter()
            .map(|fifo_id| {
                self.fifo_nodes
                    .get(&Fifo { id: fifo_id })
                    .map(|fifo_io| fifo_io.writes.len())
                    .ok_or_else(|| PyValueError::new_err(format!("no FIFO with id {}", fifo_id)))
            })
            .try_fold(0, |max, current| {
                current.map(|current| cmp::max(max, current))
            })?;
        Ok(fifo::get_design_space(width, write_count).collect())
    }

    fn node_count(&self) -> usize {
        self.graph.node_offsets.len()
    }

    fn edge_count(&self) -> usize {
        self.graph.edges.len()
    }
}

#[pymethods]
impl Simulation {
    #[getter]
    fn fifo_io(&self) -> FxHashMap<Fifo, FifoIo> {
        self.fifo_nodes
            .iter()
            .map(|(fifo, nodes)| (*fifo, FifoIo::new(nodes, &self.node_cycles)))
            .collect()
    }

    #[getter]
    fn axi_io(&self) -> FxHashMap<AxiInterface, AxiInterfaceIo> {
        self.axi_interface_nodes
            .iter()
            .map(|(interface, nodes)| (*interface, AxiInterfaceIo::new(nodes, &self.node_cycles)))
            .collect()
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
                let num_parameters: ClockCycle = num_parameters.into();
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
            Self::FifoWidthNotProvided(fifo_id) => {
                write!(f, "no width provided for FIFO with id {}", fifo_id)
            }
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
    m.add_class::<DsePoint>()?;
    m.add_class::<Fifo>()?;
    m.add_class::<FifoIo>()?;
    m.add_class::<AxiInterface>()?;
    m.add_class::<AxiInterfaceIo>()?;
    m.add_class::<AxiGenericIo>()?;
    m.add_class::<AxiAddressRange>()?;
    Ok(())
}
