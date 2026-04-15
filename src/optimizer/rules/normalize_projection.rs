use std::collections::HashMap;
use crate::ir::expr::Expr;
use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};

/// 投影归一化 Pass
/// 
/// 将嵌套的 Construction 节点进行合并。
/// 如果当前 Construction 的子节点也是 Construction，则尝试将它们的映射表达式合并。
pub struct NormalizeProjectionPass;

impl NormalizeProjectionPass {
    pub fn new() -> Self {
        Self
    }
}

impl OptimizerPass for NormalizeProjectionPass {
    fn name(&self) -> &str {
        "NormalizeProjectionPass"
    }

    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            LogicNode::Construction { projected_vars: _, bindings, child } => {
                // 首先递归处理子节点
                self.apply(child, ctx);

                // 检查子节点是否也是 Construction
                if let LogicNode::Construction { 
                    projected_vars: _child_vars, 
                    bindings: child_bindings, 
                    child: grand_child 
                } = child.as_mut() {
                    // 合并绑定：将当前节点中的变量替换为子节点中的表达式
                    let mut new_bindings = HashMap::new();
                    for (var, expr) in bindings.iter() {
                        // 如果当前表达式是一个变量引用，且该变量在子节点中有映射
                        let substituted = self.substitute_vars(expr, child_bindings);
                        new_bindings.insert(var.clone(), substituted);
                    }

                    // 更新本节点
                    *bindings = new_bindings;
                    let next_grand_child = std::mem::replace(grand_child.as_mut(), LogicNode::Union(vec![])); // 临时占位
                    *child = Box::new(next_grand_child);
                }
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

impl NormalizeProjectionPass {
    /// 在表达式中替换变量
    fn substitute_vars(&self, expr: &Expr, child_bindings: &HashMap<String, Expr>) -> Expr {
        match expr {
            Expr::Term(crate::ir::expr::Term::Variable(v)) => {
                if let Some(child_expr) = child_bindings.get(v) {
                    child_expr.clone()
                } else {
                    expr.clone()
                }
            }
            Expr::Function { name, args } => {
                let new_args = args.iter()
                    .map(|arg| self.substitute_vars(arg, child_bindings))
                    .collect();
                Expr::Function { name: name.clone(), args: new_args }
            }
            Expr::Logical { op, args } => {
                let new_args = args.iter()
                    .map(|arg| self.substitute_vars(arg, child_bindings))
                    .collect();
                Expr::Logical { op: *op, args: new_args }
            }
            Expr::Compare { left, right, op } => {
                Expr::Compare {
                    left: Box::new(self.substitute_vars(left, child_bindings)),
                    right: Box::new(self.substitute_vars(right, child_bindings)),
                    op: *op,
                }
            }
            _ => expr.clone(),
        }
    }
}
