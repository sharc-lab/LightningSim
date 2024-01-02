use std::ops;

use crate::simulation::ClockCycle;

pub type NodeIndex = u32;

#[derive(Clone, Copy, Debug)]
pub struct NodeWithDelay {
    pub node: NodeIndex,
    pub delay: ClockCycle,
}

impl NodeWithDelay {
    fn resolve<T: ops::Index<usize, Output = ClockCycle> + ?Sized>(
        &self,
        node_cycles: &T,
    ) -> ClockCycle {
        node_cycles[self.node.try_into().unwrap()] + self.delay
    }
}

impl ops::Add<ClockCycle> for NodeWithDelay {
    type Output = Self;

    fn add(self, rhs: ClockCycle) -> Self::Output {
        NodeWithDelay {
            node: self.node,
            delay: self.delay + rhs,
        }
    }
}

impl ops::AddAssign<ClockCycle> for NodeWithDelay {
    fn add_assign(&mut self, rhs: ClockCycle) {
        self.delay += rhs;
    }
}
