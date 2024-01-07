use pyo3::{exceptions::PyValueError, prelude::*};

use super::{axi_rctl::RctlTransaction, edge_builder::IncompleteEdgeKey};
use crate::{
    axi_interface::{AxiAddress, AxiAddressRange, AxiGenericIoNode, AxiInterfaceIoNodes},
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

    first_read: Option<FirstReadData>,
    writeresp_edge: IncompleteEdgeKey,

    current_read: AxiAddressRange,
    readreq_reads_remaining: u32,
    readreq_rctl_out_edge: IncompleteEdgeKey,
    current_write: AxiAddressRange,
    writereq_writes_remaining: u32,
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
pub struct InsertedAxiReadReq {
    pub index: usize,
    pub rctl_txn: RctlTransaction,
}

/// A newly created AXI read.
pub struct InsertedAxiRead {
    pub index: usize,
    pub first_read: Option<FirstReadData>,
    pub rctl_out_edge: Option<IncompleteEdgeKey>,
}

#[derive(Clone, Debug)]
pub struct FirstReadData {
    pub read_edge: IncompleteEdgeKey,
    pub rctl_in_edge: IncompleteEdgeKey,
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
pub struct WriteRespEdgeNeeded<'a> {
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
            first_read: None,
            writeresp_edge: 0,
            current_read: AxiAddressRange {
                offset: 0,
                length: 0,
            },
            readreq_reads_remaining: 0,
            readreq_rctl_out_edge: 0,
            current_write: AxiAddressRange {
                offset: 0,
                length: 0,
            },
            writereq_writes_remaining: 0,
        }
    }

    pub fn insert_readreq(
        &mut self,
        request: AxiRequestRange,
        read_edge: IncompleteEdgeKey,
        rctl_in_edge: IncompleteEdgeKey,
        rctl_out_edge: IncompleteEdgeKey,
    ) -> InsertedAxiReadReq {
        let range = request.range();
        let index = self.readreqs.len();
        self.readreqs
            .push(AxiGenericIoOptionalNode { node: None, range });

        self.current_read = request.front();
        self.first_read = Some(FirstReadData {
            read_edge,
            rctl_in_edge,
        });
        self.readreq_rctl_out_edge = rctl_out_edge;
        self.readreq_reads_remaining = request.count;

        InsertedAxiReadReq {
            index,
            rctl_txn: RctlTransaction {
                burst_count: range.burst_count(),
                in_edge: rctl_in_edge,
                out_edge: rctl_out_edge,
            },
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
        let first_read = self.first_read.take();
        let rctl_out_edge = match is_last_of_readreq {
            true => Some(self.readreq_rctl_out_edge),
            false => None,
        };

        InsertedAxiRead {
            index,
            first_read,
            rctl_out_edge,
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
        let initialized_all_edges = builder.first_read.is_none()
            && builder.readreq_reads_remaining == 0
            && builder.writereq_writes_remaining == 0;
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
            _ => Err(PyValueError::new_err("incomplete AXI edges remain")),
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

impl<'a> WriteRespEdgeNeeded<'a> {
    pub fn provide(self, edge: IncompleteEdgeKey) {
        self.builder.writeresp_edge = edge;
    }
}
