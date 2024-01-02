use std::cmp;

use bitvec::bitvec;
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

#[pyclass]
#[derive(Clone)]
pub(crate) struct CompiledSimulation {
    pub graph: SimulationGraph,
    pub top_module: CompiledModule,
    pub fifo_nodes: FxHashMap<Fifo, FifoIoNodes>,
    pub axi_interface_nodes: FxHashMap<AxiInterface, AxiInterfaceIoNodes>,
    pub start_node: NodeIndex,
    pub end_node: NodeIndex,
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

#[derive(Clone, FromPyObject)]
pub struct SimulationParameters {
    fifo_depths: FxHashMap<Fifo, Option<usize>>,
    axi_delays: FxHashMap<AxiInterface, ClockCycle>,
    ap_ctrl_chain_top_port_count: Option<u32>,
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
    fn execute(&self, parameters: &SimulationParameters) -> PyResult<Vec<ClockCycle>> {
        let node_count = self.graph.node_offsets.len();
        let mut node_cycles = vec![0; node_count];
        let mut visited = bitvec![0; node_count];
        let mut visiting = bitvec![0; node_count];
        let mut stack = vec![Visit {
            node: self.end_node,
            preorder: true,
        }];

        while let Some(Visit { node, preorder }) = stack.pop() {
            let node_usize: usize = node.try_into().unwrap();
            if preorder {
                if visited[node_usize] {
                    continue;
                }
                if visiting[node_usize] {
                    return Err(PyValueError::new_err("deadlock detected"));
                }

                visiting.set(node_usize, true);
                stack.push(Visit {
                    node,
                    preorder: false,
                });

                for edge in self.graph.in_edges(node_usize) {
                    if let Some(edge) = edge.resolve(self, parameters)? {
                        stack.push(Visit {
                            node: edge.node,
                            preorder: true,
                        });
                    }
                    // TODO: at postorder, we need to compute new node_cycles[node]... how?
                }
            } else {
                // TODO: postorder
            }
        }

        Ok(node_cycles)
    }
}

impl SimulationGraph {
    fn in_edges(&self, node: usize) -> &[Edge] {
        let start = self.node_offsets[node];
        let end = self
            .node_offsets
            .get(node + 1)
            .copied()
            .unwrap_or_else(|| self.edges.len());
        &self.edges[start..end]
    }
}

impl SimulationParameters {
    pub(crate) fn get_fifo_depth(&self, fifo: &Fifo) -> PyResult<Option<usize>> {
        self.fifo_depths.get(fifo).copied().ok_or_else(|| {
            PyValueError::new_err(format!("no depth provided for FIFO with id {}", fifo.id))
        })
    }

    pub(crate) fn get_axi_delay(&self, interface: &AxiInterface) -> PyResult<ClockCycle> {
        let delay = self.axi_delays.get(interface).copied().ok_or_else(|| {
            PyValueError::new_err(format!(
                "no delay provided for AXI interface with address {:#010x}",
                interface.address
            ))
        })?;
        Ok(cmp::max(delay, 1))
    }
}

struct Visit {
    node: NodeIndex,
    preorder: bool,
}
