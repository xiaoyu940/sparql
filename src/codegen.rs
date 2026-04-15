use crate::ir::node::LogicNode;
use crate::ir::expr::{Expr, Term};

pub mod enhanced_generator;
pub mod postgresql_generator;

pub use postgresql_generator::PostgreSQLGenerator;

pub struct PostgreSqlGenerator;

impl PostgreSqlGenerator {
    pub fn new() -> Self {
        Self
    }

    pub fn generate(&self, node: &LogicNode) -> String {
        match node {
            LogicNode::Construction { projected_vars, bindings, child } => {
                let mut cols = Vec::new();
                for v in projected_vars {
                    if let Some(expr) = bindings.get(v) {
                        cols.push(format!("{} AS {}", self.format_expr(expr), v));
                    } else {
                        cols.push(v.clone());
                    }
                }
                for (v, expr) in bindings {
                    if !projected_vars.contains(v) {
                        cols.push(format!("{} AS {}", self.format_expr(expr), v));
                    }
                }
                if cols.is_empty() { cols.push("*".to_string()); }
                format!("SELECT {} FROM ({}) AS sub", cols.join(", "), self.generate(child))
            }
            LogicNode::Filter { expression, child } => {
                format!("SELECT * FROM ({}) AS sub WHERE {}", self.generate(child), self.format_expr(expression))
            }
            LogicNode::Join { children, condition, join_type: _ } => {
                if children.is_empty() { return "(SELECT 1)".to_string(); }
                
                let parts: Vec<String> = children.iter()
                    .enumerate()
                    .map(|(i, c)| format!("({}) AS t{}", self.generate(c), i))
                    .collect();
                
                let mut sql = parts.join(" CROSS JOIN ");
                if let Some(cond) = condition {
                    sql = format!("SELECT * FROM {} WHERE {}", sql, self.format_expr(cond));
                }
                sql
            }
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                let mut cols = Vec::new();
                for (var, col) in column_mapping {
                    cols.push(format!("{} AS \"{}\"", col, var));
                }
                if cols.is_empty() {
                    format!("SELECT * FROM {}", table_name)
                } else {
                    format!("SELECT {} FROM {}", cols.join(", "), table_name)
                }
            }
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                let mut selects = Vec::new();
                for g in group_by { selects.push(g.clone()); }
                for (alias, expr) in aggregates {
                    selects.push(format!("{} AS \"{}\"", self.format_expr(expr), alias));
                }
                let mut sql = format!("SELECT {} FROM ({}) AS sub", selects.join(", "), self.generate(child));
                if !group_by.is_empty() {
                    sql = format!("{} GROUP BY {}", sql, group_by.join(", "));
                }
                sql
            }
            LogicNode::Union(children) => {
                let parts: Vec<String> = children.iter().map(|c| self.generate(c)).collect();
                format!("({})", parts.join(" UNION ALL "))
            }
            LogicNode::IntensionalData { predicate, .. } => {
                format!("(/* Unfolded Predicate: {} */ SELECT NULL)", predicate)
            },
            LogicNode::Limit { .. } => {
                "(/* Limit not supported in this generator */ SELECT NULL)".to_string()
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
                // [S4-P1-1] Leaf-like for DOT
                "/* Property Path requires recursive CTE implementation */ SELECT NULL".to_string()
            }
            LogicNode::Graph { .. } => {
                // [S5-P0-2] Graph node SQL placeholder
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
            Expr::Function { name, args } => {
                match name.as_str() {
                    "And" => format!("({} AND {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Or" => format!("({} OR {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Eq" => format!("{} = {}", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Neq" => format!("{} <> {}", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Add" => format!("({} + {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Sub" => format!("({} - {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Mul" => format!("({} * {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Div" => format!("({} / {})", self.format_expr(&args[0]), self.format_expr(&args[1])),
                    "Count" => format!("COUNT({})", self.format_expr(&args[0])),
                    "Sum" => format!("SUM({})", self.format_expr(&args[0])),
                    "Avg" => format!("AVG({})", self.format_expr(&args[0])),
                    "Max" => format!("MAX({})", self.format_expr(&args[0])),
                    "CONCAT" => format!("CONCAT({})", args.iter().map(|a| self.format_expr(a)).collect::<Vec<_>>().join(", ")),
                    _ => expr.to_string(),
                }
            }
            Expr::Term(Term::Variable(var_name)) => {
                // For now, return the variable name as-is with table alias placeholder
                // A full implementation would need access to the column mapping context
                format!("col_{}", var_name.to_lowercase())
            }
            Expr::Term(Term::Constant(val)) => {
                format!("'{}'", val)
            }
            _ => expr.to_string(),
        }
    }

}
