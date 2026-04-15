use std::collections::HashMap;
use std::sync::Arc;
use crate::ir::expr::{Term, Expr};
use crate::ir::node::{LogicNode, JoinType};
use crate::optimizer::{OptimizerPass, OptimizerContext};

/// 映射展开 Pass
/// 
/// 将 IntensionalData 节点（逻辑谓词）展开为 ExtensionalData 节点（物理表引用）。
/// 这是查询优化的关键步骤，将虚拟 RDF 映射转换为可执行的 SQL 表引用。
pub struct UnfoldingPass;

impl UnfoldingPass {
    /// 创建新的 UnfoldingPass 实例
    pub fn new() -> Self {
        Self
    }

    /// 从逻辑节点收集变量到列的映射
    ///
    /// # Arguments
    /// * `node` - 当前逻辑节点
    /// * `vars` - 变量到列的映射 HashMap（输出参数）
    /// * `pk_vars` - 可选：只收集这些变量（用于 JOIN 条件生成，避免重复收集 object 变量）
    fn collect_vars_filtered(&self, node: &LogicNode, vars: &mut HashMap<String, Vec<String>>, pk_vars: &Option<Vec<String>>) {
        match node {
            LogicNode::ExtensionalData { column_mapping, metadata, .. } => {
                // 获取表的主键列
                let pk_cols: Vec<String> = metadata.primary_keys.clone();
                
                for (var, col) in column_mapping {
                    // 如果指定了 pk_vars，只收集这些变量
                    if let Some(ref allowed) = pk_vars {
                        if !allowed.contains(var) {
                            continue;
                        }
                    }
                    
                    // Collect all column mappings for join conditions
                    vars.entry(var.clone()).or_default().push(col.clone());
                }
            }
            LogicNode::Join { children, .. } => {
                for child in children { self.collect_vars_filtered(child, vars, pk_vars); }
            }
            LogicNode::Construction { child, .. } => self.collect_vars_filtered(child, vars, pk_vars),
            _ => {}
        }
    }
    
    /// 从逻辑节点收集变量到列的映射（收集所有）
    fn collect_vars(&self, node: &LogicNode, vars: &mut HashMap<String, Vec<String>>) {
        self.collect_vars_filtered(node, vars, &None);
    }
}

impl OptimizerPass for UnfoldingPass {
    fn name(&self) -> &str {
        "UnfoldingPass"
    }

    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            LogicNode::Construction { child, .. } => {
                eprintln!("[DEBUG Unfolding] Visiting Construction");
                self.apply(child, ctx);
            }
            LogicNode::Join { children, condition, join_type } => {
                eprintln!("[DEBUG Unfolding] Visiting Join with {} children", children.len());
                for child in children.iter_mut() {
                    self.apply(child, ctx);
                }
                
                // Essential: Generate Join Conditions (Equalities for shared variables)
                if *join_type == JoinType::Inner {
                    let mut var_to_cols: HashMap<String, Vec<(usize, String)>> = HashMap::new();
                    for (i, child) in children.iter().enumerate() {
                        let mut child_vars = HashMap::new();
                        self.collect_vars(child, &mut child_vars);
                        eprintln!("[DEBUG Unfolding] Child {} vars: {:?}", i, child_vars);
                        for (var, cols) in child_vars {
                            for col in cols {
                                var_to_cols.entry(var.clone()).or_insert_with(Vec::new).push((i, col));
                            }
                        }
                    }
                    eprintln!("[DEBUG Unfolding] var_to_cols: {:?}", var_to_cols);

                    let mut eq_conds = Vec::new();
                    for (var, cols) in &var_to_cols {
                        if cols.len() > 1 {
                            for j in 1..cols.len() {
                                let (idx0, col0) = &cols[0];
                                let (idxj, colj) = &cols[j];
                                eprintln!("[DEBUG Unfolding] Creating JOIN condition: t{}.{} = t{}.{} for var {}", idx0, col0, idxj, colj, var);
                                eq_conds.push(Expr::Function {
                                    name: "Eq".to_string(),
                                    args: vec![
                                        Expr::Term(Term::Variable(format!("t{}.{}", idx0, col0))), 
                                        Expr::Term(Term::Variable(format!("t{}.{}", idxj, colj)))
                                    ],
                                });
                            }
                        }
                    }

                    if !eq_conds.is_empty() {
                        let mut combined = eq_conds.pop().expect("should have condition");
                        while let Some(next) = eq_conds.pop() {
                            combined = Expr::Function {
                                name: "And".to_string(),
                                args: vec![combined, next],
                            };
                        }
                        *condition = Some(combined);
                    }
                }
            }
            LogicNode::Filter { child, .. } => {
                eprintln!("[DEBUG Unfolding] Visiting Filter");
                self.apply(child, ctx);
            }
            LogicNode::Limit { child, .. } => {
                eprintln!("[DEBUG Unfolding] Visiting Limit");
                self.apply(child, ctx);
            }
            LogicNode::Aggregation { child, .. } => {
                eprintln!("[DEBUG Unfolding] Visiting Aggregation");
                self.apply(child, ctx);
            }
            LogicNode::Union(children) => {
                eprintln!("[DEBUG Unfolding] Visiting Union with {} children", children.len());
                for child in children { self.apply(child, ctx); }
            }
            LogicNode::IntensionalData { predicate, args } => {
                eprintln!("[DEBUG Unfolding] Processing IntensionalData: predicate={}, args={:?}", predicate, args);
                if let Some(rules) = ctx.mappings.mappings.get(predicate) {
                    // 使用第一个规则
                    let rule = &rules[0];
                    eprintln!("[DEBUG Unfolding] Found rule: table={}, position_to_column={:?}", rule.table_name, rule.position_to_column);
                    let mut column_mapping = HashMap::new();
                    
                    // 从 subject_template 提取 subject 列映射（位置 0）
                    if let Some(template) = &rule.subject_template {
                        if let Some(start) = template.find('{') {
                            if let Some(end) = template.find('}') {
                                let col = &template[start+1..end];
                                // args[0] 是 subject 变量
                                if let Some(Term::Variable(var)) = args.get(0) {
                                    column_mapping.insert(var.clone(), col.to_string());
                                    eprintln!("[DEBUG Unfolding] Subject mapping: {} -> {}", var, col);
                                }
                            }
                        }
                    }

                    // 从 position_to_column 提取其他位置映射
                    for (pos, term) in args.iter().enumerate().skip(1) { // skip(1) 因为位置 0 已处理
                        if let Term::Variable(var) = term {
                            if let Some(col) = rule.position_to_column.get(&pos) {
                                column_mapping.insert(var.clone(), col.clone());
                                eprintln!("[DEBUG Unfolding] Position {} mapping: {} -> {}", pos, var, col);
                            } else {
                                eprintln!("[DEBUG Unfolding] No mapping for position {}, var={}", pos, var);
                            }
                        }
                    }

                    if let Some(metadata) = ctx.metadata.get(&rule.table_name) {
                        eprintln!("[DEBUG Unfolding] Creating ExtensionalData: table={}, column_mapping={:?}", rule.table_name, column_mapping);
                        *node = LogicNode::ExtensionalData {
                            table_name: rule.table_name.clone(),
                            column_mapping,
                            metadata: Arc::clone(metadata),
                        };
                    } else {
                        eprintln!("[DEBUG Unfolding] No metadata found for table: {}", rule.table_name);
                    }
                } else {
                    eprintln!("[DEBUG Unfolding] No rule found for predicate: {}", predicate);
                }
            }
            LogicNode::ExtensionalData { table_name, .. } => {
                eprintln!("[DEBUG Unfolding] Visiting ExtensionalData: {}", table_name);
            }
            LogicNode::Path { subject, path, object } => {
                eprintln!("[DEBUG Unfolding] Processing Path node");
                match crate::rewriter::path_unfolder::unfold_property_path(
                    subject, path, object, &ctx.mappings, &ctx.metadata
                ) {
                    Ok(unfolded) => {
                        *node = unfolded;
                        // Process the unfolded result (may contain more IntensionalData or Paths)
                        self.apply(node, ctx);
                    }
                    Err(e) => {
                        eprintln!("[ERROR Unfolding] Failed to unfold property path: {}", e);
                    }
                }
            }
            _ => {
                eprintln!("[DEBUG Unfolding] Visiting other node type");
            }
        }
    }
}
