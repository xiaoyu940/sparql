use crate::ir::node::{LogicNode, JoinType};
use crate::ir::expr::{Expr, LogicalOp};
use std::collections::HashMap;

pub struct EnhancedSqlGenerator {
    alias_counter: usize,
    table_aliases: HashMap<String, String>,
}

impl EnhancedSqlGenerator {
    pub fn new() -> Self {
        Self {
            alias_counter: 0,
            table_aliases: HashMap::new(),
        }
    }

    fn generate_table_alias(&mut self, table_name: &str) -> String {
        if let Some(alias) = self.table_aliases.get(table_name) {
            alias.clone()
        } else {
            let alias = format!("t{}", self.alias_counter);
            self.alias_counter += 1;
            self.table_aliases.insert(table_name.to_string(), alias.clone());
            alias
        }
    }

    #[allow(dead_code)]
    fn generate_join_condition(&self, left_alias: &str, right_alias: &str, condition: &Expr) -> String {
        match condition {
            Expr::Function { name, args } if name == "Eq" => {
                let left = self.format_expr_with_alias(&args[0], left_alias);
                let right = self.format_expr_with_alias(&args[1], right_alias);
                format!("{} = {}", left, right)
            },
            _ => self.format_expr(condition),
        }
    }

    fn format_join_condition(&self, condition: &Expr, left_alias: &str, right_alias: &str) -> String {
        match condition {
            Expr::Compare { left, right, op } => {
                let left_formatted = self.format_expr_with_alias(left, left_alias);
                let right_formatted = self.format_expr_with_alias(right, right_alias);
                let operator = match op {
                    crate::ir::expr::ComparisonOp::Eq => "=",
                    crate::ir::expr::ComparisonOp::Neq => "<>",
                    crate::ir::expr::ComparisonOp::Lt => "<",
                    crate::ir::expr::ComparisonOp::Lte => "<=",
                    crate::ir::expr::ComparisonOp::Gt => ">",
                    crate::ir::expr::ComparisonOp::Gte => ">=",
                    crate::ir::expr::ComparisonOp::In => "IN",
                    crate::ir::expr::ComparisonOp::NotIn => "NOT IN",
                };
                format!("{} {} {}", left_formatted, operator, right_formatted)
            },
            Expr::Logical { op, args } => {
                let formatted_args: Vec<String> = args.iter()
                    .map(|arg| self.format_join_condition(arg, left_alias, right_alias))
                    .collect();
                let operator = match op {
                    crate::ir::expr::LogicalOp::And => "AND",
                    crate::ir::expr::LogicalOp::Or => "OR",
                    crate::ir::expr::LogicalOp::Not => return format!("NOT ({})", formatted_args.join(" AND ")),
                };
                format!("({})", formatted_args.join(&format!(" {} ", operator)))
            },
            _ => self.format_expr(condition),
        }
    }
    
    fn format_expr_with_alias(&self, expr: &Expr, alias: &str) -> String {
        match expr {
            Expr::Term(crate::ir::expr::Term::Variable(var)) => format!("{}.{}", alias, var),
            Expr::Term(crate::ir::expr::Term::Constant(val)) => format!("'{}'", val),
            Expr::Term(crate::ir::expr::Term::Literal { value, .. }) => format!("'{}'", value),
            _ => self.format_expr(expr),
        }
    }

    pub fn generate(&mut self, node: &LogicNode) -> String {
        match node {
            LogicNode::Construction { projected_vars, bindings, child } => {
                let child_sql = self.generate(child);
                let mut select_items = Vec::new();
                
                for var in projected_vars {
                    if let Some(expr) = bindings.get(var) {
                        select_items.push(format!("{} AS {}", self.format_expr(expr), var));
                    } else {
                        select_items.push(format!("{}.{}", self.get_main_alias(), var));
                    }
                }
                
                for (alias, expr) in bindings {
                    if !projected_vars.contains(alias) {
                        select_items.push(format!("{} AS {}", self.format_expr(expr), alias));
                    }
                }
                
                if select_items.is_empty() {
                    select_items.push("*".to_string());
                }
                
                format!("SELECT {} FROM ({}) AS sub", 
                    select_items.join(", "), child_sql)
            },
            
            LogicNode::Filter { expression, child } => {
                let child_sql = self.generate(child);
                format!("SELECT * FROM ({}) AS sub WHERE {}", 
                    child_sql, self.format_expr(expression))
            },
            
            LogicNode::Join { children, condition, join_type } => {
                if children.is_empty() {
                    return "(SELECT 1)".to_string();
                }
                
                // 优化：尝试扁平化简单的 ExtensionalData 节点
                let mut optimized_children = Vec::new();
                let mut from_clauses = Vec::new();
                let mut alias_counter = 0;
                
                for child in children.iter() {
                    match child {
                        LogicNode::ExtensionalData { table_name, .. } => {
                            // 直接使用表名，不需要子查询
                            let alias = format!("t{}", alias_counter);
                            from_clauses.push(format!("{} AS {}", table_name, alias));
                            optimized_children.push((child.clone(), alias));
                            alias_counter += 1;
                        },
                        _ => {
                            // 复杂节点仍然使用子查询
                            let child_sql = self.generate(child);
                            let alias = format!("t{}", alias_counter);
                            from_clauses.push(format!("({}) AS {}", child_sql, alias));
                            optimized_children.push((child.clone(), alias));
                            alias_counter += 1;
                        }
                    }
                }
                
                let mut sql = format!("SELECT * FROM {}", from_clauses[0]);
                
                for (i, from_clause) in from_clauses.iter().enumerate().skip(1) {
                    let join_clause = match join_type {
                        JoinType::Inner => format!("INNER JOIN {}", from_clause),
                        JoinType::Left => format!("LEFT JOIN {}", from_clause),
                        JoinType::Union => format!("FULL OUTER JOIN {}", from_clause),
                    };
                    
                    if let Some(condition) = condition {
                        let formatted_condition = self.format_join_condition(condition, &optimized_children[0].1, &optimized_children[i].1);
                        sql = format!("{} {} ON {}", sql, join_clause, formatted_condition);
                    } else {
                        sql = format!("{} {}", sql, join_clause);
                    }
                }
                
                sql
            },
            
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                let alias = self.generate_table_alias(table_name);
                let mut columns = Vec::new();
                
                for (var, col) in column_mapping {
                    columns.push(format!("{}.{} AS {}", alias, col, var));
                }
                
                if columns.is_empty() {
                    format!("SELECT * FROM {} AS {}", table_name, alias)
                } else {
                    format!("SELECT {} FROM {} AS {}", 
                        columns.join(", "), table_name, alias)
                }
            },
            
            LogicNode::Union(children) => {
                let parts: Vec<String> = children.iter()
                    .map(|c| format!("({})", self.generate(c)))
                    .collect();
                format!("({})", parts.join(" UNION ALL "))
            },
            
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                let child_sql = self.generate(child);
                let mut select_items = Vec::new();
                
                for col in group_by {
                    select_items.push(col.clone());
                }
                
                for (alias, expr) in aggregates {
                    select_items.push(format!("{} AS {}", self.format_expr(expr), alias));
                }
                
                let mut sql = format!("SELECT {} FROM ({}) AS sub", 
                    select_items.join(", "), child_sql);
                
                if !group_by.is_empty() {
                    sql = format!("{} GROUP BY {}", sql, group_by.join(", "));
                }
                
                sql
            },
            
            LogicNode::IntensionalData { predicate, .. } => {
                format!("/* Unfolded Predicate: {} */ SELECT NULL", predicate)
            },
            LogicNode::Limit { limit, offset, order_by: _, child } => {
                let child_sql = self.generate(child);
                if let Some(off) = offset {
                    format!("{} LIMIT {} OFFSET {}", child_sql, limit, off)
                } else {
                    format!("{} LIMIT {}", child_sql, limit)
                }
            },
            LogicNode::Values { variables, rows } => {
                let mut row_sqls = Vec::new();
                for row in rows {
                    let mut val_sqls = Vec::new();
                    for val in row {
                        val_sqls.push(self.format_expr(&Expr::Term(val.clone())));
                    }
                    row_sqls.push(format!("({})", val_sqls.join(", ")));
                }
                format!("SELECT * FROM (VALUES {}) AS t({})", 
                    row_sqls.join(", "),
                    variables.join(", ")
                )
            }
            LogicNode::Path { .. } => {
                // [S4-P1-1] Property paths require recursive CTEs
                "/* Property Path requires recursive CTE implementation */ SELECT NULL".to_string()
            }
            LogicNode::Graph { .. } => {
                // [S5-P0-2] Named Graph SQL placeholder
                "/* Named Graph requires graph table mapping */ SELECT NULL".to_string()
            }
            LogicNode::GraphUnion { .. } => {
                // [S5-P0-2] GraphUnion SQL placeholder
                "/* Graph Union requires multiple graph access */ SELECT NULL".to_string()
            }
            LogicNode::Service { endpoint, .. } => {
                // [S6-P1-2] SERVICE nodes are materialized before SQL generation
                format!("/* SERVICE node for {} should be materialized */ SELECT NULL", endpoint)
            }
            LogicNode::SubQuery { .. } => {
                // [S8-P0-4] SubQuery not yet implemented
                "/* SubQuery not yet implemented */ SELECT NULL".to_string()
            }
            LogicNode::CorrelatedJoin { .. } => {
                // [S8-P0-4] CorrelatedJoin not yet implemented
                "/* CorrelatedJoin not yet implemented */ SELECT NULL".to_string()
            }
            LogicNode::RecursivePath { .. } => {
                // [S9-P2] RecursivePath not yet implemented
                "/* RecursivePath requires recursive CTE implementation */ SELECT NULL".to_string()
            }
            _ => "/* Unsupported LogicNode variant */ SELECT NULL".to_string()
        }
    }

    fn format_expr(&self, expr: &Expr) -> String {
        match expr {
            Expr::Term(term) => term.to_string(),
            Expr::Compare { left, op, right } => {
                format!("{} {} {}", self.format_expr(left), op, self.format_expr(right))
            },
            Expr::Logical { op, args } => {
                match op {
                    LogicalOp::And => {
                        format!("({})", args.iter()
                            .map(|arg| self.format_expr(arg))
                            .collect::<Vec<_>>()
                            .join(" AND "))
                    },
                    LogicalOp::Or => {
                        format!("({})", args.iter()
                            .map(|arg| self.format_expr(arg))
                            .collect::<Vec<_>>()
                            .join(" OR "))
                    },
                    LogicalOp::Not => {
                        format!("NOT ({})", self.format_expr(&args[0]))
                    },
                }
            },
            Expr::Function { name, args } => {
                match name.as_str() {
                    "And" => format!("({} AND {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Or" => format!("({} OR {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Eq" => format!("{} = {}", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Neq" => format!("{} <> {}", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Add" => format!("({} + {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Sub" => format!("({} - {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Mul" => format!("({} * {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Div" => format!("({} / {})", 
                        self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Count" => {
                        if args.is_empty() {
                            "COUNT(*)".to_string()
                        } else {
                            format!("COUNT({})", self.format_expr(&args[0]))
                        }
                    }
                    "Sum" => {
                        if args.is_empty() {
                            "SUM(1)".to_string()
                        } else {
                            format!("SUM({})", self.format_expr(&args[0]))
                        }
                    }
                    "Avg" => {
                        if args.is_empty() {
                            "AVG(1)".to_string()
                        } else {
                            format!("AVG({})", self.format_expr(&args[0]))
                        }
                    }
                    "Max" => {
                        if args.is_empty() {
                            "MAX(1)".to_string()
                        } else {
                            format!("MAX({})", self.format_expr(&args[0]))
                        }
                    }
                    "Min" => {
                        if args.is_empty() {
                            "MIN(1)".to_string()
                        } else {
                            format!("MIN({})", self.format_expr(&args[0]))
                        }
                    }
                    _ => format!("{}({})", name, args.iter()
                        .map(|arg| self.format_expr(arg))
                        .collect::<Vec<_>>()
                        .join(", ")),
                }
            },
            Expr::Exists { patterns, .. } => {
                // Generate subquery SQL from patterns - placeholder for now
                format!("EXISTS (SELECT 1 FROM /* {} patterns */ WHERE 1=1)", patterns.len())
            },
            Expr::NotExists { patterns, .. } => {
                format!("NOT EXISTS (SELECT 1 FROM /* {} patterns */ WHERE 1=1)", patterns.len())
            },
            Expr::Arithmetic { left, op, right } => {
                let op_str = match op {
                    crate::ir::expr::ArithmeticOp::Add => "+",
                    crate::ir::expr::ArithmeticOp::Sub => "-",
                    crate::ir::expr::ArithmeticOp::Mul => "*",
                    crate::ir::expr::ArithmeticOp::Div => "/",
                };
                format!("({} {} {})", self.format_expr(left), op_str, self.format_expr(right))
            },
        }
    }

    fn get_main_alias(&self) -> String {
        "t0".to_string()
    }
}
