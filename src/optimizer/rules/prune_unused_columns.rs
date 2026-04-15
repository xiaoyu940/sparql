use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};

/// 无用列剪枝 Pass
/// 
/// 遍历查询树，移除那些既不在投影中显示，也不在父节点（如 Filter, Join）中使用的变量。
/// 当前为基础版本：主要确保 Construction 节点的变量映射是精简的。
pub struct PruneUnusedColumnsPass;

impl PruneUnusedColumnsPass {
    pub fn new() -> Self {
        Self
    }
}

impl OptimizerPass for PruneUnusedColumnsPass {
    fn name(&self) -> &str {
        "PruneUnusedColumnsPass"
    }

    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            LogicNode::Construction { projected_vars, bindings, child } => {
                // 递归处理子节点
                self.apply(child, ctx);

                // 只保留在 projected_vars 中定义的绑定
                let mut new_bindings = std::collections::HashMap::new();
                for var in projected_vars {
                    if let Some(expr) = bindings.get(var) {
                        new_bindings.insert(var.clone(), expr.clone());
                    }
                }
                *bindings = new_bindings;
            }
            LogicNode::Join { children, .. } => {
                for child in children {
                    self.apply(child, ctx);
                }
            }
            LogicNode::Filter { child, .. } => self.apply(child, ctx),
            LogicNode::Union(children) => {
                for child in children {
                    self.apply(child, ctx);
                }
            }
            LogicNode::Aggregation { child, .. } => self.apply(child, ctx),
            LogicNode::Limit { child, .. } => self.apply(child, ctx),
            _ => {}
        }
    }
}
