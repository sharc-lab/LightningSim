use std::ops;

use pyo3::prelude::*;

use crate::{node::NodeWithDelay, ClockCycle};

pub const AXI_READ_OVERHEAD: ClockCycle = 12;
pub const AXI_WRITE_OVERHEAD: ClockCycle = 7;
pub const MAX_RCTL_DEPTH: usize = 16;

pub type AxiAddress = u64;

#[pyclass]
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct AxiInterface {
    #[pyo3(get)]
    pub address: AxiAddress,
}

#[pyclass]
#[derive(Clone, Copy)]
pub struct AxiAddressRange {
    #[pyo3(get)]
    pub offset: AxiAddress,
    #[pyo3(get)]
    pub length: AxiAddress,
}

impl AxiAddressRange {
    pub fn burst_count(&self) -> usize {
        (((self.offset + self.length - 1) / 4096) - (self.offset / 4096) + 1)
            .try_into()
            .unwrap()
    }
}

impl ops::Add<AxiAddress> for AxiAddressRange {
    type Output = AxiAddressRange;

    fn add(self, rhs: AxiAddress) -> Self::Output {
        AxiAddressRange {
            offset: self.offset + rhs,
            length: self.length,
        }
    }
}

#[derive(Clone, Copy)]
pub struct AxiGenericIoNode {
    pub(crate) node: NodeWithDelay,
    pub(crate) range: AxiAddressRange,
}

#[derive(Clone, Default)]
pub struct AxiInterfaceIoNodes {
    pub(crate) readreqs: Box<[AxiGenericIoNode]>,
    pub(crate) reads: Box<[AxiGenericIoNode]>,
    pub(crate) writereqs: Box<[AxiGenericIoNode]>,
    pub(crate) writes: Box<[AxiGenericIoNode]>,
    pub(crate) writeresps: Box<[NodeWithDelay]>,
}

#[pyclass]
#[derive(Clone)]
pub struct AxiGenericIo {
    #[pyo3(get)]
    pub time: ClockCycle,
    #[pyo3(get)]
    pub range: AxiAddressRange,
}

#[pyclass]
#[derive(Clone)]
pub struct AxiInterfaceIo {
    #[pyo3(get)]
    pub readreqs: Vec<AxiGenericIo>,
    #[pyo3(get)]
    pub reads: Vec<AxiGenericIo>,
    #[pyo3(get)]
    pub writereqs: Vec<AxiGenericIo>,
    #[pyo3(get)]
    pub writes: Vec<AxiGenericIo>,
    #[pyo3(get)]
    pub writeresps: Vec<ClockCycle>,
}

impl AxiInterfaceIo {
    pub fn new<T>(axi_io_nodes: &AxiInterfaceIoNodes, node_cycles: &T) -> Self
    where
        T: ops::Index<usize, Output = ClockCycle> + ?Sized,
    {
        AxiInterfaceIo {
            readreqs: axi_io_nodes
                .readreqs
                .iter()
                .map(|AxiGenericIoNode { node, range }| AxiGenericIo {
                    time: node.resolve(node_cycles),
                    range: *range,
                })
                .collect(),
            reads: axi_io_nodes
                .reads
                .iter()
                .map(|AxiGenericIoNode { node, range }| AxiGenericIo {
                    time: node.resolve(node_cycles),
                    range: *range,
                })
                .collect(),
            writereqs: axi_io_nodes
                .writereqs
                .iter()
                .map(|AxiGenericIoNode { node, range }| AxiGenericIo {
                    time: node.resolve(node_cycles),
                    range: *range,
                })
                .collect(),
            writes: axi_io_nodes
                .writes
                .iter()
                .map(|AxiGenericIoNode { node, range }| AxiGenericIo {
                    time: node.resolve(node_cycles),
                    range: *range,
                })
                .collect(),
            writeresps: axi_io_nodes
                .writeresps
                .iter()
                .map(|node| node.resolve(node_cycles))
                .collect(),
        }
    }
}
