use pyo3::{exceptions::PyValueError, prelude::*};

use crate::fifo::FifoIoNodes;
use crate::node::{NodeIndex, NodeWithDelay};

use super::edge_builder::IncompleteEdgeKey;
use super::tee::{Tee, TeeConsumer, TeeResult};

#[derive(Clone, Default)]
pub struct FifoBuilder {
    /// The builder for [FifoIoNodes::writes].
    writes: Vec<Option<NodeWithDelay>>,

    /// The builder for [FifoIoNodes::reads].
    reads: Vec<Option<NodeIndex>>,

    /// A [Tee] yielding keys of [FifoRaw] edges for this FIFO within
    /// [EdgeBuilder::incomplete_edges].
    ///
    /// [FifoRaw]: super::edge_builder::IncompleteEdgeType::FifoRaw
    /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
    raw_edges: Tee<IncompleteEdgeKey>,
}

/// A newly created FIFO write.
pub struct InsertedFifoWrite<'a> {
    pub index: usize,
    pub raw_edge: TeeResult<'a, IncompleteEdgeKey>,
}

/// A newly created FIFO read.
pub struct InsertedFifoRead<'a> {
    pub index: usize,
    pub raw_edge: TeeResult<'a, IncompleteEdgeKey>,
}

impl FifoBuilder {
    pub fn insert_write(&mut self) -> InsertedFifoWrite {
        let index = self.writes.len();
        self.writes.push(None);
        let raw_edge = self.raw_edges.next(TeeConsumer::A);
        InsertedFifoWrite { index, raw_edge }
    }

    pub fn insert_read(&mut self) -> InsertedFifoRead {
        let index = self.reads.len();
        self.reads.push(None);
        let raw_edge = self.raw_edges.next(TeeConsumer::B);
        InsertedFifoRead { index, raw_edge }
    }

    pub fn update_write(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.writes[index].is_none());
        self.writes[index] = Some(node);
    }

    pub fn update_read(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.reads[index].is_none());
        assert_eq!(node.delay, 0);
        self.reads[index] = Some(node.node);
    }
}

impl TryFrom<FifoBuilder> for FifoIoNodes {
    type Error = PyErr;

    fn try_from(builder: FifoBuilder) -> Result<FifoIoNodes, Self::Error> {
        let writes: Option<Box<[NodeWithDelay]>> = builder.writes.into_iter().collect();
        let reads: Option<Box<[NodeIndex]>> = builder.reads.into_iter().collect();
        let initialized_all_edges = builder.raw_edges.is_empty();
        match (writes, reads, initialized_all_edges) {
            (Some(writes), Some(reads), true) => Ok(FifoIoNodes { writes, reads }),
            _ => Err(PyValueError::new_err("incomplete FIFO edges remain")),
        }
    }
}
