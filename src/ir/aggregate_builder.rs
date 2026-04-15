//! 聚合查询 IR 构建器
//!
//! 负责将 SPARQL 聚合查询转换为 IR Aggregation 节点。
//!
//! # 支持的聚合函数
//! - COUNT, COUNT(DISTINCT)
//! - SUM, AVG, MIN, MAX
//! - 支持 GROUP BY 和 HAVING

use std::collections::HashMap;
use crate::ir::node::LogicNode;
use crate::ir::expr::{Expr, Term};
use crate::parser::ParsedQuery;
use crate::parser::sparql_parser_v2::AggregateExpr;

/// 聚合查询构建器
pub struct AggregationBuilder;

impl AggregationBuilder {
    /// 创建新的聚合构建器
    pub fn new() -> Self {
        Self
    }

    /// 从 ParsedQuery 构建聚合节点
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `child` - 子节点（通常是 Join 或 ExtensionalData）
    ///
    /// # Returns
    /// 如果查询包含聚合，返回 Aggregation 节点；否则返回原节点
    pub fn build_aggregation(
        &self,
        parsed: &ParsedQuery,
        child: LogicNode,
    ) -> LogicNode {
        // 如果没有聚合函数且没有 GROUP BY，直接返回子节点
        if parsed.aggregates.is_empty() && parsed.group_by.is_empty() {
            return child;
        }

        // 转换聚合表达式
        let mut aggregates = HashMap::new();
        for agg in &parsed.aggregates {
            let expr = self.convert_aggregate_expr(agg);
            aggregates.insert(agg.alias.clone(), expr);
        }

        // 构建 HAVING 条件
        let having = if parsed.having_expressions.is_empty() {
            None
        } else {
            // 合并所有 HAVING 表达式
            let conditions: Vec<Expr> = parsed.having_expressions
                .iter()
                .map(|h| self.parse_having_expression(h))
                .collect();

            if conditions.len() == 1 {
                Some(conditions.into_iter().next().expect("should have condition"))
            } else {
                Some(Expr::Logical {
                    op: crate::ir::expr::LogicalOp::And,
                    args: conditions,
                })
            }
        };

        LogicNode::Aggregation {
            group_by: parsed.group_by.clone(),
            aggregates,
            having,
            child: Box::new(child),
        }
    }

    /// 转换聚合表达式
    fn convert_aggregate_expr(&self, agg: &AggregateExpr) -> Expr {
        let func_name = agg.func.to_uppercase();
        let arg_expr = if agg.arg == "*" {
            Expr::Term(Term::Constant("*".to_string()))
        } else if agg.arg.starts_with('?') {
            // 变量参数，如 ?salary
            let var_name = &agg.arg[1..]; // 去掉 ?
            Expr::Term(Term::Variable(var_name.to_string()))
        } else {
            // 常量或复杂表达式
            Expr::Term(Term::Constant(agg.arg.clone()))
        };

        // 如果是 DISTINCT，函数名加上 _DISTINCT 前缀
        let func_name = if agg.distinct {
            format!("{}_DISTINCT", func_name)
        } else {
            func_name
        };

        Expr::Function {
            name: func_name,
            args: vec![arg_expr],
        }
    }

    /// 解析 HAVING 表达式
    ///
    /// 将 HAVING 字符串解析为 Expr
    fn parse_having_expression(&self, having_str: &str) -> Expr {
        // 简化实现：解析常见的比较表达式
        // 例如: "(AVG(?salary) > 50000)" 或 "(COUNT(?emp) > 10)"

        let trimmed = having_str.trim();

        // 尝试解析比较操作
        // 支持: >, <, >=, <=, =, !=
        let ops = vec![">=", "<=", ">", "<", "=", "!="];

        for op in &ops {
            if let Some(pos) = trimmed.find(op) {
                let left_str = trimmed[..pos].trim();
                let right_str = trimmed[pos + op.len()..].trim();

                let left = self.parse_expr(left_str);
                let right = self.parse_expr(right_str);

                let comp_op = match *op {
                    ">" => crate::ir::expr::ComparisonOp::Gt,
                    "<" => crate::ir::expr::ComparisonOp::Lt,
                    ">=" => crate::ir::expr::ComparisonOp::Gte,
                    "<=" => crate::ir::expr::ComparisonOp::Lte,
                    "=" => crate::ir::expr::ComparisonOp::Eq,
                    "!=" => crate::ir::expr::ComparisonOp::Neq,
                    _ => crate::ir::expr::ComparisonOp::Eq,
                };

                return Expr::Compare {
                    left: Box::new(left),
                    op: comp_op,
                    right: Box::new(right),
                };
            }
        }

        // 无法解析，返回常量表达式
        Expr::Term(Term::Constant(trimmed.to_string()))
    }

    /// 解析表达式字符串
    fn parse_expr(&self, expr_str: &str) -> Expr {
        let trimmed = expr_str.trim();

        // 检查是否是聚合函数调用
        let upper = trimmed.to_ascii_uppercase();
        let agg_funcs = vec!["COUNT(", "SUM(", "AVG(", "MIN(", "MAX("];

        for func in &agg_funcs {
            if upper.starts_with(func) {
                // 解析聚合函数
                let func_name = &func[..func.len()-1]; // 去掉 (
                let inner = &trimmed[func.len()..trimmed.len()-1]; // 去掉 )

                let arg = if inner.to_ascii_uppercase().starts_with("DISTINCT ") {
                    // DISTINCT 参数
                    let distinct_arg = &inner[9..]; // 去掉 "DISTINCT "
                    if distinct_arg.starts_with('?') {
                        Expr::Term(Term::Variable(distinct_arg[1..].to_string()))
                    } else {
                        Expr::Term(Term::Constant(distinct_arg.to_string()))
                    }
                } else if inner == "*" {
                    Expr::Term(Term::Constant("*".to_string()))
                } else if inner.starts_with('?') {
                    Expr::Term(Term::Variable(inner[1..].to_string()))
                } else {
                    Expr::Term(Term::Constant(inner.to_string()))
                };

                return Expr::Function {
                    name: func_name.to_string(),
                    args: vec![arg],
                };
            }
        }

        // 检查是否是变量
        if trimmed.starts_with('?') {
            return Expr::Term(Term::Variable(trimmed[1..].to_string()));
        }

        // 检查是否是数字
        if trimmed.parse::<f64>().is_ok() {
            return Expr::Term(Term::Literal {
                value: trimmed.to_string(),
                datatype: Some("http://www.w3.org/2001/XMLSchema#decimal".to_string()),
                language: None,
            });
        }

        // 默认作为常量
        Expr::Term(Term::Constant(trimmed.to_string()))
    }
}

impl Default for AggregationBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// 扩展 IRConverter 以支持聚合
pub trait AggregateIRConverter {
    /// 将聚合查询转换为 IR
    fn convert_aggregate_query(&self, parsed: &ParsedQuery, child: LogicNode) -> LogicNode;
}

impl AggregateIRConverter for crate::parser::ir_converter::IRConverter {
    fn convert_aggregate_query(&self, parsed: &ParsedQuery, child: LogicNode) -> LogicNode {
        let builder = AggregationBuilder::new();
        builder.build_aggregation(parsed, child)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_aggregate_expr() {
        let builder = AggregationBuilder::new();

        let agg = AggregateExpr {
            func: "COUNT".to_string(),
            arg: "*".to_string(),
            alias: "count_all".to_string(),
            distinct: false,
        };

        let expr = builder.convert_aggregate_expr(&agg);

        match expr {
            Expr::Function { name, args } => {
                assert_eq!(name, "COUNT");
                assert_eq!(args.len(), 1);
            }
            _ => panic!("Expected Function expression"),
        }
    }

    #[test]
    fn test_convert_distinct_aggregate() {
        let builder = AggregationBuilder::new();

        let agg = AggregateExpr {
            func: "COUNT".to_string(),
            arg: "?emp".to_string(),
            alias: "emp_count".to_string(),
            distinct: true,
        };

        let expr = builder.convert_aggregate_expr(&agg);

        match expr {
            Expr::Function { name, args } => {
                assert_eq!(name, "COUNT_DISTINCT");
                match &args[0] {
                    Expr::Term(Term::Variable(v)) => assert_eq!(v, "emp"),
                    _ => panic!("Expected Variable argument"),
                }
            }
            _ => panic!("Expected Function expression"),
        }
    }

    #[test]
    fn test_parse_having() {
        let builder = AggregationBuilder::new();

        let expr = builder.parse_having_expression("(AVG(?salary) > 50000)");

        match expr {
            Expr::Compare { op, .. } => {
                assert!(matches!(op, crate::ir::expr::ComparisonOp::Gt));
            }
            _ => panic!("Expected Compare expression"),
        }
    }
}
