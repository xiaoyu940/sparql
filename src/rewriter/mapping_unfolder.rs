use crate::ir::node::LogicNode;
use crate::optimizer::rules::UnfoldingPass;
use crate::optimizer::{OptimizerContext, OptimizerPass};

/// Explicit mapping unfolding stage for Sprint2 P0-1.
pub struct MappingUnfolder;

impl MappingUnfolder {
    pub fn unfold(node: &mut LogicNode, ctx: &OptimizerContext) {
        UnfoldingPass::new().apply(node, ctx);
    }
}

