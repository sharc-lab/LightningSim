use std::ops;

use pyo3::prelude::*;

use crate::{node::NodeWithDelay, simulation::ClockCycle};

pub const AXI_READ_OVERHEAD: ClockCycle = 12;
pub const AXI_WRITE_OVERHEAD: ClockCycle = 7;
pub const MAX_RCTL_DEPTH: usize = 16;

pub type AxiAddress = u64;

#[derive(FromPyObject, Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct AxiInterface {
    pub address: AxiAddress,
}

#[derive(Clone, Copy)]
pub struct AxiAddressRange {
    pub offset: AxiAddress,
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
