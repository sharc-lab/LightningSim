use std::{collections::VecDeque, mem};

use crate::axi_interface::{RctlDepth, MAX_RCTL_DEPTH};

use super::edge_builder::{EdgeBuilder, IncompleteEdgeKey};

#[derive(Clone, Default)]
pub struct AxiRctl {
    state: AxiRctlState,
    depth: RctlDepth,
}

#[derive(Clone, Copy, Debug)]
pub struct RctlTransaction {
    pub burst_count: RctlDepth,
    pub in_edge: IncompleteEdgeKey,
    pub out_edge: IncompleteEdgeKey,
}

#[derive(Clone)]
enum AxiRctlState {
    WithinCapacity(VecDeque<RctlTransaction>),
    Overflowed {
        head: Box<[RctlHeadTransaction]>,
        tail: VecDeque<RctlTransaction>,
    },
}

#[derive(Clone, Copy)]
struct RctlHeadTransaction {
    burst_count: RctlDepth,
    in_edge: IncompleteEdgeKey,
}

impl AxiRctl {
    pub fn push(&mut self, edge_builder: &mut EdgeBuilder, transaction: RctlTransaction) {
        use AxiRctlState::*;

        let mut blocking_out_edge = None;
        while self.depth >= MAX_RCTL_DEPTH {
            let RctlTransaction {
                burst_count,
                in_edge: _,
                out_edge,
            } = match &mut self.state {
                WithinCapacity(queue) => {
                    let head = queue.iter().map(|txn| txn.into()).collect();
                    let front = queue.pop_front().unwrap();
                    let tail = mem::take(queue);
                    self.state = Overflowed { head, tail };
                    front
                }
                Overflowed { tail, .. } => tail.pop_front().unwrap(),
            };
            self.depth -= burst_count;

            if let Some(unused_edge) = blocking_out_edge.replace(out_edge) {
                edge_builder.void_destination(unused_edge);
            }
        }

        if let Some(blocking_out_edge) = blocking_out_edge {
            edge_builder.join(blocking_out_edge, transaction.in_edge);
        } else if let Overflowed { .. } = &self.state {
            edge_builder.void_source(transaction.in_edge);
        }

        self.depth += transaction.burst_count;
        let queue = match &mut self.state {
            WithinCapacity(queue) => queue,
            Overflowed { tail, .. } => tail,
        };
        queue.push_back(transaction);
    }

    pub fn extend(&mut self, edge_builder: &mut EdgeBuilder, other: AxiRctl) {
        use AxiRctlState::*;
        match other.state {
            WithinCapacity(queue) => {
                for transaction in queue {
                    self.push(edge_builder, transaction);
                }
            }
            Overflowed { head, tail } => {
                for transaction in head.into_iter() {
                    self.push(
                        edge_builder,
                        RctlTransaction {
                            burst_count: transaction.burst_count,
                            in_edge: transaction.in_edge,
                            out_edge: 0,
                        },
                    );
                }
                let head = match &mut self.state {
                    Overflowed { head, .. } => mem::take(head),
                    WithinCapacity(_) => panic!(
                        "AxiRctl::extend was called with overflowed AxiRctl but did not overflow"
                    ),
                };
                *self = Self {
                    state: Overflowed { head, tail },
                    depth: other.depth,
                }
            }
        }
    }

    pub fn finish(self, edge_builder: &mut EdgeBuilder) {
        use AxiRctlState::*;
        match self.state {
            WithinCapacity(queue) => {
                for transaction in queue {
                    edge_builder.void_source(transaction.in_edge);
                    edge_builder.void_destination(transaction.out_edge);
                }
            }
            Overflowed { head, tail } => {
                for transaction in head.into_iter() {
                    edge_builder.void_source(transaction.in_edge);
                }
                for transaction in tail {
                    edge_builder.void_destination(transaction.out_edge);
                }
            }
        };
    }
}

impl Default for AxiRctlState {
    fn default() -> Self {
        Self::WithinCapacity(VecDeque::with_capacity(MAX_RCTL_DEPTH.into()))
    }
}

impl From<&RctlTransaction> for RctlHeadTransaction {
    fn from(value: &RctlTransaction) -> Self {
        Self {
            burst_count: value.burst_count,
            in_edge: value.in_edge,
        }
    }
}
