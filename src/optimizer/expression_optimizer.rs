use crate::ir::expr::{Expr, Term, ComparisonOp, LogicalOp};
use std::collections::HashSet;

/// 表达式优化器
#[derive(Debug, Clone)]
pub struct ExpressionOptimizer {
    pub optimizations_applied: u64,
    pub simplifications_made: u64,
}

impl ExpressionOptimizer {
    pub fn new() -> Self {
        Self {
            optimizations_applied: 0,
            simplifications_made: 0,
        }
    }
    
    /// 优化表达式
    pub fn optimize(&mut self, expr: &Expr) -> Expr {
        let optimized = self.optimize_internal(expr);
        self.optimizations_applied += 1;
        optimized
    }
    
    /// 内部优化逻辑
    fn optimize_internal(&mut self, expr: &Expr) -> Expr {
        match expr {
            // 递归优化子表达式
            Expr::Function { name, args } => {
                let optimized_args: Vec<Expr> = args.iter()
                    .map(|arg| self.optimize_internal(arg))
                    .collect();
                
                let optimized_expr = Expr::Function {
                    name: name.clone(),
                    args: optimized_args,
                };
                
                // 应用函数特定的优化
                self.optimize_function(optimized_expr)
            },
            
            Expr::Logical { op, args } => {
                let optimized_args: Vec<Expr> = args.iter()
                    .map(|arg| self.optimize_internal(arg))
                    .collect();
                
                let optimized_expr = Expr::Logical {
                    op: *op,
                    args: optimized_args,
                };
                
                // 应用逻辑表达式优化
                self.optimize_logical(optimized_expr)
            },
            
            Expr::Compare { left, right, op } => {
                let optimized_left = self.optimize_internal(left);
                let optimized_right = self.optimize_internal(right);
                
                let optimized_expr = Expr::Compare {
                    left: Box::new(optimized_left),
                    right: Box::new(optimized_right),
                    op: *op,
                };
                
                // 应用比较表达式优化
                self.optimize_comparison(optimized_expr)
            },
            
            // 基本表达式不需要优化
            Expr::Term(term) => Expr::Term(term.clone()),
            
            // 算术表达式 - 递归优化左右操作数
            Expr::Arithmetic { left, right, op } => {
                let optimized_left = self.optimize_internal(left);
                let optimized_right = self.optimize_internal(right);
                
                // 尝试常量折叠
                if let (Expr::Term(Term::Constant(l)), Expr::Term(Term::Constant(r))) = 
                    (&optimized_left, &optimized_right) {
                    if let (Ok(lv), Ok(rv)) = (l.parse::<i64>(), r.parse::<i64>()) {
                        let result = match op {
                            crate::ir::expr::ArithmeticOp::Add => lv + rv,
                            crate::ir::expr::ArithmeticOp::Sub => lv - rv,
                            crate::ir::expr::ArithmeticOp::Mul => lv * rv,
                            crate::ir::expr::ArithmeticOp::Div => lv / rv,
                        };
                        self.simplifications_made += 1;
                        return Expr::Term(Term::Constant(result.to_string()));
                    }
                }
                
                Expr::Arithmetic {
                    left: Box::new(optimized_left),
                    right: Box::new(optimized_right),
                    op: *op,
                }
            },
            
            // EXISTS subqueries - no optimization for now
            Expr::Exists { patterns, correlated_vars, filters } => Expr::Exists {
                patterns: patterns.clone(),
                correlated_vars: correlated_vars.clone(),
                filters: filters.clone()
            },
            Expr::NotExists { patterns, correlated_vars, filters } => Expr::NotExists {
                patterns: patterns.clone(),
                correlated_vars: correlated_vars.clone(),
                filters: filters.clone()
            },
        }
    }
    
    /// 优化函数表达式
    fn optimize_function(&mut self, expr: Expr) -> Expr {
        if let Expr::Function { name, args } = expr {
            // 常量折叠
            if let Some(folded) = self.try_constant_folding(&name, &args) {
                self.simplifications_made += 1;
                return folded;
            }
            
            // 恒等函数优化
            if let Some(simplified) = self.try_identity_function(&name, &args) {
                self.simplifications_made += 1;
                return simplified;
            }
            
            // 冗余函数消除
            if let Some(reduced) = self.try_redundant_function(&name, &args) {
                self.simplifications_made += 1;
                return reduced;
            }
            
            Expr::Function { name, args }
        } else {
            expr
        }
    }
    
    /// 优化逻辑表达式
    fn optimize_logical(&mut self, expr: Expr) -> Expr {
        if let Expr::Logical { op, ref args } = expr {
            match op {
                LogicalOp::And => {
                    // AND 优化
                    let optimized_args = self.optimize_and_args(args);
                    if let Some(result) = self.try_and_simplification(&optimized_args) {
                        self.simplifications_made += 1;
                        return result;
                    }
                    Expr::Logical { op: LogicalOp::And, args: optimized_args }
                },
                LogicalOp::Or => {
                    // OR 优化
                    let optimized_args = self.optimize_or_args(args);
                    if let Some(result) = self.try_or_simplification(&optimized_args) {
                        self.simplifications_made += 1;
                        return result;
                    }
                    Expr::Logical { op: LogicalOp::Or, args: optimized_args }
                },
                LogicalOp::Not => {
                    // NOT 优化
                    if args.len() == 1 {
                        let optimized_arg = &args[0];
                        if let Some(negated) = self.try_negation_simplification(optimized_arg) {
                            self.simplifications_made += 1;
                            return negated;
                        }
                        Expr::Logical { op: LogicalOp::Not, args: vec![optimized_arg.clone()] }
                    } else {
                        expr
                    }
                },
            }
        } else {
            expr
        }
    }
    
    /// 优化比较表达式
    fn optimize_comparison(&mut self, expr: Expr) -> Expr {
        if let Expr::Compare { left, right, op } = expr {
            // 常量比较优化
            if let (Expr::Term(Term::Constant(left_val)), Expr::Term(Term::Constant(right_val))) = (&*left, &*right) {
                if let Some(result) = self.evaluate_constant_comparison(left_val, right_val, op) {
                    self.simplifications_made += 1;
                    return Expr::Term(Term::Constant(result));
                }
            }
            
            // 冗余比较消除
            if let Some(simplified) = self.try_redundant_comparison(&*left, &*right, op) {
                self.simplifications_made += 1;
                return simplified;
            }
            
            // 比较顺序标准化
            if let Some(normalized) = self.normalize_comparison(&*left, &*right, op) {
                return normalized;
            }
            
            Expr::Compare { left, right, op }
        } else {
            expr
        }
    }
    
    /// 尝试常量折叠
    fn try_constant_folding(&self, name: &str, args: &[Expr]) -> Option<Expr> {
        // 只处理所有参数都是常量的情况
        let constants: Vec<&str> = args.iter().filter_map(|arg| {
            if let Expr::Term(Term::Constant(c)) = arg {
                Some(c.as_str())
            } else {
                None
            }
        }).collect();
        
        if constants.len() != args.len() {
            return None;
        }
        
        match name {
            "ADD" | "+" => {
                if constants.len() == 2 {
                    // 简化的加法实现
                    if let (Ok(a), Ok(b)) = (constants[0].parse::<i64>(), constants[1].parse::<i64>()) {
                        return Some(Expr::Term(Term::Constant((a + b).to_string())));
                    }
                }
            },
            "MULTIPLY" | "*" => {
                if constants.len() == 2 {
                    if let (Ok(a), Ok(b)) = (constants[0].parse::<i64>(), constants[1].parse::<i64>()) {
                        return Some(Expr::Term(Term::Constant((a * b).to_string())));
                    }
                }
            },
            "SUBTRACT" | "-" => {
                if constants.len() == 2 {
                    if let (Ok(a), Ok(b)) = (constants[0].parse::<i64>(), constants[1].parse::<i64>()) {
                        return Some(Expr::Term(Term::Constant((a - b).to_string())));
                    }
                }
            },
            _ => {}
        }
        
        None
    }
    
    /// 尝试恒等函数优化
    fn try_identity_function(&self, name: &str, args: &[Expr]) -> Option<Expr> {
        match name {
            "IDENTITY" | "ID" => {
                if args.len() == 1 {
                    return Some(args[0].clone());
                }
            },
            _ => {}
        }
        None
    }
    
    /// 尝试冗余函数消除
    fn try_redundant_function(&self, name: &str, args: &[Expr]) -> Option<Expr> {
        match name {
            "UPPER" => {
                if args.len() == 1 {
                    if let Expr::Term(Term::Constant(s)) = &args[0] {
                        return Some(Expr::Term(Term::Constant(s.to_uppercase())));
                    }
                }
            },
            "LOWER" => {
                if args.len() == 1 {
                    if let Expr::Term(Term::Constant(s)) = &args[0] {
                        return Some(Expr::Term(Term::Constant(s.to_lowercase())));
                    }
                }
            },
            _ => {}
        }
        None
    }
    
    /// 优化 AND 参数
    fn optimize_and_args(&self, args: &[Expr]) -> Vec<Expr> {
        let mut result = Vec::new();
        let mut seen = HashSet::new();
        
        for arg in args {
            // 移除重复的 AND 条件
            let arg_str = format!("{:?}", arg);
            if !seen.contains(&arg_str) {
                seen.insert(arg_str);
                result.push(arg.clone());
            }
        }
        
        result
    }
    
    /// 优化 OR 参数
    fn optimize_or_args(&self, args: &[Expr]) -> Vec<Expr> {
        let mut result = Vec::new();
        let mut seen = HashSet::new();
        
        for arg in args {
            // 移除重复的 OR 条件
            let arg_str = format!("{:?}", arg);
            if !seen.contains(&arg_str) {
                seen.insert(arg_str);
                result.push(arg.clone());
            }
        }
        
        result
    }
    
    /// 尝试 AND 简化
    fn try_and_simplification(&self, args: &[Expr]) -> Option<Expr> {
        // 如果有 FALSE，整个 AND 就是 FALSE
        for arg in args {
            if let Expr::Term(Term::Constant(c)) = arg {
                if c == "false" || c == "0" {
                    return Some(Expr::Term(Term::Constant("false".to_string())));
                }
            }
        }
        
        // 如果所有都是 TRUE，返回 TRUE
        if args.iter().all(|arg| {
            if let Expr::Term(Term::Constant(c)) = arg {
                c == "true" || c == "1"
            } else {
                false
            }
        }) {
            return Some(Expr::Term(Term::Constant("true".to_string())));
        }
        
        // 如果只有一个参数，直接返回
        if args.len() == 1 {
            return Some(args[0].clone());
        }
        
        None
    }
    
    /// 尝试 OR 简化
    fn try_or_simplification(&self, args: &[Expr]) -> Option<Expr> {
        // 如果有 TRUE，整个 OR 就是 TRUE
        for arg in args {
            if let Expr::Term(Term::Constant(c)) = arg {
                if c == "true" || c == "1" {
                    return Some(Expr::Term(Term::Constant("true".to_string())));
                }
            }
        }
        
        // 如果所有都是 FALSE，返回 FALSE
        if args.iter().all(|arg| {
            if let Expr::Term(Term::Constant(c)) = arg {
                c == "false" || c == "0"
            } else {
                false
            }
        }) {
            return Some(Expr::Term(Term::Constant("false".to_string())));
        }
        
        // 如果只有一个参数，直接返回
        if args.len() == 1 {
            return Some(args[0].clone());
        }
        
        None
    }
    
    /// 尝试否定简化
    fn try_negation_simplification(&self, arg: &Expr) -> Option<Expr> {
        match arg {
            // 双重否定
            Expr::Logical { op: LogicalOp::Not, args } => {
                if args.len() == 1 {
                    return Some(args[0].clone());
                }
            },
            // NOT TRUE = FALSE
            Expr::Term(Term::Constant(c)) if c == "true" || c == "1" => {
                return Some(Expr::Term(Term::Constant("false".to_string())));
            },
            // NOT FALSE = TRUE
            Expr::Term(Term::Constant(c)) if c == "false" || c == "0" => {
                return Some(Expr::Term(Term::Constant("true".to_string())));
            },
            _ => {}
        }
        None
    }
    
    /// 评估常量比较
    fn evaluate_constant_comparison(&self, left: &str, right: &str, op: ComparisonOp) -> Option<String> {
        // 简化的字符串比较
        let result = match op {
            ComparisonOp::Eq => left == right,
            ComparisonOp::Neq => left != right,
            ComparisonOp::Lt => left < right,
            ComparisonOp::Lte => left <= right,
            ComparisonOp::Gt => left > right,
            ComparisonOp::Gte => left >= right,
            ComparisonOp::In => right
                .split(',')
                .map(|v| v.trim())
                .any(|candidate| candidate == left),
            ComparisonOp::NotIn => right
                .split(',')
                .map(|v| v.trim())
                .all(|candidate| candidate != left),
        };
        
        Some(if result { "true" } else { "false" }.to_string())
    }
    
    /// 尝试冗余比较消除
    fn try_redundant_comparison(&self, left: &Expr, right: &Expr, op: ComparisonOp) -> Option<Expr> {
        // 检查是否是相同的表达式比较
        if left == right {
            match op {
                ComparisonOp::Eq => return Some(Expr::Term(Term::Constant("true".to_string()))),
                ComparisonOp::Neq => return Some(Expr::Term(Term::Constant("false".to_string()))),
                _ => {}
            }
        }
        
        None
    }
    
    /// 标准化比较顺序
    fn normalize_comparison(&self, left: &Expr, right: &Expr, op: ComparisonOp) -> Option<Expr> {
        // 对于某些操作符，确保常量在右边
        if let Expr::Term(Term::Constant(_)) = left {
            match op {
                ComparisonOp::Eq => {
                    return Some(Expr::Compare {
                        left: Box::new(right.clone()),
                        right: Box::new(left.clone()),
                        op: ComparisonOp::Eq,
                    });
                },
                ComparisonOp::Neq => {
                    return Some(Expr::Compare {
                        left: Box::new(right.clone()),
                        right: Box::new(left.clone()),
                        op: ComparisonOp::Neq,
                    });
                },
                _ => {}
            }
        }
        
        None
    }
    
    /// 获取优化统计信息
    pub fn get_stats(&self) -> OptimizationStats {
        OptimizationStats {
            optimizations_applied: self.optimizations_applied,
            simplifications_made: self.simplifications_made,
        }
    }
    
    /// 重置统计信息
    pub fn reset_stats(&mut self) {
        self.optimizations_applied = 0;
        self.simplifications_made = 0;
    }
}

/// 优化统计信息
#[derive(Debug, Clone)]
pub struct OptimizationStats {
    pub optimizations_applied: u64,
    pub simplifications_made: u64,
}

impl Default for ExpressionOptimizer {
    fn default() -> Self {
        Self::new()
    }
}

/// 表达式复杂度分析器
#[derive(Debug, Clone)]
pub struct ExpressionComplexityAnalyzer;

impl ExpressionComplexityAnalyzer {
    pub fn new() -> Self {
        Self
    }
    
    /// 计算表达式复杂度
    pub fn analyze_complexity(&self, expr: &Expr) -> ComplexityMetrics {
        let mut analyzer = ComplexityCalculator::new();
        analyzer.calculate(expr)
    }
    
    /// 检查表达式是否过于复杂
    pub fn is_too_complex(&self, expr: &Expr, threshold: u32) -> bool {
        let metrics = self.analyze_complexity(expr);
        metrics.total_complexity > threshold
    }
}

/// 复杂度计算器
#[derive(Debug)]
struct ComplexityCalculator {
    depth: u32,
    function_count: u32,
    logical_count: u32,
    comparison_count: u32,
    nesting_depth: u32,
    current_depth: u32,
}

impl ComplexityCalculator {
    fn new() -> Self {
        Self {
            depth: 0,
            function_count: 0,
            logical_count: 0,
            comparison_count: 0,
            nesting_depth: 0,
            current_depth: 0,
        }
    }
    
    fn calculate(&mut self, expr: &Expr) -> ComplexityMetrics {
        self.current_depth += 1;
        self.nesting_depth = self.nesting_depth.max(self.current_depth);
        
        match expr {
            Expr::Function { args, .. } => {
                self.function_count += 1;
                for arg in args {
                    self.calculate(arg);
                }
            },
            Expr::Logical { args, .. } => {
                self.logical_count += 1;
                for arg in args {
                    self.calculate(arg);
                }
            },
            Expr::Compare { left, right, .. } => {
                self.comparison_count += 1;
                self.calculate(left);
                self.calculate(right);
            },
            Expr::Term(_) => {
                self.depth += 1;
            },
            Expr::Exists { .. } | Expr::NotExists { .. } | Expr::Arithmetic { .. } => {
                // EXISTS subqueries count as complex expressions
                // Arithmetic expressions also counted as complex
                self.function_count += 1;
            },
        }
        
        self.current_depth -= 1;
        
        let total_complexity = self.function_count * 3 + 
                              self.logical_count * 2 + 
                              self.comparison_count + 
                              self.nesting_depth;
        
        ComplexityMetrics {
            total_complexity,
            function_count: self.function_count,
            logical_count: self.logical_count,
            comparison_count: self.comparison_count,
            nesting_depth: self.nesting_depth,
        }
    }
}

/// 复杂度指标
#[derive(Debug, Clone)]
pub struct ComplexityMetrics {
    pub total_complexity: u32,
    pub function_count: u32,
    pub logical_count: u32,
    pub comparison_count: u32,
    pub nesting_depth: u32,
}

impl Default for ExpressionComplexityAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}
