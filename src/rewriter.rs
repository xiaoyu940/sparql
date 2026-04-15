use crate::ir::node::LogicNode;
use crate::ir::expr::{Expr, Term, LogicalOp, ComparisonOp};
use crate::optimizer::OptimizerContext;
use std::collections::HashMap;

/// 查询重写器
#[derive(Debug, Clone)]
pub struct QueryRewriter {
    pub rewrite_rules: Vec<RewriteRule>,
    pub max_iterations: usize,
    pub enable_statistics: bool,
}

/// 重写规则
#[derive(Debug, Clone)]
pub struct RewriteRule {
    pub name: String,
    pub description: String,
    pub pattern: RewritePattern,
    pub replacement: RewriteReplacement,
    pub priority: u32,
    pub condition: Option<RewriteCondition>,
}

/// 重写模式
#[derive(Debug, Clone)]
pub enum RewritePattern {
    /// 匹配特定节点类型
    NodeType(NodeTypePattern),
    /// 匹配表达式
    Expression(ExprPattern),
    /// 复合模式
    Composite(Vec<RewritePattern>),
    /// 通配符
    Wildcard,
}

/// 节点类型模式
#[derive(Debug, Clone)]
pub enum NodeTypePattern {
    Join,
    Filter,
    Union,
    Aggregation,
    Construction,
    ExtensionalData,
    IntensionalData,
}

/// 表达式模式
#[derive(Debug, Clone)]
pub enum ExprPattern {
    Function { name: String, args: Vec<ExprPattern> },
    Compare { op: ComparisonOp, left: Box<ExprPattern>, right: Box<ExprPattern> },
    Logical { op: LogicalOp, args: Vec<ExprPattern> },
    Term(TermPattern),
}

/// 项模式
#[derive(Debug, Clone)]
pub enum TermPattern {
    Variable(String),
    Constant(String),
    Wildcard,
}

/// 重写替换
#[derive(Debug, Clone)]
pub enum RewriteReplacement {
    /// 复制节点
    Copy,
    /// 创建新节点
    NewNode(NewNodeTemplate),
    /// 表达式替换
    Expression(ExprTemplate),
    /// 复合替换
    Composite(Vec<RewriteReplacement>),
}

/// 新节点模板
#[derive(Debug, Clone)]
pub struct NewNodeTemplate {
    pub node_type: NodeTypePattern,
    pub attributes: HashMap<String, ExprTemplate>,
}

/// 表达式模板
#[derive(Debug, Clone)]
pub enum ExprTemplate {
    Constant(String),
    Variable(String),
    Function { name: String, args: Vec<ExprTemplate> },
}

/// 重写条件
#[derive(Debug, Clone)]
pub enum RewriteCondition {
    Always,
    Never,
    Expression(Expr),
    Custom(String), // 自定义条件名称
}

/// 重写统计
#[derive(Debug, Clone)]
pub struct RewriteStatistics {
    pub rules_applied: HashMap<String, u32>,
    pub total_rewrites: u32,
    pub iterations: u32,
    pub rewrite_time_ms: u64,
}

/// 重写结果
#[derive(Debug, Clone)]
pub struct RewriteResult {
    pub rewritten_query: LogicNode,
    pub statistics: RewriteStatistics,
    pub success: bool,
}

impl QueryRewriter {
    pub fn new() -> Self {
        Self {
            rewrite_rules: Vec::new(),
            max_iterations: 10,
            enable_statistics: true,
        }
    }
    
    /// 添加重写规则
    pub fn add_rule(&mut self, rule: RewriteRule) {
        self.rewrite_rules.push(rule);
    }
    
    /// 执行查询重写
    pub fn rewrite(&mut self, query: &LogicNode, ctx: &OptimizerContext) -> RewriteResult {
        let start_time = std::time::Instant::now();
        let mut current_query = query.clone();
        let mut stats = RewriteStatistics {
            rules_applied: HashMap::new(),
            total_rewrites: 0,
            iterations: 0,
            rewrite_time_ms: 0,
        };
        
        // 按优先级排序规则
        let mut sorted_rules = self.rewrite_rules.clone();
        sorted_rules.sort_by(|a, b| b.priority.cmp(&a.priority));
        
        for iteration in 0..self.max_iterations {
            let mut rewritten_this_iteration = false;
            
            for rule in &sorted_rules {
                if self.should_apply_rule(rule, &current_query, ctx) {
                    if let Some(new_query) = self.apply_rule(rule, &current_query) {
                        current_query = new_query;
                        rewritten_this_iteration = true;
                        stats.total_rewrites += 1;
                        
                        let count = stats.rules_applied.entry(rule.name.clone()).or_insert(0);
                        *count += 1;
                    }
                }
            }
            
            stats.iterations = (iteration + 1) as u32;
            
            if !rewritten_this_iteration {
                break; // 没有更多重写，退出
            }
        }
        
        stats.rewrite_time_ms = start_time.elapsed().as_millis() as u64;
        
        RewriteResult {
            rewritten_query: current_query,
            statistics: stats,
            success: true,
        }
    }
    
    /// 检查是否应该应用规则
    fn should_apply_rule(&self, rule: &RewriteRule, _query: &LogicNode, _ctx: &OptimizerContext) -> bool {
        // 检查条件
        match &rule.condition {
            Some(RewriteCondition::Always) => true,
            Some(RewriteCondition::Never) => false,
            Some(RewriteCondition::Expression(_expr)) => {
                // 简化版本：总是返回 true
                true
            },
            Some(RewriteCondition::Custom(_)) => {
                // 自定义条件逻辑
                true
            },
            None => true,
        }
    }
    
    /// 应用重写规则
    fn apply_rule(&self, rule: &RewriteRule, query: &LogicNode) -> Option<LogicNode> {
        match &rule.pattern {
            RewritePattern::NodeType(node_type) => {
                self.apply_node_type_rule(rule, query, node_type)
            },
            RewritePattern::Expression(expr_pattern) => {
                self.apply_expression_rule(rule, query, expr_pattern)
            },
            RewritePattern::Composite(patterns) => {
                self.apply_composite_rule(rule, query, patterns)
            },
            RewritePattern::Wildcard => {
                Some(query.clone())
            },
        }
    }
    
    /// 应用节点类型规则
    fn apply_node_type_rule(&self, rule: &RewriteRule, query: &LogicNode, node_type: &NodeTypePattern) -> Option<LogicNode> {
        let matches = self.matches_node_type(query, node_type);
        
        if matches {
            match &rule.replacement {
                RewriteReplacement::Copy => Some(query.clone()),
                RewriteReplacement::NewNode(template) => {
                    self.create_node_from_template(template, query)
                },
                RewriteReplacement::Expression(_) => None,
                RewriteReplacement::Composite(_) => None,
            }
        } else {
            // 递归应用到子节点
            self.apply_to_children(rule, query)
        }
    }
    
    /// 应用表达式规则
    fn apply_expression_rule(&self, rule: &RewriteRule, query: &LogicNode, expr_pattern: &ExprPattern) -> Option<LogicNode> {
        // 在查询中查找匹配的表达式
        if let Some(matched_expr) = self.find_matching_expression(query, expr_pattern) {
            // 应用重写
            self.rewrite_expression(query, &matched_expr, &rule.replacement)
        } else {
            None
        }
    }
    
    /// 应用复合规则
    fn apply_composite_rule(&self, rule: &RewriteRule, query: &LogicNode, patterns: &[RewritePattern]) -> Option<LogicNode> {
        let mut current_query = query.clone();
        
        for _pattern in patterns {
            if let Some(new_query) = self.apply_rule(rule, &current_query) {
                current_query = new_query;
            } else {
                return None;
            }
        }
        
        Some(current_query)
    }
    
    /// 检查节点类型是否匹配
    fn matches_node_type(&self, query: &LogicNode, node_type: &NodeTypePattern) -> bool {
        match (query, node_type) {
            (LogicNode::Join { .. }, NodeTypePattern::Join) => true,
            (LogicNode::Filter { .. }, NodeTypePattern::Filter) => true,
            (LogicNode::Union(_), NodeTypePattern::Union) => true,
            (LogicNode::Aggregation { .. }, NodeTypePattern::Aggregation) => true,
            (LogicNode::Construction { .. }, NodeTypePattern::Construction) => true,
            (LogicNode::ExtensionalData { .. }, NodeTypePattern::ExtensionalData) => true,
            (LogicNode::IntensionalData { .. }, NodeTypePattern::IntensionalData) => true,
            _ => false,
        }
    }
    
    /// 查找匹配的表达式
    fn find_matching_expression(&self, query: &LogicNode, pattern: &ExprPattern) -> Option<Expr> {
        // 简化版本：在查询中递归查找
        self.search_expression_in_node(query, pattern)
    }
    
    /// 在节点中搜索表达式
    fn search_expression_in_node(&self, node: &LogicNode, pattern: &ExprPattern) -> Option<Expr> {
        match node {
            LogicNode::Filter { expression, child } => {
                if self.matches_expression_pattern(expression, pattern) {
                    Some(expression.clone())
                } else {
                    self.search_expression_in_node(child, pattern)
                }
            },
            LogicNode::Join { condition, children, .. } => {
                if let Some(cond) = condition {
                    if self.matches_expression_pattern(cond, pattern) {
                        return Some(cond.clone());
                    }
                }
                
                for child in children {
                    if let Some(expr) = self.search_expression_in_node(child, pattern) {
                        return Some(expr);
                    }
                }
                
                None
            },
            LogicNode::Aggregation { aggregates, child, .. } => {
                for (_, expr) in aggregates {
                    if self.matches_expression_pattern(expr, pattern) {
                        return Some(expr.clone());
                    }
                }
                self.search_expression_in_node(child, pattern)
            },
            LogicNode::Construction { bindings, child, .. } => {
                for (_, expr) in bindings {
                    if self.matches_expression_pattern(expr, pattern) {
                        return Some(expr.clone());
                    }
                }
                self.search_expression_in_node(child, pattern)
            },
            _ => None,
        }
    }
    
    /// 检查表达式是否匹配模式
    fn matches_expression_pattern(&self, expr: &Expr, pattern: &ExprPattern) -> bool {
        match (expr, pattern) {
            (Expr::Function { name, args }, ExprPattern::Function { name: pattern_name, args: pattern_args }) => {
                name == pattern_name && args.len() == pattern_args.len()
            },
            (Expr::Compare { op, left, right }, ExprPattern::Compare { op: pattern_op, left: pattern_left, right: pattern_right }) => {
                op == pattern_op && 
                self.matches_expression_pattern(left, pattern_left) && 
                self.matches_expression_pattern(right, pattern_right)
            },
            (Expr::Logical { op, args }, ExprPattern::Logical { op: pattern_op, args: pattern_args }) => {
                op == pattern_op && args.len() == pattern_args.len()
            },
            (Expr::Term(term), ExprPattern::Term(term_pattern)) => {
                self.matches_term_pattern(term, term_pattern)
            },
            _ => false,
        }
    }
    
    /// 检查项是否匹配模式
    fn matches_term_pattern(&self, term: &Term, pattern: &TermPattern) -> bool {
        match (term, pattern) {
            (Term::Variable(var), TermPattern::Variable(pattern_var)) => var == pattern_var,
            (Term::Constant(const_val), TermPattern::Constant(pattern_val)) => const_val == pattern_val,
            (Term::Variable(_), TermPattern::Wildcard) => true,
            (Term::Constant(_), TermPattern::Wildcard) => true,
            _ => false,
        }
    }
    
    /// 重写表达式
    fn rewrite_expression(&self, query: &LogicNode, matched_expr: &Expr, replacement: &RewriteReplacement) -> Option<LogicNode> {
        match replacement {
            RewriteReplacement::Expression(template) => {
                // 创建新的表达式
                let new_expr = self.create_expression_from_template(template);
                // 在查询中替换表达式
                self.replace_expression_in_query(query, matched_expr, &new_expr)
            },
            _ => None,
        }
    }
    
    /// 从模板创建表达式
    fn create_expression_from_template(&self, template: &ExprTemplate) -> Expr {
        match template {
            ExprTemplate::Constant(value) => Expr::Term(Term::Constant(value.clone())),
            ExprTemplate::Variable(var) => Expr::Term(Term::Variable(var.clone())),
            ExprTemplate::Function { name, args } => {
                let expr_args: Vec<Expr> = args.iter()
                    .map(|arg| self.create_expression_from_template(arg))
                    .collect();
                Expr::Function {
                    name: name.clone(),
                    args: expr_args,
                }
            },
        }
    }
    
    /// 在查询中替换表达式
    fn replace_expression_in_query(&self, query: &LogicNode, old_expr: &Expr, new_expr: &Expr) -> Option<LogicNode> {
        match query {
            LogicNode::Filter { expression, child } => {
                if self.expressions_equal(expression, old_expr) {
                    Some(LogicNode::Filter {
                        expression: new_expr.clone(),
                        child: child.clone(),
                    })
                } else {
                    if let Some(new_child) = self.replace_expression_in_query(child, old_expr, new_expr) {
                        Some(LogicNode::Filter {
                            expression: expression.clone(),
                            child: Box::new(new_child),
                        })
                    } else {
                        None
                    }
                }
            },
            _ => None,
        }
    }
    
    /// 检查表达式是否相等
    fn expressions_equal(&self, expr1: &Expr, expr2: &Expr) -> bool {
        match (expr1, expr2) {
            (Expr::Function { name: name1, args: args1 }, Expr::Function { name: name2, args: args2 }) => {
                name1 == name2 && args1.len() == args2.len() && 
                args1.iter().zip(args2.iter()).all(|(a, b)| self.expressions_equal(a, b))
            },
            (Expr::Term(term1), Expr::Term(term2)) => term1 == term2,
            _ => false,
        }
    }
    
    /// 应用到子节点
    fn apply_to_children(&self, rule: &RewriteRule, query: &LogicNode) -> Option<LogicNode> {
        match query {
            LogicNode::Join { children, condition, join_type } => {
                let mut new_children = Vec::new();
                let mut changed = false;
                
                for child in children {
                    if let Some(new_child) = self.apply_rule(rule, child) {
                        new_children.push(new_child);
                        changed = true;
                    } else {
                        new_children.push(child.clone());
                    }
                }
                
                if changed {
                    Some(LogicNode::Join {
                        children: new_children,
                        condition: condition.clone(),
                        join_type: join_type.clone(),
                    })
                } else {
                    None
                }
            },
            _ => None,
        }
    }
    
    /// 从模板创建节点
    fn create_node_from_template(&self, template: &NewNodeTemplate, original: &LogicNode) -> Option<LogicNode> {
        match template.node_type {
            NodeTypePattern::Filter => {
                // 创建新的过滤器节点
                Some(LogicNode::Filter {
                    expression: Expr::Term(Term::Constant("true".to_string())),
                    child: Box::new(original.clone()),
                })
            },
            _ => None,
        }
    }
}

impl Default for QueryRewriter {
    fn default() -> Self {
        Self::new()
    }
}

pub mod mapping_unfolder;
pub mod path_unfolder;
pub mod tbox_rewriter;

pub use mapping_unfolder::MappingUnfolder;
pub use tbox_rewriter::TBoxRewriter;
