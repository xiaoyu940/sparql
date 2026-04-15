use crate::ir::node::LogicNode;

pub type IRNode = LogicNode;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IRStage {
    Parsed,
    Optimized,
    SqlReady,
}
