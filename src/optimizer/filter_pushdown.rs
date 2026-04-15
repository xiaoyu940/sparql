use std::collections::HashSet;

use crate::ir::expr::{Expr, Term};
use crate::ir::node::LogicNode;

#[derive(Debug, Default)]
pub struct FilterPushdown;

impl FilterPushdown {
    pub fn apply(node: LogicNode) -> LogicNode {
        match node {
            LogicNode::Filter { expression, child } => match *child {
                LogicNode::Join {
                    mut children,
                    condition,
                    join_type,
                } => {
                    let filter_vars = vars_in_expr(&expression);
                    for child in &mut children {
                        let child_vars = child.used_variables();
                        if !filter_vars.is_empty() && filter_vars.is_subset(&child_vars) {
                            let pushed = LogicNode::Filter {
                                expression: expression.clone(),
                                child: Box::new(child.clone()),
                            };
                            *child = pushed;
                            return LogicNode::Join {
                                children,
                                condition,
                                join_type,
                            };
                        }
                    }
                    LogicNode::Filter {
                        expression,
                        child: Box::new(LogicNode::Join {
                            children,
                            condition,
                            join_type,
                        }),
                    }
                }
                other => LogicNode::Filter {
                    expression,
                    child: Box::new(other),
                },
            },
            other => other,
        }
    }
}

fn vars_in_expr(expr: &Expr) -> HashSet<String> {
    let mut out = HashSet::new();
    collect_vars(expr, &mut out);
    out
}

fn collect_vars(expr: &Expr, out: &mut HashSet<String>) {
    match expr {
        Expr::Term(Term::Variable(v)) => {
            out.insert(v.clone());
        }
        Expr::Compare { left, right, .. } => {
            collect_vars(left, out);
            collect_vars(right, out);
        }
        Expr::Logical { args, .. } | Expr::Function { args, .. } => {
            for arg in args {
                collect_vars(arg, out);
            }
        }
        _ => {}
    }
}
