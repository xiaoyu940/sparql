use crate::ir::node::{LogicNode, JoinType};
use crate::ir::expr::{Expr, Term, ComparisonOp, LogicalOp};
use std::collections::HashMap;

/// PostgreSQL SQL 生成器
pub struct PostgreSQLGenerator {
    alias_counter: usize,
    table_aliases: HashMap<String, String>,
}

impl PostgreSQLGenerator {
    pub fn new() -> Self {
        Self {
            alias_counter: 0,
            table_aliases: HashMap::new(),
        }
    }

    /// 生成有效的 PostgreSQL SQL
    pub fn generate(&mut self, node: &LogicNode) -> String {
        match node {
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                eprintln!("[DEBUG SQL] ExtensionalData: table={}, columns={:?}", table_name, column_mapping);
                let alias = self.generate_table_alias(table_name);
                format!("SELECT * FROM {} AS {}", table_name, alias)
            },
            
            LogicNode::Join { children, condition, join_type } => {
                eprintln!("[DEBUG SQL] Join: children={}, condition={:?}, join_type={:?}", children.len(), condition, join_type);
                for (i, child) in children.iter().enumerate() {
                    eprintln!("[DEBUG SQL] Join child {}: {:?}", i, child);
                }
                self.generate_join(children, condition, join_type)
            },
            
            LogicNode::Filter { expression, child } => {
                self.generate_filter(child, expression)
            },
            
            LogicNode::Union(children) => {
                self.generate_union(children)
            },
            
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                self.generate_aggregation(child, group_by, aggregates)
            },
            
            LogicNode::Construction { projected_vars, bindings, child } => {
                self.generate_construction(child, projected_vars, bindings)
            },
            
            LogicNode::IntensionalData { .. } => {
                "SELECT 'IntensionalData not supported in SQL' as description".to_string()
            },
            LogicNode::Limit { limit, offset, child, .. } => {
                let child_sql = self.generate(child);
                if let Some(off) = offset {
                    format!("{} LIMIT {} OFFSET {}", child_sql, limit, off)
                } else {
                    format!("{} LIMIT {}", child_sql, limit)
                }
            },
            LogicNode::Values { .. } => {
                "/* VALUES not supported in SQL */ SELECT NULL".to_string()
            },
            LogicNode::Path { .. } => {
                "/* Property Path requires recursive CTE */ SELECT NULL".to_string()
            },
            LogicNode::Graph { .. } => {
                "/* Named Graph requires graph mapping */ SELECT NULL".to_string()
            },
            LogicNode::GraphUnion { .. } => {
                "/* Graph Union requires multiple graph access */ SELECT NULL".to_string()
            },
            LogicNode::Service { endpoint, .. } => {
                format!("/* SERVICE for {} */ SELECT NULL", endpoint)
            }
            LogicNode::SubQuery { .. } => {
                "/* SubQuery not yet implemented */ SELECT NULL".to_string()
            }
            LogicNode::CorrelatedJoin { .. } => {
                "/* CorrelatedJoin not yet implemented */ SELECT NULL".to_string()
            }
            LogicNode::RecursivePath { .. } => {
                "/* RecursivePath requires recursive CTE implementation */ SELECT NULL".to_string()
            }
            _ => "/* Unsupported LogicNode variant */ SELECT NULL".to_string()
        }
    }

    /// 生成 Construction 查询（SELECT 投影）
    fn generate_construction(
        &mut self,
        child: &LogicNode,
        projected_vars: &[String],
        bindings: &HashMap<String, Expr>,
    ) -> String {
        let child_sql = self.generate(child);
        
        // 构建 SELECT 子句
        let mut select_parts = Vec::new();
        
        for var in projected_vars {
            if let Some(expr) = bindings.get(var) {
                // 有表达式绑定，生成表达式 AS 别名
                let expr_sql = self.format_expr(expr);
                select_parts.push(format!("{} AS {}", expr_sql, var));
            } else {
                // 无绑定，直接使用变量名
                select_parts.push(var.clone());
            }
        }
        
        let select_clause = if select_parts.is_empty() {
            "*".to_string()
        } else {
            select_parts.join(", ")
        };
        
        format!("SELECT {} FROM ({}) AS sub", select_clause, child_sql)
    }

    /// 生成表别名
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

    /// 生成 JOIN 查询 - 使用扁平化结构而非嵌套子查询
    fn generate_join(&mut self, children: &[LogicNode], condition: &Option<Expr>, join_type: &JoinType) -> String {
        eprintln!("[DEBUG SQL generate_join] children count: {}", children.len());
        for (i, child) in children.iter().enumerate() {
            match child {
                LogicNode::ExtensionalData { table_name, .. } => {
                    eprintln!("[DEBUG SQL generate_join] child {}: ExtensionalData table={}", i, table_name);
                },
                LogicNode::Join { .. } => {
                    eprintln!("[DEBUG SQL generate_join] child {}: Join (nested)", i);
                },
                _ => {
                    eprintln!("[DEBUG SQL generate_join] child {}: other type", i);
                }
            }
        }
        
        if children.len() < 2 {
            return self.generate(&children[0]);
        }

        // 收集所有表和它们的别名 - 扁平化处理嵌套Joins
        let mut tables: Vec<(String, String)> = Vec::new(); // (table_name, alias)
        let mut all_conditions: Vec<Option<Expr>> = Vec::new(); // 每个JOIN的条件
        
        // 递归函数收集所有表和条件 - 跟踪已访问的节点避免重复
        fn collect_tables_from_node(
            node: &LogicNode,
            tables: &mut Vec<(String, String)>,
            conditions: &mut Vec<Option<Expr>>,
            generator: &mut PostgreSQLGenerator,
            visited: &mut std::collections::HashSet<String>, // 跟踪已处理的表
        ) {
            match node {
                LogicNode::ExtensionalData { table_name, .. } => {
                    // 只有第一次遇到这个表时才添加
                    if visited.insert(table_name.clone()) {
                        let alias = generator.generate_table_alias(table_name);
                        tables.push((table_name.clone(), alias));
                    }
                },
                LogicNode::Join { children, condition, .. } => {
                    // 递归收集所有子节点
                    for (i, child) in children.iter().enumerate() {
                        if i > 0 && children.len() > 1 {
                            // 对于右子节点，记录join条件
                            collect_tables_from_node(child, tables, conditions, generator, visited);
                            if i == children.len() - 1 {
                                conditions.push(condition.clone());
                            }
                        } else {
                            collect_tables_from_node(child, tables, conditions, generator, visited);
                        }
                    }
                },
                _ => {}
            }
        }
        
        let mut visited: std::collections::HashSet<String> = std::collections::HashSet::new();
        
        // 收集所有表
        for child in children {
            collect_tables_from_node(child, &mut tables, &mut all_conditions, self, &mut visited);
        }
        
        if tables.is_empty() {
            return "SELECT 1 WHERE 1=0".to_string(); // 空结果
        }
        
        if tables.len() == 1 {
            return format!("SELECT * FROM {} AS {}", tables[0].0, tables[0].1);
        }
        
        // 生成JOIN子句
        let join_clause = match join_type {
            JoinType::Inner => "INNER JOIN",
            JoinType::Left => "LEFT JOIN",
            JoinType::Union => "UNION JOIN",
        };
        
        // 构建SQL - 使用收集到的所有表和条件
        let mut sql = format!("SELECT * FROM {} AS {}", tables[0].0, tables[0].1);
        
        for i in 1..tables.len() {
            sql.push_str(&format!(" {} {} AS {}", join_clause, tables[i].0, tables[i].1));
            
            // 添加ON条件 - 使用对应的条件
            if let Some(cond) = all_conditions.get(i-1).and_then(|c| c.as_ref()) {
                let on = self.generate_join_on_clause(cond, &tables[0].1, &tables[i].1);
                sql.push_str(&format!(" ON {}", on));
            } else if let Some(cond) = condition {
                // 如果没有收集到条件，使用顶层条件
                let on = self.generate_join_on_clause(cond, &tables[0].1, &tables[i].1);
                sql.push_str(&format!(" ON {}", on));
            }
        }
        
        sql
    }

    /// 生成过滤查询
    fn generate_filter(&mut self, child: &LogicNode, expression: &Expr) -> String {
        let child_sql = self.generate(child);
        let where_clause = self.generate_where_clause(expression);
        
        if child_sql.contains("WHERE") {
            format!("{} AND {}", child_sql, where_clause)
        } else {
            format!("{} WHERE {}", child_sql, where_clause)
        }
    }

    /// 生成 UNION 查询
    fn generate_union(&mut self, children: &[LogicNode]) -> String {
        let sqls: Vec<String> = children.iter()
            .map(|child| self.generate(child))
            .collect();
        
        sqls.join(" UNION ")
    }

    /// 生成聚合查询
    fn generate_aggregation(&mut self, child: &LogicNode, group_vars: &[String], aggregates: &HashMap<String, Expr>) -> String {
        let child_sql = self.generate(child);
        
        let select_clause = if group_vars.is_empty() && aggregates.is_empty() {
            "COUNT(*)".to_string()
        } else {
            let mut parts = Vec::new();
            
            // 添加分组变量
            for var in group_vars {
                parts.push(var.clone());
            }
            
            // 添加聚合函数
            for (alias, expr) in aggregates {
                parts.push(format!("{} AS {}", self.generate_aggregate_expr(expr), alias));
            }
            
            parts.join(", ")
        };

        let group_by_clause = if group_vars.is_empty() {
            String::new()
        } else {
            format!(" GROUP BY {}", group_vars.join(", "))
        };

        format!("SELECT {} FROM ({}) AS sub{}", select_clause, child_sql, group_by_clause)
    }

    /// 生成 JOIN ON 子句
    fn generate_join_on_clause(&self, condition: &Expr, left_alias: &str, right_alias: &str) -> String {
        match condition {
            Expr::Compare { left, op, right } => {
                let left_expr = self.format_expr_with_alias(left, left_alias);
                let right_expr = self.format_expr_with_alias(right, right_alias);
                match op {
                    ComparisonOp::Eq => format!("{} = {}", left_expr, right_expr),
                    _ => format!("{} = {}", left_expr, right_expr),
                }
            },
            Expr::Function { name, args } if name == "Eq" => {
                let left = self.format_expr_with_alias(&args[0], left_alias);
                let right = self.format_expr_with_alias(&args[1], right_alias);
                format!("{} = {}", left, right)
            },
            Expr::Function { name, args } if name == "And" => {
                let conditions: Vec<String> = args.iter()
                    .map(|arg| self.generate_join_on_clause(arg, left_alias, right_alias))
                    .collect();
                conditions.join(" AND ")
            },
            _ => {
                "TRUE".to_string()
            },
        }
    }

    /// 生成 WHERE 子句
    fn generate_where_clause(&self, condition: &Expr) -> String {
        match condition {
            Expr::Compare { left, op, right } => {
                let left_expr = self.format_expr(left);
                let right_expr = self.format_expr(right);
                match op {
                    ComparisonOp::Eq => format!("{} = {}", left_expr, right_expr),
                    ComparisonOp::Gt => format!("{} > {}", left_expr, right_expr),
                    ComparisonOp::Lt => format!("{} < {}", left_expr, right_expr),
                    ComparisonOp::Gte => format!("{} >= {}", left_expr, right_expr),
                    ComparisonOp::Lte => format!("{} <= {}", left_expr, right_expr),
                    ComparisonOp::Neq => format!("{} <> {}", left_expr, right_expr),
                    ComparisonOp::In => format!("{} IN ({})", left_expr, right_expr),
                    ComparisonOp::NotIn => format!("{} NOT IN ({})", left_expr, right_expr),
                }
            },
            Expr::Logical { op, args } => {
                let conditions: Vec<String> = args.iter()
                    .map(|arg| self.generate_where_clause(arg))
                    .collect();
                match op {
                    LogicalOp::And => format!("({})", conditions.join(" AND ")),
                    LogicalOp::Or => format!("({})", conditions.join(" OR ")),
                    LogicalOp::Not => format!("NOT ({})", conditions.join(" AND ")),
                }
            },
            Expr::Term(Term::Literal { value, .. }) => {
                format!("'{}'", value)
            },
            Expr::Term(Term::Variable(var)) => {
                var.clone()
            },
            Expr::Term(Term::Constant(const_val)) => {
                format!("'{}'", const_val)
            },
            _ => {
                "1=1".to_string()
            }
        }
    }

    /// 生成聚合表达式
    fn generate_aggregate_expr(&self, expr: &Expr) -> String {
        match expr {
            Expr::Function { name, args } => {
                match name.as_str() {
                    "Count" => {
                        if args.is_empty() {
                            "COUNT(*)".to_string()
                        } else {
                            let arg = self.format_expr(&args[0]);
                            format!("COUNT({})", arg)
                        }
                    },
                    "Avg" => {
                        let arg = self.format_expr(&args[0]);
                        format!("AVG({})", arg)
                    },
                    "Max" => {
                        let arg = self.format_expr(&args[0]);
                        format!("MAX({})", arg)
                    },
                    "Min" => {
                        let arg = self.format_expr(&args[0]);
                        format!("MIN({})", arg)
                    },
                    "Sum" => {
                        let arg = self.format_expr(&args[0]);
                        format!("SUM({})", arg)
                    },
                    _ => {
                        format!("{}({})", name, args.iter().map(|arg| self.format_expr(arg)).collect::<Vec<_>>().join(", "))
                    }
                }
            },
            _ => {
                self.format_expr(expr)
            }
        }
    }

    /// 格式化表达式
    fn format_expr(&self, expr: &Expr) -> String {
        match expr {
            Expr::Term(Term::Literal { value, .. }) => {
                if value.chars().all(|c: char| c.is_ascii_digit() || c == '.' || c == '-') {
                    value.clone()
                } else {
                    format!("'{}'", value)
                }
            },
            Expr::Term(Term::Variable(var)) => {
                var.clone()
            },
            Expr::Term(Term::Constant(const_val)) => {
                format!("'{}'", const_val)
            },
            Expr::Function { name, args } => {
                format!("{}({})", name, args.iter().map(|arg| self.format_expr(arg)).collect::<Vec<_>>().join(", "))
            },
            _ => {
                "NULL".to_string()
            }
        }
    }

    /// 格式化带表别名的表达式
    fn format_expr_with_alias(&self, expr: &Expr, alias: &str) -> String {
        let formatted = self.format_expr(expr);
        if formatted.contains('.') {
            formatted
        } else {
            format!("{}.{}", alias, formatted)
        }
    }

    /// 从 SQL 中提取表别名
    #[allow(dead_code)]
    fn extract_table_alias(&self, sql: &str) -> String {
        if let Some(start) = sql.find(" AS ") {
            let alias_part = &sql[start + 4..];
            if let Some(end) = alias_part.find(' ') {
                alias_part[..end].to_string()
            } else {
                alias_part.to_string()
            }
        } else {
            "t0".to_string()
        }
    }

    /// 重置生成器状态
    pub fn reset(&mut self) {
        self.alias_counter = 0;
        self.table_aliases.clear();
    }
}

impl Default for PostgreSQLGenerator {
    fn default() -> Self {
        Self::new()
    }
}
