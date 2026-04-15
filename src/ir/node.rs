use std::collections::HashMap;
use std::sync::Arc;
use crate::ir::expr::{Expr, Term};
use crate::metadata::TableMetadata;

/// Join 类型
///
/// 表示 SQL 中的连接类型：
/// - Inner: 内连接
/// - Left: 左外连接
/// - Union: 并集操作
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum JoinType {
    /// 内连接
    Inner,
    /// 左外连接
    Left,
    /// 并集操作（也可作为 Join 变体处理）
    Union,
}

/// LogicNode: 中间查询 (IQ) 的主要 IR
///
/// 表示查询计划树的节点类型，支持：
/// - Construction: 投影、别名和计算列
/// - Join: N 元连接操作符
/// - ExtensionalData: 物理表扫描
/// - IntensionalData: 未展开的谓词节点
/// - Filter: 过滤操作
/// - Union: 并集操作
/// - Aggregation: 分组聚合
/// - Limit: 分页限制
#[derive(Debug, Clone, PartialEq)]
pub enum LogicNode {
    /// Projection, Aliases and Calculated Columns.
    /// maps logic variable names to expressions.
    Construction {
        projected_vars: Vec<String>,
        bindings: HashMap<String, Expr>, // variable_name -> expression
        child: Box<LogicNode>,
    },

    /// N-ary Join operator, facilitating join reordering.
    Join {
        children: Vec<LogicNode>,
        condition: Option<Expr>,
        join_type: JoinType,
    },

    /// Physical Table Scan, carries DB constraint info.
    ExtensionalData {
        table_name: String,
        /// Binding of Variable names to physical column names (Variable -> Physical Column).
        column_mapping: HashMap<String, String>,
        metadata: Arc<TableMetadata>,
    },

    /// Higher-level predicate node that HAS NOT BEEN unfolded yet.
    IntensionalData {
        predicate: String,
        args: Vec<Term>,
    },

    /// Filter operator.
    Filter {
        expression: Expr,
        child: Box<LogicNode>,
    },

    /// Set Union operator.
    Union(Vec<LogicNode>),

    /// Aggregation operator for GROUP BY and aggregate functions.
    Aggregation {
        group_by: Vec<String>,
        aggregates: HashMap<String, Expr>, // alias -> expression (e.g., COUNT(?s))
        having: Option<Expr>,
        child: Box<LogicNode>,
    },
    
    /// Limit operator for pagination.
    /// [S4-P0-1] 添加 order_by 支持
    Limit {
        limit: usize,
        offset: Option<usize>,
        order_by: Vec<(String, bool)>, // (变量名, 是否降序)
        child: Box<LogicNode>,
    },
    
    /// VALUES data block.
    Values {
        variables: Vec<String>,
        rows: Vec<Vec<Term>>,
    },
    
    /// [S4-P1-1] Property Path operator for SPARQL path expressions
    /// Supports *, +, ?, sequence, and alternative paths
    Path {
        subject: Term,
        path: PropertyPath,
        object: Term,
    },
    
    /// [S5-P0-2] Named Graph operator for SPARQL GRAPH clause
    /// Queries within a specific named graph
    Graph {
        graph_name: Term,
        child: Box<LogicNode>,
        is_named_graph: bool,
    },
    
    /// [S5-P0-2] Graph Union for variable graph patterns
    /// GRAPH ?g { ... } where ?g binds to multiple graphs
    GraphUnion {
        graph_var: String,
        children: Vec<LogicNode>,
    },

    /// [S6-P1-2] Federated SERVICE query node.
    ///
    /// Represents a SPARQL SERVICE clause that queries an external SPARQL endpoint.
    /// During execution, this node is materialized into a PostgreSQL temporary table,
    /// then replaced by an ExtensionalData scan so downstream SQL generation is unchanged.
    Service {
        /// The SPARQL endpoint URL (e.g. "https://query.wikidata.org/sparql")
        endpoint: String,
        /// Variables that this SERVICE block is expected to produce
        output_vars: Vec<String>,
        /// The inner logic plan describing what to ask the remote endpoint
        inner_plan: Box<LogicNode>,
        /// If true, errors are silently ignored and an empty result is returned
        silent: bool,
    },

    /// [S8-P0-4] SubQuery node for nested SPARQL queries
    SubQuery {
        /// The inner query plan
        inner: Box<LogicNode>,
        /// Correlated variables from outer query
        correlated_vars: Vec<String>,
    },

    /// [S8-P0-4] CorrelatedJoin node for correlated subqueries
    CorrelatedJoin {
        /// The outer (left) plan
        outer: Box<LogicNode>,
        /// The inner (correlated) plan
        inner: Box<LogicNode>,
        /// The correlation condition
        condition: Expr,
    },

    /// [S9-P2] RecursivePath node for property path modifiers (*, +)
    /// Generates recursive CTE SQL for transitive closure queries
    RecursivePath {
        /// Base path (anchor query)
        base_path: Box<LogicNode>,
        /// Recursive path step
        recursive_path: Box<LogicNode>,
        /// Starting node variable
        subject: Term,
        /// Ending node variable
        object: Term,
        /// Minimum path length (0 for *, 1 for +)
        min_depth: usize,
        /// Maximum recursion depth limit
        max_depth: usize,
    },
}

/// [S4-P1-1] Property Path types for SPARQL path expressions
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum PropertyPath {
    /// Zero or more repetitions: p*
    Star(Box<PropertyPath>),
    /// One or more repetitions: p+
    Plus(Box<PropertyPath>),
    /// Optional (zero or one): p?
    Optional(Box<PropertyPath>),
    /// Sequence: p1/p2
    Sequence(Vec<PropertyPath>),
    /// Alternative: p1|p2
    Alternative(Vec<PropertyPath>),
    /// Inverse: ^p
    Inverse(Box<PropertyPath>),
    /// Negated property set: !p or !(p1|p2)
    Negated(Vec<String>),
    /// Simple predicate (IRI)
    Predicate(String),
}

impl LogicNode {
    /// Returns the set of all variables used in this node and its children.
    pub fn used_variables(&self) -> std::collections::HashSet<String> {
        let mut vars = std::collections::HashSet::new();
        match self {
            LogicNode::ExtensionalData { column_mapping, .. } => {
                for v in column_mapping.keys() {
                    vars.insert(v.clone());
                }
            }
            LogicNode::IntensionalData { args, .. } => {
                for arg in args {
                    if let Term::Variable(v) = arg {
                        vars.insert(v.clone());
                    }
                }
            }
            LogicNode::Join { children, .. } => {
                for child in children {
                    vars.extend(child.used_variables());
                }
            }
            LogicNode::Filter { expression, child } => {
                vars.extend(child.used_variables());
                self.extract_vars_from_expr(expression, &mut vars);
            }
            LogicNode::Construction { projected_vars, bindings, child } => {
                // Vars used in children
                // Note: Construction often hides some variables.
                // For simplicity, we track which vars are *mentioned*.
                vars.extend(child.used_variables());
                for v in projected_vars { vars.insert(v.clone()); }
                for expr in bindings.values() {
                    self.extract_vars_from_expr(expr, &mut vars);
                }
            }
            LogicNode::Union(children) => {
                for child in children {
                    vars.extend(child.used_variables());
                }
            }
            LogicNode::Aggregation { group_by, aggregates, having, child } => {
                vars.extend(child.used_variables());
                for v in group_by { vars.insert(v.clone()); }
                for expr in aggregates.values() {
                    self.extract_vars_from_expr(expr, &mut vars);
                }
                if let Some(h) = having {
                    self.extract_vars_from_expr(h, &mut vars);
                }
            }
            LogicNode::Limit { child, .. } => {
                vars.extend(child.used_variables());
            }
            LogicNode::Values { variables, .. } => {
                for v in variables {
                    vars.insert(v.clone());
                }
            }
            LogicNode::Path { subject, object, .. } => {
                if let Term::Variable(v) = subject {
                    vars.insert(v.clone());
                }
                if let Term::Variable(v) = object {
                    vars.insert(v.clone());
                }
            }
            LogicNode::Graph { graph_name, child, .. } => {
                vars.extend(child.used_variables());
                if let Term::Variable(v) = graph_name {
                    vars.insert(v.clone());
                }
            }
            LogicNode::GraphUnion { graph_var, children } => {
                vars.insert(graph_var.clone());
                for child in children {
                    vars.extend(child.used_variables());
                }
            }
            LogicNode::Service { output_vars, inner_plan, .. } => {
                for v in output_vars {
                    vars.insert(v.clone());
                }
                vars.extend(inner_plan.used_variables());
            }
            LogicNode::SubQuery { inner, correlated_vars } => {
                vars.extend(inner.used_variables());
                for v in correlated_vars {
                    vars.insert(v.clone());
                }
            }
            LogicNode::CorrelatedJoin { outer, inner, condition } => {
                vars.extend(outer.used_variables());
                vars.extend(inner.used_variables());
                self.extract_vars_from_expr(condition, &mut vars);
            }
            LogicNode::RecursivePath { base_path, recursive_path, subject, object, .. } => {
                vars.extend(base_path.used_variables());
                vars.extend(recursive_path.used_variables());
                if let Term::Variable(v) = subject {
                    vars.insert(v.clone());
                }
                if let Term::Variable(v) = object {
                    vars.insert(v.clone());
                }
            }
        }
        vars
    }

    fn extract_vars_from_expr(&self, expr: &Expr, vars: &mut std::collections::HashSet<String>) {
        match expr {
            Expr::Term(Term::Variable(v)) => { vars.insert(v.clone()); }
            Expr::Compare { left, right, .. } => {
                self.extract_vars_from_expr(left, vars);
                self.extract_vars_from_expr(right, vars);
            }
            Expr::Logical { args, .. } => {
                for arg in args { self.extract_vars_from_expr(arg, vars); }
            }
            Expr::Function { args, .. } => {
                for arg in args { self.extract_vars_from_expr(arg, vars); }
            }
            _ => {}
        }
    }
}
