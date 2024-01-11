use std::{cmp, iter, ops};

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

#[derive(Clone, Copy, FromPyObject)]
pub struct FifoConfig {
    pub width: u32,
    pub depth: u32,
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

impl FifoConfig {
    pub fn r#type(&self) -> FifoType {
        if self.depth <= 2 {
            FifoType::ShiftRegister
        } else {
            FifoType::Ram
        }
    }

    pub fn bram_count(&self) -> u32 {
        if matches!(self.r#type(), FifoType::Ram) {
            let mut bram_count = 0;
            let mut remaining_width = self.width;

            // BRAMs can be configured as 1Kx18...
            bram_count += (remaining_width / 18) * ((self.depth + 1023) / 1024);
            remaining_width %= 18;
            if self.depth <= 1024 {
                bram_count += u32::from(remaining_width != 0);
                return bram_count;
            }

            // ...and/or as 2Kx9...
            bram_count += (remaining_width / 9) * ((self.depth + 2047) / 2048);
            remaining_width %= 9;
            if self.depth <= 2048 {
                bram_count += u32::from(remaining_width != 0);
                return bram_count;
            }

            // (Ad-hoc special case found empirically)
            if self.depth <= 4096 && self.width > 18 && remaining_width == 3 {
                bram_count += 2;
                return bram_count;
            }

            // ...and/or as 4Kx4...
            bram_count += (remaining_width / 4) * ((self.depth + 4095) / 4096);
            remaining_width %= 4;
            if self.depth <= 4096 {
                bram_count += u32::from(remaining_width != 0);
                return bram_count;
            }

            // ...and/or as 8Kx2...
            bram_count += (remaining_width / 2) * ((self.depth + 8191) / 8192);
            remaining_width %= 2;

            // ...and/or as 16Kx1.
            bram_count += remaining_width * ((self.depth + 16383) / 16384);
            bram_count
        } else {
            0
        }
    }

    pub fn get_design_space(width: u32, write_count: u32) -> impl Iterator<Item = Self> {
        let initial_depth = 2;
        let max_depth = cmp::max(write_count, initial_depth);
        let max_bram_count = FifoConfig {
            width,
            depth: max_depth,
        }
        .bram_count();

        iter::once(FifoConfig {
            width,
            depth: initial_depth,
        })
        .chain(
            (1024..max_depth)
                .step_by(1024)
                .map(move |depth| FifoConfig { width, depth }),
        )
        .map_while(move |config| {
            let bram_count = config.bram_count();
            (bram_count != max_bram_count).then(|| {
                let next_config = FifoConfig {
                    width: config.width,
                    depth: (config.depth + 1024) / 1024 * 1024,
                };
                (bram_count != next_config.bram_count()).then_some(config)
            })
        })
        .flatten()
        .chain(iter::once(FifoConfig {
            width,
            depth: max_depth,
        }))
    }
}

impl FifoType {
    pub fn from_config(config: Option<&FifoConfig>) -> Self {
        match config {
            Some(config) => config.r#type(),
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

#[pymethods]
impl FifoIo {
    fn get_observed_depth(&self) -> usize {
        let mut depth: usize = 0;
        let mut max_depth: usize = 0;
        let mut write_iter = self.writes.iter();
        let mut read_iter = self.reads.iter();
        let mut next_write_cycle = write_iter.next();
        let mut next_read_cycle = read_iter.next();

        while let Some(write_cycle) = next_write_cycle {
            let read_cycle =
                next_read_cycle.expect("last read should never happen before last write");
            if write_cycle < read_cycle {
                depth += 1;
                max_depth = max_depth.max(depth);
                next_write_cycle = write_iter.next();
            } else {
                depth -= 1;
                next_read_cycle = read_iter.next();
            }
        }

        max_depth
    }
}
