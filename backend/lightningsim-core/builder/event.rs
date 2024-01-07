use crate::{axi_interface::AxiInterface, fifo::Fifo};

use super::{
    axi_builder::FirstReadData, axi_rctl::RctlTransaction, edge_builder::IncompleteEdgeKey,
    module_builder::ModuleKey,
};

/// Some event that impacts the global simulation state, as seen from the
/// perspective of an [UncommittedNode].
///
/// These are usually a potential source or destination point of some edge in
/// the final graph, but not always, such as in the case of
/// [Event::AxiWriteRequest], which only exists because it needs to be tracked
/// by [AxiInterfaceIoNodes::writereqs].
///
/// [UncommittedNode]: super::node::UncommittedNode
/// [AxiInterfaceIoNodes::writereqs]: crate::graph::AxiInterfaceIoNodes::writereqs
#[derive(Clone, Debug)]
pub enum Event {
    SubcallStart {
        module_key: ModuleKey,
        /// The key of the [ControlFlow] edge within
        /// [EdgeBuilder::incomplete_edges] whose source should be this node.
        ///
        /// [ControlFlow]: super::edge_builder::IncompleteEdgeType::ControlFlow
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        edge: IncompleteEdgeKey,
    },
    SubcallEnd {
        /// The key of the [ControlFlow] edge within
        /// [EdgeBuilder::incomplete_edges] whose destination should be this
        /// node.
        ///
        /// [ControlFlow]: super::edge_builder::IncompleteEdgeType::ControlFlow
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        edge: IncompleteEdgeKey,
    },
    FifoRead {
        fifo: Fifo,
        index: usize,

        /// The key of the [FifoRaw] edge within [EdgeBuilder::incomplete_edges]
        /// whose destination should be this read.
        ///
        /// [FifoRaw]: super::edge_builder::IncompleteEdgeType::FifoRaw
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        raw_edge: IncompleteEdgeKey,
    },
    FifoWrite {
        fifo: Fifo,
        index: usize,

        /// The key of the [FifoRaw] edge within [EdgeBuilder::incomplete_edges]
        /// whose source should be this write.
        ///
        /// [FifoRaw]: super::edge_builder::IncompleteEdgeType::FifoRaw
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        raw_edge: IncompleteEdgeKey,
    },
    AxiReadRequest {
        interface: AxiInterface,
        index: usize,

        /// The key of the [AxiRead] edge within [EdgeBuilder::incomplete_edges]
        /// whose source should be this read request.
        ///
        /// [AxiRead]: super::edge_builder::IncompleteEdgeType::AxiRead
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        read_edge: IncompleteEdgeKey,
        rctl_txn: RctlTransaction,
    },
    AxiRead {
        interface: AxiInterface,
        index: usize,
        first_read: Option<FirstReadData>,

        /// The key of the [AxiRctl] edge within [EdgeBuilder::incomplete_edges]
        /// whose source should be this read.
        ///
        /// [AxiRctl]: super::edge_builder::IncompleteEdgeType::AxiRctl
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        rctl_out_edge: Option<IncompleteEdgeKey>,
    },
    AxiWriteRequest {
        interface: AxiInterface,
        index: usize,
    },
    AxiWrite {
        interface: AxiInterface,
        index: usize,

        /// The key of the [AxiWriteResp] edge within
        /// [EdgeBuilder::incomplete_edges] whose source should be this write.
        ///
        /// [AxiWriteResp]: super::edge_builder::IncompleteEdgeType::AxiWriteResp
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        writeresp_edge: Option<IncompleteEdgeKey>,
    },
    AxiWriteResponse {
        interface: AxiInterface,
        index: usize,

        /// The key of the [AxiWriteResp] edge within
        /// [EdgeBuilder::incomplete_edges] whose destination should be this
        /// write response.
        ///
        /// [AxiWriteResp]: super::edge_builder::IncompleteEdgeType::AxiWriteResp
        /// [EdgeBuilder::incomplete_edges]: super::edge_builder::EdgeBuilder::incomplete_edges
        writeresp_edge: IncompleteEdgeKey,
    },
}

impl Event {
    /// Whether this type of event induces an incoming edge to an
    /// [UncommittedNode].
    ///
    /// For instance, all [Event::FifoRead] events induce an [Edge::FifoRaw]
    /// edge to the node that the event is on; on the other hand, no
    /// [Event::AxiReadRequest] events do; such events are only ever the source
    /// of an edge, never the destination.
    ///
    /// [UncommittedNode]: super::node::UncommittedNode
    /// [Edge::FifoRaw]: crate::graph::Edge::FifoRaw
    pub fn has_in_edge(&self) -> bool {
        match self {
            Event::SubcallStart { .. } => false,
            // Induces an Edge::ControlFlow.
            Event::SubcallEnd { .. } => true,
            // Induces an Edge::FifoWar, except the first write.
            Event::FifoWrite { index, .. } => *index != 0,
            // Induces an Edge::FifoRaw.
            Event::FifoRead { .. } => true,
            Event::AxiReadRequest { .. } => false,
            // Can induce an Edge::AxiRctl and/or an Edge::AxiRead.
            Event::AxiRead { first_read, .. } => first_read.is_some(),
            Event::AxiWriteRequest { .. } => false,
            Event::AxiWrite { .. } => false,
            // Induces an Edge::AxiWriteResp.
            Event::AxiWriteResponse { .. } => true,
        }
    }

    /// Whether this event is stalled by other events occurring in the same
    /// stage.
    pub fn is_stalled(&self) -> bool {
        !matches!(self, Event::SubcallStart { .. })
    }
}
