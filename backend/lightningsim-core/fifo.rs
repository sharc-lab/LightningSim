use std::ops;

use pyo3::prelude::*;

use crate::{
    node::{NodeIndex, NodeWithDelay},
    ClockCycle,
};

pub type FifoId = u32;

const SHIFT_REGISTER_RAW_DELAY: ClockCycle = 1;
const SHIFT_REGISTER_WAR_DELAY: ClockCycle = 1;
const RAM_RAW_DELAY: ClockCycle = 2;
const RAM_WAR_DELAY: ClockCycle = 1;

#[pyclass]
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Fifo {
    #[pyo3(get)]
    pub id: FifoId,
}

pub enum FifoType {
    ShiftRegister,
    Ram,
}

#[derive(Clone)]
pub struct FifoIoNodes {
    /// Nodes which write to this FIFO.
    ///
    /// The first FIFO write node may not have any dependencies, so it may not
    /// be its own node, which is why this is a [Box] of [NodeWithDelay] instead
    /// of [NodeIndex].
    pub(crate) writes: Box<[NodeWithDelay]>,
    /// Nodes which read from this FIFO.
    ///
    /// All FIFO read nodes always have their corresponding write node as a
    /// dependency; therefore, all FIFO reads are guaranteed to be part of their
    /// own node, which is why this is a [Box] of [NodeIndex] instead of
    /// [NodeWithDelay].
    pub(crate) reads: Box<[NodeIndex]>,
}

#[pyclass]
#[derive(Clone)]
pub struct FifoIo {
    #[pyo3(get)]
    pub writes: Vec<ClockCycle>,
    #[pyo3(get)]
    pub reads: Vec<ClockCycle>,
}

impl FifoType {
    pub fn from_depth(depth: Option<usize>) -> Self {
        match depth {
            Some(depth) => {
                if depth <= 2 {
                    Self::ShiftRegister
                } else {
                    Self::Ram
                }
            }
            None => Self::ShiftRegister,
        }
    }

    pub fn raw_delay(&self) -> ClockCycle {
        match self {
            Self::ShiftRegister => SHIFT_REGISTER_RAW_DELAY,
            Self::Ram => RAM_RAW_DELAY,
        }
    }

    pub fn war_delay(&self) -> ClockCycle {
        match self {
            Self::ShiftRegister => SHIFT_REGISTER_WAR_DELAY,
            Self::Ram => RAM_WAR_DELAY,
        }
    }
}

impl FifoIo {
    pub fn new<T>(fifo_io_nodes: &FifoIoNodes, node_cycles: &T) -> Self
    where
        T: ops::Index<usize, Output = ClockCycle> + ?Sized,
    {
        FifoIo {
            writes: fifo_io_nodes
                .writes
                .iter()
                .map(|node| node.resolve(node_cycles))
                .collect(),
            reads: fifo_io_nodes
                .reads
                .iter()
                .map(|&node| node_cycles[node.try_into().unwrap()])
                .collect(),
        }
    }
}
