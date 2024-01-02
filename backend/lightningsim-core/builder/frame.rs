use std::collections::VecDeque;

use crate::SimulationStage;

use super::{
    edge_builder::IncompleteEdgeKey,
    event::Event,
    module_builder::ModuleKey,
    node::{NodeTime, UncommittedNode},
};

/// A stack frame being parsed.
///
/// Every edge generated during parsing is either:
/// - Committed, meaning the exact start node is known, or
/// - Uncommitted, meaning the start of the edge is only known to be a specific
///   dynamic stage within a specific frame. (Upon commit, this stage may not
///   have a specific node, in which case the edge will start at the nearest
///   previous node but with an added delay corresponding to how many stages lie
///   between the two.)
#[derive(Clone)]
pub struct StackFrame {
    pub key: ModuleKey,
    /// The dynamic stage within this module's parent at which this module ends.
    pub parent_end: SimulationStage,
    pub current_edge: IncompleteEdgeKey,
    pub current_time: NodeTime,
    /// The offset representing the dynamic stage at the start of the window of
    /// uncommitted nodes.
    pub offset: SimulationStage,
    /// The window of uncommitted nodes. This is only ever as large as the
    /// static stage of the latest dynamic stage encountered, as any nodes
    /// earlier than that can be committed.
    pub window: VecDeque<UncommittedNode>,
}

#[derive(Clone, Copy)]
pub struct SimulationStagePair {
    pub static_stage: SimulationStage,
    pub dynamic_stage: SimulationStage,
}

impl StackFrame {
    pub fn new(key: ModuleKey, parent_end: SimulationStage, start_edge: IncompleteEdgeKey) -> Self {
        Self {
            key,
            parent_end,
            current_edge: start_edge,
            current_time: NodeTime::RelativeToStart(0),
            offset: 0,
            window: VecDeque::new(),
        }
    }

    pub fn add_event(&mut self, static_stage: SimulationStage, event: Event) {
        let static_stage = static_stage.try_into().unwrap();
        if static_stage >= self.window.len() {
            self.window.resize_with(static_stage + 1, Default::default);
        }
        self.window[static_stage].events.push(event);
    }
}
