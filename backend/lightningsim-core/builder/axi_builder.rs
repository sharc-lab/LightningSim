use std::collections::VecDeque;
use std::mem;

use pyo3::{exceptions::PyValueError, prelude::*};

use super::edge_builder::IncompleteEdgeKey;
use crate::{
    axi_interface::{
        AxiAddress, AxiAddressRange, AxiGenericIoNode, AxiInterfaceIoNodes, MAX_RCTL_DEPTH,
    },
    node::NodeWithDelay,
};

#[derive(Clone)]
pub struct AxiBuilder {
    /// The builder for [AxiInterfaceIoNodes::readreqs].
    readreqs: Vec<AxiGenericIoOptionalNode>,

    /// The builder for [AxiInterfaceIoNodes::reads].
    reads: Vec<AxiGenericIoOptionalNode>,

    /// The builder for [AxiInterfaceIoNodes::writereqs].
    writereqs: Vec<AxiGenericIoOptionalNode>,

    /// The builder for [AxiInterfaceIoNodes::writes].
    writes: Vec<AxiGenericIoOptionalNode>,

    /// The builder for [AxiInterfaceIoNodes::writeresps].
    writeresps: Vec<Option<NodeWithDelay>>,

    read_edge: Option<IncompleteEdgeKey>,
    rctl_edge: Option<IncompleteEdgeKey>,
    writeresp_edge: IncompleteEdgeKey,

    current_read: AxiAddressRange,
    readreq_reads_remaining: u32,
    current_write: AxiAddressRange,
    writereq_writes_remaining: u32,
    rctl_depth: usize,
    rctl_bursts: VecDeque<RctlBurst>,
}

#[derive(Clone, Copy)]
struct AxiGenericIoOptionalNode {
    node: Option<NodeWithDelay>,
    range: AxiAddressRange,
}

#[derive(Clone, FromPyObject)]
pub struct AxiRequestRange {
    pub offset: AxiAddress,
    pub increment: AxiAddress,
    pub count: u32,
}

/// A newly created AXI read request.
pub struct InsertedAxiReadReq<'a> {
    pub index: usize,
    pub read_edge: ReadEdgeNeeded<'a>,
    pub voided_rctl_edges: VoidedRctlEdgeIter<'a>,
}

/// A newly created AXI read.
pub struct InsertedAxiRead<'a> {
    pub index: usize,
    pub read_edge: Option<IncompleteEdgeKey>,
    pub rctl_out_edge: Option<RctlEdgeNeeded<'a>>,
    pub rctl_in_edge: Option<IncompleteEdgeKey>,
}

/// A newly created AXI write request.
pub struct InsertedAxiWriteReq {
    pub index: usize,
}

/// A newly created AXI write.
pub struct InsertedAxiWrite<'a> {
    pub index: usize,
    pub writeresp_edge: Option<WriteRespEdgeNeeded<'a>>,
}

/// A newly created AXI write response.
pub struct InsertedAxiWriteResp {
    pub index: usize,
    pub writeresp_edge: IncompleteEdgeKey,
}

#[must_use]
pub struct ReadEdgeNeeded<'a> {
    builder: &'a mut AxiBuilder,
}

#[must_use]
pub struct RctlEdgeNeeded<'a> {
    builder: &'a mut AxiBuilder,
}

#[must_use]
pub struct WriteRespEdgeNeeded<'a> {
    builder: &'a mut AxiBuilder,
}

#[must_use]
pub struct VoidedRctlEdgeIter<'a> {
    builder: &'a mut AxiBuilder,
}

impl AxiBuilder {
    pub fn new() -> Self {
        Self {
            readreqs: Vec::new(),
            reads: Vec::new(),
            writereqs: Vec::new(),
            writes: Vec::new(),
            writeresps: Vec::new(),
            read_edge: None,
            rctl_edge: None,
            writeresp_edge: 0,
            current_read: AxiAddressRange {
                offset: 0,
                length: 0,
            },
            readreq_reads_remaining: 0,
            current_write: AxiAddressRange {
                offset: 0,
                length: 0,
            },
            writereq_writes_remaining: 0,
            rctl_depth: 0,
            rctl_bursts: VecDeque::with_capacity(MAX_RCTL_DEPTH),
        }
    }

    pub fn insert_readreq(&mut self, request: AxiRequestRange) -> InsertedAxiReadReq {
        let range = request.range();
        let index = self.readreqs.len();
        self.readreqs
            .push(AxiGenericIoOptionalNode { node: None, range });

        self.current_read = request.front();
        self.readreq_reads_remaining = request.count;

        let burst_count = range.burst_count();
        self.rctl_bursts.push_back(RctlBurst::new(burst_count));
        self.rctl_depth += burst_count;
        self.pop_rctl_edge();

        InsertedAxiReadReq {
            index,
            read_edge: ReadEdgeNeeded { builder: self },
            voided_rctl_edges: VoidedRctlEdgeIter { builder: self },
        }
    }

    pub fn insert_writereq(&mut self, request: AxiRequestRange) -> InsertedAxiWriteReq {
        let range = request.range();
        let index = self.writereqs.len();
        self.writereqs
            .push(AxiGenericIoOptionalNode { node: None, range });

        self.current_write = request.front();
        self.writereq_writes_remaining = request.count;

        InsertedAxiWriteReq { index }
    }

    pub fn insert_read(&mut self) -> InsertedAxiRead {
        let range = self.current_read;
        self.current_read = range + range.length;

        let index = self.reads.len();
        self.reads
            .push(AxiGenericIoOptionalNode { node: None, range });

        self.readreq_reads_remaining -= 1;
        let is_last_of_readreq = self.readreq_reads_remaining == 0;

        InsertedAxiRead {
            index,
            read_edge: self.read_edge.take(),
            rctl_out_edge: if is_last_of_readreq {
                Some(RctlEdgeNeeded { builder: self })
            } else {
                None
            },
            rctl_in_edge: self.rctl_edge.take(),
        }
    }

    pub fn insert_write(&mut self) -> InsertedAxiWrite {
        let range = self.current_write;
        self.current_write = range + range.length;

        let index = self.writes.len();
        self.writes
            .push(AxiGenericIoOptionalNode { node: None, range });

        self.writereq_writes_remaining -= 1;
        let is_last_of_writereq = self.writereq_writes_remaining == 0;

        InsertedAxiWrite {
            index,
            writeresp_edge: if is_last_of_writereq {
                Some(WriteRespEdgeNeeded { builder: self })
            } else {
                None
            },
        }
    }

    pub fn insert_writeresp(&mut self) -> InsertedAxiWriteResp {
        let index = self.writeresps.len();
        self.writeresps.push(None);

        InsertedAxiWriteResp {
            index,
            writeresp_edge: self.writeresp_edge,
        }
    }

    pub fn update_readreq(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.readreqs[index].node.is_none());
        self.readreqs[index].node = Some(node);
    }

    pub fn update_writereq(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.writereqs[index].node.is_none());
        self.writereqs[index].node = Some(node);
    }

    pub fn update_read(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.reads[index].node.is_none());
        self.reads[index].node = Some(node);
    }

    pub fn update_write(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.writes[index].node.is_none());
        self.writes[index].node = Some(node);
    }

    pub fn update_writeresp(&mut self, index: usize, node: NodeWithDelay) {
        debug_assert!(self.writeresps[index].is_none());
        self.writeresps[index] = Some(node);
    }

    /// Returns an iterator of edges to void.
    pub fn finish(&mut self) -> impl Iterator<Item = IncompleteEdgeKey> {
        mem::take(&mut self.rctl_bursts)
            .into_iter()
            .filter_map(|burst| burst.rctl_edge)
    }

    fn pop_rctl_edge(&mut self) -> Option<IncompleteEdgeKey> {
        if self.rctl_depth < MAX_RCTL_DEPTH {
            return None;
        }
        let burst = self.rctl_bursts.pop_front().unwrap();
        self.rctl_depth -= burst.burst_count;
        let mut rctl_edge = Some(burst.rctl_edge.unwrap());
        mem::swap(&mut rctl_edge, &mut self.rctl_edge);
        rctl_edge
    }
}

impl Default for AxiBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl TryFrom<AxiBuilder> for AxiInterfaceIoNodes {
    type Error = PyErr;

    fn try_from(builder: AxiBuilder) -> Result<AxiInterfaceIoNodes, Self::Error> {
        let readreqs: Option<Box<[AxiGenericIoNode]>> = builder
            .readreqs
            .into_iter()
            .map(|readreq| readreq.into())
            .collect();
        let reads: Option<Box<[AxiGenericIoNode]>> =
            builder.reads.into_iter().map(|read| read.into()).collect();
        let writereqs: Option<Box<[AxiGenericIoNode]>> = builder
            .writereqs
            .into_iter()
            .map(|writereq| writereq.into())
            .collect();
        let writes: Option<Box<[AxiGenericIoNode]>> = builder
            .writes
            .into_iter()
            .map(|write| write.into())
            .collect();
        let writeresps: Option<Box<[NodeWithDelay]>> = builder.writeresps.into_iter().collect();
        let initialized_all_edges = builder.read_edge.is_none()
            && builder.rctl_edge.is_none()
            && builder.rctl_bursts.is_empty();
        match (
            readreqs,
            reads,
            writereqs,
            writes,
            writeresps,
            initialized_all_edges,
        ) {
            (
                Some(readreqs),
                Some(reads),
                Some(writereqs),
                Some(writes),
                Some(writeresps),
                true,
            ) => Ok(AxiInterfaceIoNodes {
                readreqs,
                reads,
                writereqs,
                writes,
                writeresps,
            }),
            _ => Err(PyValueError::new_err("incomplete edges remain")),
        }
    }
}

impl From<AxiGenericIoOptionalNode> for Option<AxiGenericIoNode> {
    fn from(value: AxiGenericIoOptionalNode) -> Self {
        value.node.map(|node| AxiGenericIoNode {
            node,
            range: value.range,
        })
    }
}

impl AxiRequestRange {
    fn range(&self) -> AxiAddressRange {
        self.into()
    }

    fn front(&self) -> AxiAddressRange {
        AxiAddressRange {
            offset: self.offset,
            length: self.increment,
        }
    }
}

impl From<&AxiRequestRange> for AxiAddressRange {
    fn from(request: &AxiRequestRange) -> Self {
        let count: AxiAddress = request.count.into();
        AxiAddressRange {
            offset: request.offset,
            length: request.increment * count,
        }
    }
}

impl<'a> ReadEdgeNeeded<'a> {
    pub fn provide(self, edge: IncompleteEdgeKey) {
        self.builder.read_edge = Some(edge);
    }
}

impl<'a> RctlEdgeNeeded<'a> {
    pub fn provide(self, edge: IncompleteEdgeKey) {
        self.builder.rctl_bursts.back_mut().unwrap().rctl_edge = Some(edge);
    }
}

impl<'a> WriteRespEdgeNeeded<'a> {
    pub fn provide(self, edge: IncompleteEdgeKey) {
        self.builder.writeresp_edge = edge;
    }
}

impl<'a> Iterator for VoidedRctlEdgeIter<'a> {
    type Item = IncompleteEdgeKey;

    #[must_use]
    fn next(&mut self) -> Option<Self::Item> {
        self.builder.pop_rctl_edge()
    }
}

#[derive(Clone)]
struct RctlBurst {
    burst_count: usize,
    rctl_edge: Option<IncompleteEdgeKey>,
}

impl RctlBurst {
    fn new(burst_count: usize) -> Self {
        Self {
            burst_count,
            rctl_edge: None,
        }
    }
}
