use slab::Slab;

use pyo3::{exceptions::PyValueError, prelude::*};

use crate::{
    axi_interface::AxiInterface,
    edge::{Edge, EdgeIndex},
    fifo::Fifo,
    node::{NodeIndex, NodeWithDelay},
    simulation::{ClockCycle, SimulationGraph},
};

pub type IncompleteEdgeKey = usize;

#[derive(Clone, Default)]
pub struct EdgeBuilder {
    node_offsets: Vec<usize>,
    edges: Vec<Option<Edge>>,
    incomplete_edges: Slab<IncompleteEdge>,
}

#[derive(Clone)]
pub enum IncompleteEdgeType {
    ControlFlow,
    FifoRaw(Fifo),
    AxiRctl(AxiInterface),
    AxiRead(AxiInterface),
    AxiWriteResp(AxiInterface),
}

impl EdgeBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert_node(&mut self) -> NodeIndex {
        let node_index = self.node_offsets.len().try_into().expect("too many nodes");
        self.node_offsets.push(self.edges.len());
        node_index
    }

    pub fn insert_edge(&mut self, r#type: IncompleteEdgeType) -> IncompleteEdgeKey {
        self.incomplete_edges.insert(IncompleteEdge::new(r#type))
    }

    pub fn push_edge(&mut self, edge: Edge) {
        self.edges.push(Some(edge));
    }

    pub fn update_source(&mut self, key: IncompleteEdgeKey, source: NodeWithDelay) {
        use IncompleteEdgeEndpoints::*;
        let incomplete_edge = &mut self.incomplete_edges[key];
        incomplete_edge.delay += source.delay;
        let destination = match incomplete_edge.endpoints {
            EndpointsUnknown => None,
            DestinationKnown(destination) => Some(destination),
            SourceKnown(_) => panic!("source already exists"),
        };
        match destination {
            None => incomplete_edge.endpoints = SourceKnown(source.node),
            Some(destination) => {
                let incomplete_edge = self.incomplete_edges.remove(key);
                if let Some(edge_index) = destination {
                    self.edges[edge_index] = Some(incomplete_edge.into_edge(source.node));
                }
            }
        }
    }

    pub fn add_delay(&mut self, key: IncompleteEdgeKey, delay: ClockCycle) {
        self.incomplete_edges[key].delay += delay;
    }

    pub fn push_destination(&mut self, key: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::*;
        let incomplete_edge = &mut self.incomplete_edges[key];
        let source = match incomplete_edge.endpoints {
            EndpointsUnknown => None,
            SourceKnown(source) => Some(source),
            DestinationKnown(..) => panic!("destination already exists"),
        };
        let edge = match source {
            None => {
                incomplete_edge.endpoints = DestinationKnown(Some(self.edges.len()));
                None
            }
            Some(source) => Some(self.incomplete_edges.remove(key).into_edge(source)),
        };
        self.edges.push(edge);
    }

    pub fn void_destination(&mut self, key: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::*;
        let incomplete_edge = &mut self.incomplete_edges[key];
        match incomplete_edge.endpoints {
            EndpointsUnknown => incomplete_edge.endpoints = DestinationKnown(None),
            SourceKnown(..) => drop(self.incomplete_edges.remove(key)),
            DestinationKnown(..) => panic!("destination already exists"),
        }
    }
}

impl TryFrom<EdgeBuilder> for SimulationGraph {
    type Error = PyErr;

    fn try_from(value: EdgeBuilder) -> Result<Self, Self::Error> {
        let node_offsets = value.node_offsets.into_boxed_slice();
        let edges: Option<Box<[Edge]>> = value.edges.into_iter().collect();
        let all_edges_completed = value.incomplete_edges.is_empty();
        match (edges, all_edges_completed) {
            (Some(edges), true) => Ok(SimulationGraph {
                node_offsets,
                edges,
            }),
            _ => Err(PyValueError::new_err("incomplete edges remain")),
        }
    }
}

#[derive(Clone)]
struct IncompleteEdge {
    r#type: IncompleteEdgeType,
    delay: ClockCycle,
    endpoints: IncompleteEdgeEndpoints,
}

impl IncompleteEdge {
    fn new(r#type: IncompleteEdgeType) -> Self {
        Self {
            r#type,
            delay: 0,
            endpoints: IncompleteEdgeEndpoints::default(),
        }
    }
}

impl IncompleteEdge {
    fn into_edge(self, source: NodeIndex) -> Edge {
        let u = NodeWithDelay {
            node: source,
            delay: self.delay,
        };
        use IncompleteEdgeType::*;
        match self.r#type {
            ControlFlow => Edge::ControlFlow(u),
            FifoRaw(fifo) => Edge::FifoRaw { u, fifo },
            AxiRctl(interface) => Edge::AxiRctl { u, interface },
            AxiRead(interface) => Edge::AxiRead { u, interface },
            AxiWriteResp(interface) => Edge::AxiWriteResp { u, interface },
        }
    }
}

#[derive(Clone)]
enum IncompleteEdgeEndpoints {
    EndpointsUnknown,
    SourceKnown(NodeIndex),
    DestinationKnown(Option<EdgeIndex>),
}

impl Default for IncompleteEdgeEndpoints {
    fn default() -> Self {
        Self::EndpointsUnknown
    }
}
