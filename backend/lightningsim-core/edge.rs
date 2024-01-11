use crate::{
    axi_interface::{AxiInterface, AXI_READ_OVERHEAD, AXI_WRITE_OVERHEAD},
    fifo::{Fifo, FifoType},
    node::NodeWithDelay,
    CompiledSimulation, SimulationError, SimulationParameters,
};

pub type EdgeIndex = usize;

/// An edge in the graph.
///
/// As edges are stored in CSR format, the destination node is not stored
/// explicitly as it is implicit in the position of the edge within the edge
/// list.
#[derive(Clone, Debug)]
pub enum Edge {
    /// An edge derived from the control flow of the simulation. The exact
    /// source node and edge delay are known at the time of graph construction
    /// and will never change.
    ///
    /// Note that during graph construction, the node index may be
    /// indeterminate, but the delay may be valid. Upon being updated with a
    /// valid source, the delay of the source and the existing delay must be
    /// added together.
    ControlFlow(NodeWithDelay),
    /// A FIFO read-after-write dependency. The source node is known at the time
    /// of graph construction, but the delay must be determined at runtime based
    /// on the FIFO hardware implementation (which is determined by its depth).
    FifoRaw {
        /// The source node, i.e., the FIFO write.
        ///
        /// This may theoretically not be its own node (e.g., in the case of the
        /// first write to a FIFO), which is why this is a [NodeWithDelay]
        /// instead of a [NodeIndex].
        u: NodeWithDelay,
        /// The FIFO being read.
        ///
        /// The depth of this FIFO determines its hardware implementation, which
        /// determines the delay to add to `u`.
        fifo: Fifo,
    },
    /// A FIFO write-after-read dependency. The source node, if any, is not
    /// known until runtime and must be looked up based on the FIFO depth. The
    /// delay must also be determined at runtime based on the FIFO hardware
    /// implementation.
    FifoWar { fifo: Fifo, index: usize },
    /// A dependency caused by filling the AXI rctl FIFO. The source node is
    /// known at the time of graph construction, but the delay must be
    /// determined at runtime based on the user-specified AXI interface latency.
    AxiRctl {
        /// The source node, i.e., the blocking AXI read.
        u: NodeWithDelay,
        interface: AxiInterface,
    },
    /// A dependency between an AXI read request and one of its corresponding
    /// reads. The source node is known at the time of graph construction, but
    /// the delay must be determined at runtime based on the user-specified AXI
    /// interface latency.
    AxiRead {
        /// The source node, i.e., the AXI read request.
        u: NodeWithDelay,
        interface: AxiInterface,
    },
    /// A dependency between an AXI write and its corresponding write response.
    /// The source node is known at the time of graph construction, but the
    /// delay must be determined at runtime based on the user-specified AXI
    /// interface latency.
    AxiWriteResp {
        /// The source node, i.e., the AXI write.
        u: NodeWithDelay,
        interface: AxiInterface,
    },
}

impl Edge {
    pub fn resolve(
        &self,
        simulation: &CompiledSimulation,
        parameters: &SimulationParameters,
    ) -> Result<Option<NodeWithDelay>, SimulationError> {
        match *self {
            Edge::ControlFlow(node) => Ok(Some(node)),
            Edge::FifoRaw { u, fifo } => {
                let depth = parameters.get_fifo_depth(fifo)?;
                let fifo_type = FifoType::from_depth(depth);
                Ok(Some(u + fifo_type.raw_delay()))
            }
            Edge::FifoWar { fifo, index } => {
                let depth = parameters.get_fifo_depth(fifo)?;
                Ok(depth
                    .and_then(|depth| index.checked_sub(depth))
                    .map(|index| NodeWithDelay {
                        node: simulation.fifo_nodes[&fifo].reads[index],
                        delay: FifoType::from_depth(depth).war_delay(),
                    }))
            }
            Edge::AxiRctl { u, interface } => {
                let delay = parameters.get_axi_delay(interface)?;
                Ok(Some(u + (delay + AXI_READ_OVERHEAD - AXI_WRITE_OVERHEAD)))
            }
            Edge::AxiRead { u, interface } => {
                let delay = parameters.get_axi_delay(interface)?;
                Ok(Some(u + (delay + AXI_READ_OVERHEAD)))
            }
            Edge::AxiWriteResp { u, interface } => {
                let delay = parameters.get_axi_delay(interface)?;
                Ok(Some(u + (delay + AXI_WRITE_OVERHEAD)))
            }
        }
    }
}
