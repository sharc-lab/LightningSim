use slab::Slab;

use pyo3::{exceptions::PyValueError, prelude::*};

use crate::{
    axi_interface::AxiInterface,
    edge::{Edge, EdgeIndex},
    fifo::Fifo,
    node::{NodeIndex, NodeWithDelay},
    ClockCycle, SimulationGraph,
};

pub type IncompleteEdgeKey = usize;

#[derive(Clone, Default)]
pub struct EdgeBuilder {
    node_offsets: Vec<usize>,
    edges: Vec<Option<Edge>>,
    incomplete_edges: Slab<IncompleteEdge>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
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

    pub fn add_delay(&mut self, key: IncompleteEdgeKey, delay: ClockCycle) {
        self.incomplete_edges[key].delay += delay;
    }

    pub fn update_source(&mut self, key: IncompleteEdgeKey, source: NodeWithDelay) {
        use IncompleteEdgeEndpoints::{
            DestinationKnown, DestinationRedirected, EndpointsUnknown, SourceKnown,
            SourceRedirected,
        };
        let IncompleteEdge {
            endpoints, delay, ..
        } = &mut self.incomplete_edges[key];
        *delay += source.delay;
        match endpoints {
            EndpointsUnknown | SourceRedirected(..) => *endpoints = SourceKnown(Some(source.node)),
            &mut DestinationKnown(destination) => {
                let incomplete_edge = self.incomplete_edges.remove(key);
                if let Some(edge_index) = destination {
                    self.edges[edge_index] = Some(incomplete_edge.into_edge(source.node));
                }
            }
            &mut DestinationRedirected(redirected_key) => {
                let delay = *delay;
                self.incomplete_edges.remove(key);
                self.update_source(
                    redirected_key,
                    NodeWithDelay {
                        node: source.node,
                        delay,
                    },
                );
            }
            SourceKnown(..) => panic!("source already exists"),
        }
    }

    pub fn push_destination(&mut self, key: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::{
            DestinationKnown, DestinationRedirected, EndpointsUnknown, SourceKnown,
            SourceRedirected,
        };
        let IncompleteEdge {
            endpoints, delay, ..
        } = &mut self.incomplete_edges[key];
        let edge = match endpoints {
            EndpointsUnknown | DestinationRedirected(..) => {
                *endpoints = DestinationKnown(Some(self.edges.len()));
                None
            }
            &mut SourceKnown(source) => {
                let incomplete_edge = self.incomplete_edges.remove(key);
                match source {
                    Some(source) => Some(incomplete_edge.into_edge(source)),
                    None => return,
                }
            }
            &mut SourceRedirected(redirected_key) => {
                let delay = *delay;
                self.incomplete_edges.remove(key);
                self.add_delay(redirected_key, delay);
                return self.push_destination(redirected_key);
            }
            DestinationKnown(..) => panic!("destination already exists"),
        };
        self.edges.push(edge);
    }

    pub fn void_source(&mut self, key: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::{
            DestinationKnown, DestinationRedirected, EndpointsUnknown, SourceKnown,
            SourceRedirected,
        };
        let endpoints = &mut self.incomplete_edges[key].endpoints;
        match endpoints {
            EndpointsUnknown | SourceRedirected(..) => *endpoints = SourceKnown(None),
            DestinationKnown(..) => drop(self.incomplete_edges.remove(key)),
            &mut DestinationRedirected(redirected_key) => {
                self.incomplete_edges.remove(key);
                self.void_source(redirected_key);
            }
            SourceKnown(..) => panic!("source already exists"),
        }
    }

    pub fn void_destination(&mut self, key: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::{
            DestinationKnown, DestinationRedirected, EndpointsUnknown, SourceKnown,
            SourceRedirected,
        };
        let endpoints = &mut self.incomplete_edges[key].endpoints;
        match endpoints {
            EndpointsUnknown | DestinationRedirected(..) => *endpoints = DestinationKnown(None),
            SourceKnown(..) => drop(self.incomplete_edges.remove(key)),
            &mut SourceRedirected(redirected_key) => {
                self.incomplete_edges.remove(key);
                self.void_destination(redirected_key);
            }
            DestinationKnown(..) => panic!("destination already exists"),
        }
    }

    pub fn join(&mut self, source_edge: IncompleteEdgeKey, destination_edge: IncompleteEdgeKey) {
        use IncompleteEdgeEndpoints::{
            DestinationKnown, DestinationRedirected, EndpointsUnknown, SourceKnown,
            SourceRedirected,
        };
        let (
            IncompleteEdge {
                r#type: source_type,
                delay: source_delay,
                endpoints: source_endpoints,
            },
            IncompleteEdge {
                r#type: destination_type,
                delay: destination_delay,
                endpoints: destination_endpoints,
            },
        ) = self
            .incomplete_edges
            .get2_mut(source_edge, destination_edge)
            .expect("join on nonexistent edge");
        assert_eq!(
            source_type, destination_type,
            "cannot join edges of different types"
        );
        match (&source_endpoints, &destination_endpoints) {
            (SourceRedirected(..), _) | (_, DestinationRedirected(..)) => {
                panic!("cannot join an edge already joined to another edge");
            }
            (DestinationKnown(..) | DestinationRedirected(..), _) => {
                panic!("destination already exists on source edge");
            }
            (_, SourceKnown(..) | SourceRedirected(..)) => {
                panic!("source already exists on destination edge");
            }
            (EndpointsUnknown, EndpointsUnknown) => {
                *source_endpoints = DestinationRedirected(destination_edge);
                *destination_endpoints = SourceRedirected(source_edge);
            }
            (&&mut SourceKnown(source_node), EndpointsUnknown) => {
                *destination_endpoints = SourceKnown(source_node);
                *destination_delay += *source_delay;
                self.incomplete_edges.remove(source_edge);
            }
            (EndpointsUnknown, &&mut DestinationKnown(edge_index)) => {
                *source_endpoints = DestinationKnown(edge_index);
                *source_delay += *destination_delay;
                self.incomplete_edges.remove(destination_edge);
            }
            (&&mut SourceKnown(source_node), &&mut DestinationKnown(edge_index)) => {
                *destination_delay += *source_delay;
                self.incomplete_edges.remove(source_edge);
                let incomplete_edge = self.incomplete_edges.remove(destination_edge);
                if let (Some(source_node), Some(edge_index)) = (source_node, edge_index) {
                    self.edges[edge_index] = Some(incomplete_edge.into_edge(source_node));
                }
            }
        }
    }
}

impl TryFrom<EdgeBuilder> for SimulationGraph {
    type Error = PyErr;

    fn try_from(value: EdgeBuilder) -> Result<Self, Self::Error> {
        let edge_iter_1 = value.edges.into_iter();
        let edge_iter_2 = edge_iter_1.clone();
        let edges: Box<[Edge]> = edge_iter_1.flatten().collect();
        let voided_count: Box<[usize]> = edge_iter_2
            .scan(0, |voided_count, edge| {
                let current_voided_count = *voided_count;
                if edge.is_none() {
                    *voided_count += 1;
                }
                Some(current_voided_count)
            })
            .collect();
        let node_offsets = value
            .node_offsets
            .into_iter()
            .map(|offset| offset - voided_count[offset])
            .collect();
        value
            .incomplete_edges
            .is_empty()
            .then_some(SimulationGraph {
                node_offsets,
                edges,
            })
            .ok_or_else(|| PyValueError::new_err("incomplete edges remain"))
    }
}

#[derive(Clone, Debug)]
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
        use IncompleteEdgeType::{AxiRctl, AxiRead, AxiWriteResp, ControlFlow, FifoRaw};
        let u = NodeWithDelay {
            node: source,
            delay: self.delay,
        };
        match self.r#type {
            ControlFlow => Edge::ControlFlow(u),
            FifoRaw(fifo) => Edge::FifoRaw { u, fifo },
            AxiRctl(interface) => Edge::AxiRctl { u, interface },
            AxiRead(interface) => Edge::AxiRead { u, interface },
            AxiWriteResp(interface) => Edge::AxiWriteResp { u, interface },
        }
    }
}

#[derive(Clone, Debug)]
enum IncompleteEdgeEndpoints {
    EndpointsUnknown,
    SourceKnown(Option<NodeIndex>),
    SourceRedirected(IncompleteEdgeKey),
    DestinationKnown(Option<EdgeIndex>),
    DestinationRedirected(IncompleteEdgeKey),
}

impl Default for IncompleteEdgeEndpoints {
    fn default() -> Self {
        Self::EndpointsUnknown
    }
}
