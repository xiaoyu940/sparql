use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext, rules::*};

pub struct PassManager {
    passes: Vec<Box<dyn OptimizerPass>>,
}

impl PassManager {
    pub fn new() -> Self {
        Self {
            passes: vec![
                Box::new(UnfoldingPass::new()),
                Box::new(SelfJoinEliminationPass::new()),
                Box::new(JoinEliminationPass::new()),
                Box::new(LeftToInnerJoinPass::new()),
                Box::new(NormalizeProjectionPass::new()),
                Box::new(PruneUnusedColumnsPass::new()),
            ],
        }
    }

    /// Run all passes on the given node tree until it reaches a fixed point.
    pub fn run(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        let mut changed = true;
        let mut iterations = 0;
        const MAX_ITERATIONS: usize = 10;

        while changed && iterations < MAX_ITERATIONS {
            let initial_node = node.clone();
            for pass in &self.passes {
                pass.apply(node, ctx);
            }
            changed = *node != initial_node;
            iterations += 1;
        }
    }
}
