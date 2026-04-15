use std::collections::HashSet;
use crate::ir::node::LogicNode;
use crate::ir::expr::{Expr, Term};
use crate::optimizer::{OptimizerPass, OptimizerContext};

pub struct PredicatePushdownPass;

impl PredicatePushdownPass {
    pub fn new() -> Self {
        Self
    }

    fn can_push_down(&self, expr: &Expr, target_vars: &HashSet<String>) -> bool {
        match expr {
            Expr::Term(Term::Variable(var)) => target_vars.contains(var),
            Expr::Compare { left, right, .. } => {
                self.can_push_down(left, target_vars) && 
                self.can_push_down(right, target_vars)
            },
            Expr::Logical { args, .. } => {
                args.iter().all(|arg| self.can_push_down(arg, target_vars))
            },
            Expr::Function { name, args: _ } => {
                // 某些函数可以下推，如字符串操作、数值计算
                match name.as_str() {
                    // 可下推的函数：字符串操作
                    "UPPER" | "LOWER" | "TRIM" | "LENGTH" | "SUBSTR" => true,
                    // 可下推的函数：数值计算
                    "ABS" | "CEIL" | "FLOOR" | "ROUND" => true,
                    // 可下推的函数：类型转换
                    "CAST" => true,
                    // 不可下推的函数：聚合函数
                    "COUNT" | "SUM" | "AVG" | "MAX" | "MIN" => false,
                    // 不可下推的函数：复杂分析函数
                    "RANK" | "DENSE_RANK" | "ROW_NUMBER" => false,
                    // 其他函数保守处理
                    _ => false,
                }
            },
            _ => false,
        }
    }

    fn extract_pushable_conditions(
        &self, 
        node: &LogicNode, 
        conditions: &mut Vec<Expr>
    ) {
        match node {
            LogicNode::Filter { expression, child } => {
                if self.can_push_down(expression, &child.used_variables()) {
                    // 检查是否已经存在相同的条件，避免重复
                    if !self.contains_condition(conditions, expression) {
                        conditions.push(expression.clone());
                    }
                }
                self.extract_pushable_conditions(child, conditions);
            },
            LogicNode::Join { children, .. } => {
                for child in children {
                    self.extract_pushable_conditions(child, conditions);
                }
            },
            _ => {}
        }
    }
    
    /// 检查条件列表中是否已存在相同的条件
    fn contains_condition(&self, conditions: &[Expr], target: &Expr) -> bool {
        conditions.iter().any(|cond| self.expressions_equal(cond, target))
    }
    
    /// 简单的表达式等价性检查（用于去重）
    fn expressions_equal(&self, expr1: &Expr, expr2: &Expr) -> bool {
        match (expr1, expr2) {
            (Expr::Term(term1), Expr::Term(term2)) => term1 == term2,
            (Expr::Compare { left: l1, op: op1, right: r1 }, 
             Expr::Compare { left: l2, op: op2, right: r2 }) => {
                op1 == op2 && 
                self.expressions_equal(l1, l2) && 
                self.expressions_equal(r1, r2)
            },
            (Expr::Logical { op: op1, args: args1 }, 
             Expr::Logical { op: op2, args: args2 }) => {
                op1 == op2 && 
                args1.len() == args2.len() &&
                args1.iter().zip(args2.iter()).all(|(a1, a2)| self.expressions_equal(a1, a2))
            },
            (Expr::Function { name: name1, args: args1 }, 
             Expr::Function { name: name2, args: args2 }) => {
                name1 == name2 && 
                args1.len() == args2.len() &&
                args1.iter().zip(args2.iter()).all(|(a1, a2)| self.expressions_equal(a1, a2))
            },
            _ => false,
        }
    }

    fn push_down_to_extensional(&self, node: &mut LogicNode, conditions: Vec<Expr>) {
        match node {
            LogicNode::ExtensionalData { table_name, column_mapping, metadata } => {
                // 将条件推送到表扫描
                if !conditions.is_empty() {
                    let mut combined = conditions[0].clone();
                    for condition in conditions.iter().skip(1) {
                        combined = Expr::Logical {
                            op: crate::ir::expr::LogicalOp::And,
                            args: vec![combined, condition.clone()],
                        };
                    }
                    
                    *node = LogicNode::Filter {
                        expression: combined,
                        child: Box::new(LogicNode::ExtensionalData {
                            table_name: table_name.clone(),
                            column_mapping: column_mapping.clone(),
                            metadata: std::sync::Arc::clone(metadata),
                        }),
                    };
                }
            },
            _ => {}
        }
    }
}

impl OptimizerPass for PredicatePushdownPass {
    fn name(&self) -> &str {
        "PredicatePushdownPass"
    }

    fn apply(&self, node: &mut LogicNode, _ctx: &OptimizerContext) {
        match node {
            LogicNode::Filter { expression: _, child } => {
                // 递归处理子节点
                self.apply(child, _ctx);
                
                // 尝试将条件下推
                let mut conditions = Vec::new();
                self.extract_pushable_conditions(child, &mut conditions);
                
                if !conditions.is_empty() {
                    // 将条件下推到 ExtensionalData 节点
                    self.push_down_to_extensional(child, conditions);
                    
                    // 如果所有条件都被下推，则移除当前 Filter 节点
                    if let LogicNode::Filter { .. } = child.as_ref() {
                        // 保留部分无法下推的条件
                    }
                }
            },
            LogicNode::Join { children, .. } => {
                // 处理 JOIN 节点的子节点
                for child in children.iter_mut() {
                    self.apply(child, _ctx);
                }
            },
            _ => {}
        }
    }
}
