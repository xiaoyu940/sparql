use crate::ir::node::LogicNode;

#[derive(Debug, Default)]
pub struct JoinOptimizer;

impl JoinOptimizer {
    pub fn reorder(node: LogicNode) -> LogicNode {
        // Sprint1 MVP: keep semantics unchanged; future versions can use statistics.
        node
    }
}
