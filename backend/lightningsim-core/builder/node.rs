use std::ops;

use smallvec::SmallVec;

use crate::{node::NodeWithDelay, ClockCycle};

use super::event::Event;

#[derive(Clone, Default)]
pub struct UncommittedNode {
    pub events: SmallVec<[Event; 2]>,
}

#[derive(Clone)]
pub struct ResolvedNode {
    pub time: NodeTime,
    pub node: UncommittedNode,
}

#[derive(Clone, Copy, Debug)]
pub enum NodeTime {
    Absolute(NodeWithDelay),
    RelativeToStart(ClockCycle),
}

impl UncommittedNode {
    pub fn is_own_node(&self) -> bool {
        self.events.iter().any(|event| event.has_in_edge())
    }
}

impl NodeTime {
    pub fn resolve(&self, start: NodeWithDelay) -> NodeWithDelay {
        match self {
            Self::Absolute(time) => *time,
            Self::RelativeToStart(delay) => start + *delay,
        }
    }
}

impl ops::Add<ClockCycle> for NodeTime {
    type Output = Self;

    fn add(self, rhs: ClockCycle) -> Self::Output {
        match self {
            Self::Absolute(time) => Self::Absolute(time + rhs),
            Self::RelativeToStart(delay) => Self::RelativeToStart(delay + rhs),
        }
    }
}

impl ops::AddAssign<ClockCycle> for NodeTime {
    fn add_assign(&mut self, rhs: ClockCycle) {
        match self {
            Self::Absolute(time) => *time += rhs,
            Self::RelativeToStart(delay) => *delay += rhs,
        }
    }
}
