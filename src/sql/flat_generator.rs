//! 扁平化 SQL 生成器
//! 
//! 这是 RS Ontop Core V2.0 的核心改造，消除嵌套子查询
//! 参考 Ontop 的 "Sub-query Elimination" 技术

use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use crate::ir::node::{LogicNode, JoinType};
use crate::ir::expr::{Expr, Term, ComparisonOp, LogicalOp};
use crate::mapping::MappingStore;

/// 扁平化 SQL 生成器
/// 
/// 核心思想：将整个查询树的所有组件收集到上下文中，
/// 最后一次性拼装为扁平的 SQL，消除嵌套子查询
#[derive(Debug)]
/// 扁平 SQL 生成器
/// 
/// 将 IR（中间表示）逻辑计划转换为可执行的 SQL 查询。
/// 支持多种 SQL 特性：JOIN、FILTER、聚合、UNION、LIMIT/OFFSET 等。
/// 
/// # Architecture
/// - 使用访问者模式遍历 IR 树
/// - 通过 GeneratorContext 收集 SQL 组件
/// - 最后通过 assemble_sql 拼装完整 SQL
pub struct FlatSQLGenerator {
    /// 生成上下文
    ctx: GeneratorContext,
    /// 别名管理器
    alias_manager: AliasManager,
    /// 映射存储（可选，用于 EXISTS 子查询等需要映射信息的场景）
    mappings: Option<Arc<MappingStore>>,
}

/// 生成上下文，收集整个查询树的所有组件
#[derive(Debug, Default)]
struct GeneratorContext {
    /// SELECT 子句中的项目
    select_items: Vec<SelectItem>,
    /// FROM 子句中的表
    from_tables: Vec<FromTable>,
    /// WHERE 子句中的条件
    where_conditions: Vec<Condition>,
    /// GROUP BY 子句
    group_by: Vec<String>,
    /// HAVING 子句
    having_conditions: Vec<Condition>,
    /// ORDER BY 子句
    order_by: Vec<OrderByItem>,
    /// LIMIT 子句
    limit: Option<usize>,
    /// OFFSET 子句
    offset: Option<usize>,
    /// 根节点是 UNION 时，直接保存拼接后的 SQL
    union_sql: Option<String>,
    /// 记录所有扫描过的表产生的变量（用于 HAVING 引用那些不在最终 SELECT 中的列）
    all_available_items: Vec<SelectItem>,
}

/// SELECT 项目
#[derive(Debug, Clone)]
struct SelectItem {
    /// 表达式
    expression: String,
    /// 别名
    alias: String,
    /// 是否是聚合函数
    #[allow(dead_code)]
    is_aggregate: bool,
}

/// FROM 表项
#[derive(Debug, Clone)]
struct FromTable {
    /// 表名
    table_name: String,
    /// 别名
    alias: String,
    /// 连接类型
    join_type: Option<JoinType>,
    /// 连接条件
    join_condition: Option<String>,
    /// 是否为子查询
    is_subquery: bool,
    /// 子查询SQL（当is_subquery为true时使用）
    subquery_sql: Option<String>,
}

/// WHERE 条件
#[derive(Debug, Clone)]
struct Condition {
    /// SQL 表达式
    expression: String,
    /// 条件类型
    #[allow(dead_code)]
    condition_type: ConditionType,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
enum ConditionType {
    /// 普通条件
    Normal,
    /// JOIN 条件
    Join,
    /// 过滤条件
    Filter,
}

/// ORDER BY 项目
#[derive(Debug, Clone)]
struct OrderByItem {
    /// 表达式
    expression: String,
    /// 排序方向
    direction: SortDirection,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
enum SortDirection {
    Asc,
    Desc,
}

/// 将 camelCase 转换为 snake_case
fn to_snake_case(s: &str) -> String {
    let mut result = String::new();
    for (i, c) in s.chars().enumerate() {
        if c.is_uppercase() {
            if i > 0 {
                result.push('_');
            }
            result.push(c.to_lowercase().next().unwrap_or(c));
        } else {
            result.push(c);
        }
    }
    result
}

/// 别名管理器 - 解决你文档末尾提到的别名碰撞问题
#[derive(Debug)]
struct AliasManager {
    /// 已使用的别名
    used_aliases: HashSet<String>,
    /// 表到别名的映射
    table_alias_map: HashMap<String, String>,
    /// 变量到别名的映射
    var_alias_map: HashMap<String, String>,
    /// 别名计数器
    alias_counter: usize,
}

impl AliasManager {
    fn new() -> Self {
        Self {
            used_aliases: HashSet::new(),
            table_alias_map: HashMap::new(),
            var_alias_map: HashMap::new(),
            alias_counter: 0,
        }
    }
    
    /// 为表分配别名，避免碰撞
    fn allocate_table_alias(&mut self, table_name: &str) -> String {
        // 生成基础别名
        let base_alias = self.generate_base_alias(table_name);
        let mut alias = base_alias.clone();
        
        // 避免碰撞
        let mut counter = 1;
        while self.used_aliases.contains(&alias) {
            alias = format!("{}_{}", base_alias, counter);
            counter += 1;
        }
        
        self.used_aliases.insert(alias.clone());
        self.table_alias_map.insert(table_name.to_string(), alias.clone());
        
        alias
    }
    
    /// 为变量分配别名
    fn allocate_var_alias(&mut self, var_name: &str) -> String {
        if let Some(existing) = self.var_alias_map.get(var_name) {
            return existing.clone();
        }
        
        // [Fix] 转换为小写蛇形命名以匹配数据库列名
        let base_name = var_name.trim_start_matches('?');
        let snake_name = to_snake_case(base_name);
        let alias = format!("col_{}", snake_name);
        self.var_alias_map.insert(var_name.to_string(), alias.clone());
        alias
    }
    
    /// 从表名生成基础别名
    fn generate_base_alias(&self, table_name: &str) -> String {
        // 从表名提取有意义的前缀
        if let Some(caps) = regex::Regex::new(r"([a-z]+)").ok().and_then(|re| re.captures(table_name)) {
            let prefix = caps[1].chars().take(3).collect::<String>();
            if !prefix.is_empty() {
                prefix
            } else {
                format!("t{}", self.alias_counter)
            }
        } else {
            format!("t{}", self.alias_counter)
        }
    }
    
    /// 获取表的别名
    #[allow(dead_code)]
    fn get_table_alias(&self, table_name: &str) -> Option<&String> {
        self.table_alias_map.get(table_name)
    }
    
    /// 获取变量的别名
    fn get_var_alias(&self, var_name: &str) -> Option<&String> {
        self.var_alias_map.get(var_name)
    }
    
    /// 生成下一个唯一ID
    fn next_id(&mut self) -> usize {
        self.alias_counter += 1;
        self.alias_counter
    }
    
    /// 重置状态（用于新的查询生成）
    fn reset(&mut self) {
        self.used_aliases.clear();
        self.table_alias_map.clear();
        self.var_alias_map.clear();
        self.alias_counter = 0;
    }
}

impl FlatSQLGenerator {
    pub fn new_with_mappings(mappings: Arc<MappingStore>) -> Self {
        Self {
            ctx: GeneratorContext::default(),
            alias_manager: AliasManager::new(),
            mappings: Some(mappings),
        }
    }

    /// 创建新的 FlatSQLGenerator 实例
    ///
    /// # Returns
    /// 初始化好的生成器，包含新的 GeneratorContext 和 AliasManager
    pub fn new() -> Self {
        Self {
            ctx: GeneratorContext::default(),
            alias_manager: AliasManager::new(),
            mappings: None,
        }
    }

    fn child_generator(&self) -> Self {
        if let Some(mappings) = &self.mappings {
            FlatSQLGenerator::new_with_mappings(Arc::clone(mappings))
        } else {
            FlatSQLGenerator::new()
        }
    }
    
    /// 生成扁平化 SQL
    /// 生成扁平化 SQL 字符串
    ///
    /// # Arguments
    /// * `root_node` - IR 逻辑树的根节点
    ///
    /// # Returns
    /// 返回生成的 SQL 字符串
    ///
    /// # Errors
    /// - 当 IR 包含未展开的 IntensionalData 时返回 UnexpandedPredicate
    /// - 当 JOIN 条件无效时返回 InvalidJoin
    pub fn generate(&mut self, root_node: &LogicNode) -> Result<String, GenerationError> {
        // 重置上下文
        self.reset_context();

        // UNION 根节点单独处理，避免与扁平化上下文混用
        if let LogicNode::Union(children) = root_node {
            self.ctx.union_sql = Some(self.generate_union_sql(children)?);
            return self.assemble_sql();
        }
        
        // 遍历 IR 树，收集所有组件
        self.traverse_node(root_node)?;
        
        // 拼装扁平 SQL
        self.assemble_sql()
    }
    
    /// 重置生成上下文
    /// 重置生成上下文
    fn reset_context(&mut self) {
        self.ctx = GeneratorContext::default();
        self.alias_manager.reset();
    }
    
    /// 遍历 IR 树，收集组件到上下文
    ///
    /// # Arguments
    /// * `node` - 当前处理的逻辑节点
    ///
    /// # Errors
    /// 根据节点类型可能返回各种 GenerationError
    fn traverse_node(&mut self, node: &LogicNode) -> Result<(), GenerationError> {
        match node {
            LogicNode::ExtensionalData { 
                table_name, 
                column_mapping, 
                metadata: _ 
            } => {
                self.handle_extensional_data(table_name, column_mapping)?;
            },
            
            LogicNode::Join { 
                children, 
                condition, 
                join_type 
            } => {
                self.handle_join(children, condition, *join_type)?;
            },
            
            LogicNode::Filter { expression, child } => {
                self.handle_filter(expression, child)?;
            },
            
            LogicNode::Construction { 
                projected_vars, 
                bindings, 
                child 
            } => {
                self.handle_construction(projected_vars, bindings, child)?;
            },
            
            LogicNode::Union(children) => {
                self.handle_union(children)?;
            },
            
            LogicNode::Aggregation { 
                group_by, 
                aggregates, 
                child,
                ..
            } => {
                self.handle_aggregation(group_by, aggregates, child)?;
            },
            
            LogicNode::Limit { limit, offset, order_by, child } => {
                self.handle_limit(*limit, *offset, order_by, child)?;
            },
            
            LogicNode::IntensionalData { .. } => {
                // IntensionalData 需要先展开为 ExtensionalData
                return Err(GenerationError::UnexpandedPredicate(
                    "IntensionalData must be expanded before SQL generation".to_string()
                ));
            },
            
            LogicNode::Values { variables, rows } => {
                self.handle_values(variables, rows)?;
            },
            LogicNode::Path { subject, path, object } => {
                // [S4-P1-1] 使用属性路径 SQL 生成器
                let path_sql = crate::sql::path_sql_generator::PropertyPathSQLGenerator::generate(
                    subject, path, object, &self.alias_manager.allocate_table_alias("path")
                )?;
                
                // 将路径查询作为子查询加入
                let path_alias = self.alias_manager.allocate_table_alias("path_result");
                self.ctx.from_tables.push(FromTable {
                    table_name: format!("({})", path_sql),
                    alias: path_alias.clone(),
                    join_type: None,
                    join_condition: None,
                    is_subquery: true,
                    subquery_sql: Some(path_sql.clone()),
                });
                
                // [Fix] 注册路径节点的变量到select_items，使后续节点可以引用
                if let Term::Variable(var_name) = subject {
                    let col_alias = format!("{}", var_name.trim_start_matches('?'));
                    let col_expr = format!("{}.{}", path_alias, "start_node");
                    if !self.ctx.select_items.iter().any(|i| i.alias == *var_name || i.alias == col_alias) {
                        self.ctx.select_items.push(SelectItem {
                            expression: col_expr,
                            alias: col_alias.clone(),
                            is_aggregate: false,
                        });
                    }
                    // 同时注册到all_available_items
                    if !self.ctx.all_available_items.iter().any(|i| i.alias == *var_name || i.alias == col_alias) {
                        self.ctx.all_available_items.push(SelectItem {
                            expression: format!("{}.{}", path_alias, "start_node"),
                            alias: var_name.clone(),
                            is_aggregate: false,
                        });
                    }
                }
                
                if let Term::Variable(var_name) = object {
                    let col_alias = format!("{}", var_name.trim_start_matches('?'));
                    let col_expr = format!("{}.{}", path_alias, "end_node");
                    if !self.ctx.select_items.iter().any(|i| i.alias == *var_name || i.alias == col_alias) {
                        self.ctx.select_items.push(SelectItem {
                            expression: col_expr,
                            alias: col_alias.clone(),
                            is_aggregate: false,
                        });
                    }
                    // 同时注册到all_available_items
                    if !self.ctx.all_available_items.iter().any(|i| i.alias == *var_name || i.alias == col_alias) {
                        self.ctx.all_available_items.push(SelectItem {
                            expression: format!("{}.{}", path_alias, "end_node"),
                            alias: var_name.clone(),
                            is_aggregate: false,
                        });
                    }
                }
            }
            LogicNode::Graph { graph_name: _, child, .. } => {
                // [S5-P0-2] Named Graph SQL placeholder
                self.traverse_node(child)?;
            }
            LogicNode::GraphUnion { children, .. } => {
                // [S5-P0-2] GraphUnion SQL placeholder - process as UNION
                self.handle_union(children)?;
            }
            LogicNode::Service { endpoint, .. } => {
                // [S6-P1-2] SERVICE nodes are materialized before SQL generation
                return Err(GenerationError::Other(
                    format!("SERVICE node for {} should be materialized before SQL generation", endpoint)
                ));
            }
            LogicNode::SubQuery { inner, correlated_vars } => {
                self.handle_subquery(inner, correlated_vars)?;
            }
            LogicNode::CorrelatedJoin { outer, inner, condition } => {
                self.traverse_node(outer)?;
                self.handle_subquery(inner, &[])?;
                let cond_sql = self.translate_expression(condition)?;
                self.ctx.where_conditions.push(Condition {
                    expression: cond_sql,
                    condition_type: ConditionType::Filter,
                });
            }
            LogicNode::RecursivePath { base_path, recursive_path, subject, object, min_depth, max_depth } => {
                // [S9-P2] Generate recursive CTE for path modifiers (*, +)
                self.generate_recursive_path_cte(
                    base_path,
                    recursive_path,
                    subject,
                    object,
                    *min_depth,
                    *max_depth,
                )?;
            }
        }
        
        Ok(())
    }
    
    /// 处理表扫描节点
    fn handle_extensional_data(
        &mut self,
        table_name: &str,
        column_mapping: &HashMap<String, String>,
    ) -> Result<(), GenerationError> {
        // 分配表别名
        let table_alias = self.alias_manager.allocate_table_alias(table_name);
        
        // 添加到 FROM 子句
        self.ctx.from_tables.push(FromTable {
            table_name: table_name.to_string(),
            alias: table_alias.clone(),
            join_type: None,
            join_condition: None,
            is_subquery: false,
            subquery_sql: None,
        });
        
        // 处理列映射
        for (var_name, column_name) in column_mapping {
            let var_alias = self.alias_manager.allocate_var_alias(var_name);
            
            // 添加到 SELECT 子句
            let item = SelectItem {
                expression: format!("{}.{}", table_alias, column_name),
                alias: var_alias.clone(),
                is_aggregate: false,
            };
            self.ctx.select_items.push(item.clone());
            self.ctx.all_available_items.push(item);
        }
        
        Ok(())
    }
    
    /// 处理 JOIN 节点
    fn handle_join(
        &mut self,
        children: &[LogicNode],
        condition: &Option<Expr>,
        join_type: JoinType,
    ) -> Result<(), GenerationError> {
        if children.len() < 2 {
            return Err(GenerationError::InvalidJoin(
                "Join must have at least 2 children".to_string()
            ));
        }

        let mut all_child_items = Vec::new();

        for child in children {
            let start = self.ctx.select_items.len();
            self.traverse_node(child)?;
            let end = self.ctx.select_items.len();
            let items = self.ctx.select_items[start..end].to_vec();
            all_child_items.push(items);
        }

        let mut infer_conditions = |generator: &mut Self| {
            let mut seen_conditions = HashSet::new();
            for i in 0..all_child_items.len() {
                for j in (i + 1)..all_child_items.len() {
                    for item_i in &all_child_items[i] {
                        for item_j in &all_child_items[j] {
                            if item_i.alias == item_j.alias && item_i.expression != item_j.expression {
                                let cond = format!("{} = {}", item_i.expression, item_j.expression);
                                if seen_conditions.insert(cond.clone()) {
                                    if let Err(_) = generator.add_join_condition(&cond, JoinType::Inner) {
                                        generator.ctx.where_conditions.push(Condition {
                                            expression: cond,
                                            condition_type: ConditionType::Join,
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
            }

            let mut alias_exprs: HashMap<String, Vec<String>> = HashMap::new();
            for item in &generator.ctx.all_available_items {
                let entry = alias_exprs.entry(item.alias.clone()).or_default();
                if !entry.contains(&item.expression) {
                    entry.push(item.expression.clone());
                }
            }
            for exprs in alias_exprs.values() {
                if exprs.len() > 1 {
                    for e in exprs.iter().skip(1) {
                        let cond = format!("{} = {}", exprs[0], e);
                        if seen_conditions.insert(cond.clone()) {
                            generator.ctx.where_conditions.push(Condition {
                                expression: cond,
                                condition_type: ConditionType::Join,
                            });
                        }
                    }
                }
            }
        };

        if condition.is_none() {
            infer_conditions(self);
        }

        if let Some(join_condition) = condition {
            let sql_condition = self.translate_expression(join_condition)?;
            if Self::condition_references_known_columns(&sql_condition, &self.ctx.all_available_items) {
                self.add_join_condition(&sql_condition, join_type)?;
            } else {
                eprintln!("[JOINDBG] skip unresolved explicit condition: {}", sql_condition);
                infer_conditions(self);
            }
        }

        Ok(())
    }

    fn handle_filter(
        &mut self,
        expression: &Expr,
        child: &LogicNode,
    ) -> Result<(), GenerationError> {
        // 先处理子节点
        self.traverse_node(child)?;
        
        // 翻译过滤条件
        let sql_condition = self.translate_expression(expression)?;
        
        // [S3-P1-3] 分流：如果是聚合后的过滤，应放入 HAVING，否则放入 WHERE
        let condition = Condition {
            expression: sql_condition,
            condition_type: ConditionType::Filter,
        };
        
        if self.contains_aggregate(expression) {
            self.ctx.having_conditions.push(condition);
        } else {
            self.ctx.where_conditions.push(condition);
        }
        
        Ok(())
    }
    
    /// 检查表达式是否包含聚合函数
    fn contains_aggregate(&self, expr: &Expr) -> bool {
        match expr {
            Expr::Term(_) => false,
            Expr::Function { name, args } => {
                match name.to_uppercase().as_str() {
                    "COUNT" | "AVG" | "SUM" | "MIN" | "MAX" => true,
                    _ => args.iter().any(|arg| self.contains_aggregate(arg)),
                }
            }
            Expr::Logical { args, .. } => args.iter().any(|arg| self.contains_aggregate(arg)),
            Expr::Compare { left, right, .. } => {
                self.contains_aggregate(left) || self.contains_aggregate(right)
            }
            Expr::Exists { .. } | Expr::NotExists { .. } | Expr::Arithmetic { .. } => {
                // EXISTS subqueries and arithmetic don't contain aggregates in the outer expression
                false
            }
        }
    }
    
    /// Generate recursive CTE for path modifiers (*, +)
    fn generate_recursive_path_cte(
        &mut self,
        base_path: &LogicNode,
        recursive_path: &LogicNode,
        subject: &Term,
        object: &Term,
        min_depth: usize,
        _max_depth: usize,
    ) -> Result<(), GenerationError> {
        let cte_name = format!("recursive_path_{}", self.alias_manager.next_id());
        
        // 1. Generate SQL for the base step (anchor/recursive component)
        let mut base_gen = self.child_generator();
        let base_sql = base_gen.generate(base_path)?;
        
        let mut rec_step_gen = self.child_generator();
        let rec_step_sql = rec_step_gen.generate(recursive_path)?;

        // 2. Identify subject and object column aliases in the generated base SQL
        let subject_var = match subject {
            Term::Variable(v) => v.clone(),
            _ => "path_start".to_string(),
        };
        let object_var = match object {
            Term::Variable(v) => v.clone(),
            _ => "path_end".to_string(),
        };

        let base_subject_col = base_gen.alias_manager.get_var_alias(&subject_var)
            .cloned().unwrap_or_else(|| subject_var.clone());
        let base_object_col = base_gen.alias_manager.get_var_alias(&object_var)
            .cloned().unwrap_or_else(|| object_var.clone());

        // 3. Construct the recursive CTE
        // Anchor part (length 1 path)
        let anchor_query = format!(
            "SELECT {} AS start_node, {} AS end_node, 1 AS depth FROM ({}) AS anchor",
            base_subject_col, base_object_col, base_sql
        );

        // Recursive part (extend by one step)
        let recursive_query = format!(
            "SELECT cte.start_node, step.{} AS end_node, cte.depth + 1 \
             FROM {} AS cte \
             JOIN ({}) AS step ON cte.end_node = step.{} \
             WHERE cte.depth < 10",
            base_object_col, cte_name, rec_step_sql, base_subject_col
        );

        let mut cte_full_sql = format!(
            "WITH RECURSIVE {} AS (\n    {}\n    UNION\n    {}\n)\nSELECT * FROM {}",
            cte_name, anchor_query, recursive_query, cte_name
        );

        // 4. Handle min_depth=0 (*) by adding an identity relation
        // In OBDA, we often only care about nodes that appear in the path
        if min_depth == 0 {
            let identity_query = format!(
                "SELECT {} AS start_node, {} AS end_node, 0 AS depth FROM ({}) AS identity_base",
                base_subject_col, base_subject_col, base_sql
            );
            cte_full_sql = format!(
                "WITH RECURSIVE {} AS (\n    {}\n    UNION\n    {}\n    UNION\n    {}\n)\nSELECT * FROM {}",
                cte_name, identity_query, anchor_query, recursive_query, cte_name
            );
        }

        // 5. Add to FROM tables
        self.ctx.from_tables.push(FromTable {
            table_name: cte_name.clone(),
            alias: cte_name.clone(),
            join_type: None,
            join_condition: None,
            is_subquery: true,
            subquery_sql: Some(cte_full_sql),
        });

        // 6. Project results to variables
        let subj_alias = self.alias_manager.allocate_var_alias(&subject_var);
        let obj_alias = self.alias_manager.allocate_var_alias(&object_var);

        self.ctx.select_items.push(SelectItem {
            expression: format!("{}.start_node", cte_name),
            alias: subj_alias.clone(),
            is_aggregate: false,
        });
        self.ctx.select_items.push(SelectItem {
            expression: format!("{}.end_node", cte_name),
            alias: obj_alias.clone(),
            is_aggregate: false,
        });

        self.ctx.all_available_items.push(SelectItem {
            expression: format!("{}.start_node", cte_name),
            alias: subj_alias,
            is_aggregate: false,
        });
        self.ctx.all_available_items.push(SelectItem {
            expression: format!("{}.end_node", cte_name),
            alias: obj_alias,
            is_aggregate: false,
        });

        Ok(())
    }
    
    /// Helper to generate base SQL for a path component
    fn generate_base_sql(&self, node: &LogicNode) -> Result<String, GenerationError> {
        // Simplified implementation - extract table info from ExtensionalData
        match node {
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                let keys: Vec<_> = column_mapping.keys().collect();
                let start_col = if let Some(k) = keys.get(0) {
                    column_mapping.get(*k).unwrap_or(k).to_string()
                } else {
                    "id".to_string()
                };
                let end_col = if let Some(k) = keys.get(1) {
                    column_mapping.get(*k).unwrap_or(k).to_string()
                } else {
                    "id".to_string()
                };
                
                Ok(format!(
                    "SELECT {} AS start_node, {} AS end_node, 1 AS depth FROM {}",
                    start_col, end_col, table_name
                ))
            }
            _ => Ok("SELECT NULL AS start_node, NULL AS end_node, 1 AS depth".to_string()),
        }
    }
    
    /// 处理 CONSTRUCTION 节点（投影）
    fn handle_construction(
        &mut self,
        projected_vars: &[String],
        bindings: &HashMap<String, Expr>,
        child: &LogicNode,
    ) -> Result<(), GenerationError> {
        let start_count = self.ctx.select_items.len();
        self.traverse_node(child)?;
        
        // DEBUG: 显示 all_available_items
        let child_items = self.ctx.select_items.split_off(start_count);
        let mut new_select_items = Vec::new();
        
        // [Fix] 首先将所有子节点的 select_items 添加到 all_available_items
        // 这样即使变量不在 projected_vars 中，也能被后续查找找到
        self.ctx.all_available_items.extend(child_items.clone());
        
        // 按 projected_vars 顺序重新组织 SELECT 项
        for var_name in projected_vars {
            // [Fix] 使用与 allocate_var_alias 一致的别名生成逻辑
            let snake_var_name = to_snake_case(var_name);
            let expected_alias = format!("col_{}", snake_var_name);
            
            // 查找该变量在子节点 select_items 中的对应项
            // 首先尝试直接匹配变量名或预期的别名
            if let Some(existing) = child_items.iter()
                .find(|item| item.alias == *var_name || item.alias == expected_alias || item.alias == format!("col_{}", var_name)) {
                // [Fix] 使用原始变量名作为最终别名，而不是 col_ 前缀
                new_select_items.push(SelectItem {
                    expression: existing.expression.clone(),
                    alias: var_name.clone(), // 使用原始变量名
                    is_aggregate: existing.is_aggregate,
                });
                continue;
            }
            
            // 如果找不到，检查 binding - 如果是 Variable，查找该变量对应的列
            if let Some(expr) = bindings.get(var_name) {
                match expr {
                    Expr::Term(Term::Variable(source_var)) => {
                        // 查找 source_var 对应的列
                        let source_snake = to_snake_case(source_var);
                        let source_expected_alias = format!("col_{}", source_snake);
                        if let Some(existing) = child_items.iter()
                            .find(|item| item.alias == *source_var || item.alias == source_expected_alias || item.alias == format!("col_{}", source_var)) {
                            // 使用相同的表达式，但别名为 var_name
                            new_select_items.push(SelectItem {
                                expression: existing.expression.clone(),
                                alias: var_name.clone(),
                                is_aggregate: existing.is_aggregate,
                            });
                            continue;
                        }
                    },
                    _ => {
                        // Temporarily expose child columns so BIND expressions resolve
                        // deterministically, then restore previous SELECT context.
                        let prev_select_len = self.ctx.select_items.len();
                        for item in &child_items {
                            if !self.ctx.all_available_items.iter().any(|i| i.alias == item.alias) {
                                self.ctx.all_available_items.push(item.clone());
                            }
                            if !self.ctx.select_items.iter().any(|i| i.alias == item.alias) {
                                self.ctx.select_items.push(item.clone());
                            }
                        }

                        let sql_expr = self.translate_expression(expr)?;
                        self.ctx.select_items.truncate(prev_select_len);

                        let is_agg = self.contains_aggregate(expr);
                        new_select_items.push(SelectItem {
                            expression: sql_expr.clone(),
                            alias: var_name.clone(),
                            is_aggregate: is_agg,
                        });

                        let snake_alias = format!("col_{}", to_snake_case(var_name));
                        if snake_alias != *var_name
                            && !self.ctx.all_available_items.iter().any(|i| i.alias == snake_alias)
                        {
                            self.ctx.all_available_items.push(SelectItem {
                                expression: sql_expr.clone(),
                                alias: snake_alias.clone(),
                                is_aggregate: is_agg,
                            });
                        }

                        let _ = self.alias_manager.allocate_var_alias(var_name);
                        let _ = self.alias_manager.allocate_var_alias(&snake_alias);
                        continue;
                    }
                }
            }
            
            if let Some(existing) = self.ctx.all_available_items.iter()
                .find(|item| item.alias == *var_name || item.alias == expected_alias || item.alias == format!("col_{}", var_name)) {
                new_select_items.push(SelectItem {
                    expression: existing.expression.clone(),
                    alias: var_name.clone(),
                    is_aggregate: existing.is_aggregate,
                });
            }
        }
        
        self.ctx.select_items.extend(new_select_items.clone());
        self.ctx.all_available_items.extend(new_select_items);
        
        Ok(())
    }
    
    /// 处理 VALUES 节点
    fn handle_values(
        &mut self,
        variables: &[String],
        rows: &[Vec<Term>],
    ) -> Result<(), GenerationError> {
        let mut row_sqls = Vec::new();
        for row in rows {
            let mut val_sqls = Vec::new();
            for val in row {
                let term_sql = match val {
                    Term::Constant(c) => {
                        self.format_values_constant(c)
                    }
                    _ => self.translate_term(val)?,
                };
                val_sqls.push(term_sql);
            }
            row_sqls.push(format!("({})", val_sqls.join(", ")));
        }
        
        let values_alias = self.alias_manager.allocate_table_alias("vals");
        let col_aliases: Vec<String> = variables.iter()
            .map(|v| self.alias_manager.allocate_var_alias(v))
            .collect();
            
        if row_sqls.is_empty() {
            let alias = self.alias_manager.allocate_table_alias("vals_empty");
            let is_first = self.ctx.from_tables.is_empty();
            self.ctx.from_tables.push(FromTable {
                table_name: "(SELECT 1)".to_string(),
                alias,
                join_type: if is_first { None } else { Some(JoinType::Inner) },
                join_condition: if is_first { None } else { Some("FALSE".to_string()) },
                is_subquery: true,
                subquery_sql: None,
            });
            self.ctx.where_conditions.push(Condition {
                expression: "FALSE".to_string(),
                condition_type: ConditionType::Filter,
            });
            return Ok(());
        }

        let sql = format!("(VALUES {})", 
            row_sqls.join(", ")
        );
        
        // [Fix] Store the alias separately in FromTable to avoid duplicate AS
        self.ctx.from_tables.push(FromTable {
            table_name: sql,
            alias: format!("{}({})", values_alias, col_aliases.join(", ")),
            join_type: None,
            join_condition: None,
            is_subquery: true,
            subquery_sql: None,
        });
        
        // 注册到 select_items 供上方引用
        for (i, _var) in variables.iter().enumerate() {
            self.ctx.select_items.push(SelectItem {
                expression: format!("{}.{}", values_alias, col_aliases[i]),
                alias: col_aliases[i].clone(),
                is_aggregate: false,
            });
        }
        
        Ok(())
    }
    
    /// 处理 UNION 节点
    fn handle_union(&mut self, children: &[LogicNode]) -> Result<(), GenerationError> {
        // [S3-Fix] 生成并作为子查询加入 FROM 子句
        let union_sql = self.generate_union_sql(children)?;
        
        // 即使是根节点级别的 UNION，由 Construction 包裹时也需要作为子查询处理
        // 或者直接在这里生成 SELECT * FROM (...) AS un
        let alias = self.alias_manager.allocate_table_alias("union");
        self.ctx.from_tables.push(FromTable {
            table_name: format!("({})", union_sql),
            alias: alias.clone(),
            join_type: None,
            join_condition: None,
            is_subquery: true,
            subquery_sql: Some(union_sql.clone()),
        });
        
        // 将 union 的投影项添加到 select_items
        if let Some(first_child) = children.first() {
            for var in first_child.used_variables() {
                let var_alias = self.alias_manager.allocate_var_alias(&var);
                
                self.ctx.select_items.push(SelectItem {
                    expression: format!("{}.{}", alias, var_alias),
                    alias: var_alias,
                    is_aggregate: false,
                });
            }
        }
        
        Ok(())
    }

    fn generate_union_sql(&self, children: &[LogicNode]) -> Result<String, GenerationError> {
        if children.is_empty() {
            return Err(GenerationError::Other("UNION requires at least one branch".to_string()));
        }

        // Build a deterministic UNION schema from all child variables.
        let mut union_aliases: Vec<String> = children
            .iter()
            .flat_map(|c| c.used_variables().into_iter())
            .map(|v| format!("col_{}", to_snake_case(&v)))
            .collect();
        union_aliases.sort();
        union_aliases.dedup();

        let mut parts = Vec::with_capacity(children.len());
        for (idx, child) in children.iter().enumerate() {
            let mut branch_generator = self.child_generator();
            let branch_sql = branch_generator.generate(child)?;

            let mut branch_aliases: Vec<String> = branch_generator
                .ctx
                .select_items
                .iter()
                .map(|i| i.alias.clone())
                .collect();
            branch_aliases.sort();
            branch_aliases.dedup();

            let branch_alias = format!("u{}", idx);
            let normalized_items: Vec<String> = union_aliases
                .iter()
                .map(|alias| {
                    if branch_aliases.iter().any(|a| a == alias) {
                        format!("{}.{} AS {}", branch_alias, alias, alias)
                    } else {
                        format!("NULL AS {}", alias)
                    }
                })
                .collect();

            let normalized_sql = format!(
                "SELECT {} FROM ({}) AS {}",
                normalized_items.join(", "),
                branch_sql,
                branch_alias
            );
            parts.push(normalized_sql);
        }

        Ok(parts.join(" UNION ALL "))
    }

    /// 处理聚合节点
    fn handle_aggregation(
        &mut self,
        group_by: &[String],
        aggregates: &HashMap<String, Expr>,
        child: &LogicNode,
    ) -> Result<(), GenerationError> {
        // 先处理子节点（收集基础列到 select_items）
        self.traverse_node(child)?;

        // 记录旧的 select_items，我们需要从中挑选用于 GROUP BY 的列
        let old_select_items = std::mem::take(&mut self.ctx.select_items);
        let mut new_select_items = Vec::new();

        // [DEBUG] 打印调试信息
        eprintln!("[DEBUG] handle_aggregation: group_by={:?}", group_by);
        eprintln!("[DEBUG] old_select_items={:?}", old_select_items.iter().map(|i| (&i.alias, &i.expression)).collect::<Vec<_>>());
        eprintln!("[DEBUG] all_available_items={:?}", self.ctx.all_available_items.iter().map(|i| (&i.alias, &i.expression)).collect::<Vec<_>>());

        // 1. 处理 GROUP BY 列
        for var_name in group_by {
            // 尝试多种方式查找列
            let possible_aliases = vec![
                var_name.clone(),
                format!("col_{}", var_name),
            ];
            
            eprintln!("[DEBUG] Looking for var_name={}, possible_aliases={:?}", var_name, possible_aliases);
            
            // 在 old_select_items 中查找匹配
            let mut found_item = None;
            for alias in &possible_aliases {
                if let Some(item) = old_select_items.iter().find(|i| &i.alias == alias) {
                    eprintln!("[DEBUG] Found in old_select_items: alias={}, expr={}", item.alias, item.expression);
                    found_item = Some(item.clone());
                    break;
                }
            }
            
            // 如果没找到，尝试从 alias_manager 获取变量映射
            if found_item.is_none() {
                if let Some(var_alias) = self.alias_manager.get_var_alias(var_name) {
                    eprintln!("[DEBUG] Looking in old_select_items with var_alias={}", var_alias);
                    if let Some(item) = old_select_items.iter().find(|i| &i.alias == var_alias) {
                        eprintln!("[DEBUG] Found via alias_manager: alias={}, expr={}", item.alias, item.expression);
                        found_item = Some(item.clone());
                    }
                }
            }
            
            // 还是没找到？尝试从 all_available_items 查找（更广泛的搜索）
            if found_item.is_none() {
                eprintln!("[DEBUG] Searching in all_available_items...");
                for alias in &possible_aliases {
                    if let Some(item) = self.ctx.all_available_items.iter().find(|i| &i.alias == alias) {
                        eprintln!("[DEBUG] Found in all_available_items: alias={}, expr={}", item.alias, item.expression);
                        found_item = Some(item.clone());
                        break;
                    }
                }
            }
            
            if let Some(item) = found_item {
                new_select_items.push(item.clone());
                self.ctx.group_by.push(item.expression.clone());
            } else {
                eprintln!("[DEBUG] NOT FOUND! Using fallback for var_name={}", var_name);
                // Fallback: 使用变量名作为列表达式（可能不正确，但避免 panic）
                new_select_items.push(SelectItem {
                    expression: var_name.clone(),
                    alias: var_name.clone(),
                    is_aggregate: false,
                });
                self.ctx.group_by.push(var_name.clone());
            }
        }

        // 2. 处理聚合函数
        // 在翻译聚合表达式前，我们需要能够查找旧的 select_items（因为聚合函数如 COUNT(?emp) 需要物理列名）
        // 临时将旧 item 放回 ctx 以便 translate_term 能找到它们
        self.ctx.select_items = old_select_items.clone();

        for (alias, expr) in aggregates {
            // 使用原始别名（如 empCount）而非 col_ 前缀
            let sql_expr = self.translate_expression(expr)?;

            new_select_items.push(SelectItem {
                expression: sql_expr,
                alias: alias.clone(),  // 使用原始别名
                is_aggregate: true,
            });
        }

        // 最终更新 select_items 为只包含分组列和聚合列
        self.ctx.select_items = new_select_items;

        Ok(())
    }
    
    /// 处理 LIMIT 节点
    /// [S4-P0-1] 支持 ORDER BY
    fn handle_limit(
        &mut self,
        limit: usize,
        offset: Option<usize>,
        order_by: &[(String, bool)],
        child: &LogicNode,
    ) -> Result<(), GenerationError> {
        // 先处理子节点
        self.traverse_node(child)?;
        
        // 设置 LIMIT 和 OFFSET
        if limit == usize::MAX {
            self.ctx.limit = None;
            self.ctx.offset = None;
        } else {
            self.ctx.limit = Some(limit);
            self.ctx.offset = offset;
        }
        
        // [S4-P0-1] 转换 order_by 到 GeneratorContext
        for (var_name, is_desc) in order_by {
            // 查找变量对应的列表达式
            if let Some(expr) = self.find_column_expression(var_name) {
                self.ctx.order_by.push(OrderByItem {
                    expression: expr,
                    direction: if *is_desc { SortDirection::Desc } else { SortDirection::Asc },
                });
            }
        }
        
        Ok(())
    }
    
    /// 查找变量对应的列表达式
    fn find_column_expression(&self, var_name: &str) -> Option<String> {
        // [Fix] 生成蛇形命名的别名用于匹配
        let snake_var_name = to_snake_case(var_name);
        let expected_alias = format!("col_{}", snake_var_name);
        
        // 1. 从 select_items 查找
        for item in &self.ctx.select_items {
            if item.alias == expected_alias || item.alias == *var_name || item.alias == format!("col_{}", var_name) {
                return Some(item.expression.clone());
            }
        }
        
        // 2. 从别名管理器查找
        if let Some(var_alias) = self.alias_manager.get_var_alias(var_name) {
            for item in &self.ctx.select_items {
                if &item.alias == var_alias {
                    return Some(item.expression.clone());
                }
            }
            // 3. 从 all_available_items 查找（用于聚合后的引用）
            for item in &self.ctx.all_available_items {
                if &item.alias == var_alias {
                    return Some(item.expression.clone());
                }
            }
        }
        
        // [Fix] 4. 使用蛇形命名在 all_available_items 中查找
        for item in &self.ctx.all_available_items {
            if item.alias == expected_alias {
                return Some(item.expression.clone());
            }
        }
        
        // 5. 如果都没有找到，使用变量名本身作为回退
        Some(var_name.to_string())
    }

    /// 添加 JOIN 条件
        fn condition_references_known_columns(condition: &str, items: &[SelectItem]) -> bool {
        let re = match regex::Regex::new(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)") {
            Ok(r) => r,
            Err(_) => return true,
        };
        let mut any = false;
        for cap in re.captures_iter(condition) {
            any = true;
            let token = format!("{}.{}", &cap[1], &cap[2]);
            if !items.iter().any(|i| i.expression == token) {
                return false;
            }
        }
        if !any {
            return true;
        }
        true
    }

fn add_join_condition(
        &mut self,
        condition: &str,
        join_type: JoinType,
    ) -> Result<(), GenerationError> {
        // 找到最后添加的表作为 JOIN 的右表
        if let Some(last_table) = self.ctx.from_tables.last_mut() {
            last_table.join_type = Some(join_type);
            
            // 支持多个连接条件叠加 (AND)
            if let Some(ref prev) = last_table.join_condition {
                if !prev.contains(condition) { // 简单去重
                    last_table.join_condition = Some(format!("{} AND {}", prev, condition));
                }
            } else {
                last_table.join_condition = Some(condition.to_string());
            }
            Ok(())
        } else {
            Err(GenerationError::InvalidJoin("No table available to join".to_string()))
        }
    }
    
    /// 将表达式翻译为 SQL
    fn translate_expression(&mut self, expr: &Expr) -> Result<String, GenerationError> {
        match expr {
            Expr::Term(term) => self.translate_term(term),
            Expr::Compare { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let op_sql = self.translate_comparison_op(*op);

                if matches!(op, ComparisonOp::In | ComparisonOp::NotIn) {
                    match right.as_ref() {
                        Expr::Function { name, args } if name.eq_ignore_ascii_case("LIST") => {
                            let rhs_items: Result<Vec<_>, _> = args
                                .iter()
                                .map(|arg| self.translate_expression(arg))
                                .collect();
                            let rhs_items = rhs_items?;
                            return Ok(format!("{} {} ({})", left_sql, op_sql, rhs_items.join(", ")));
                        }
                        _ => {
                            let right_sql = self.translate_expression(right)?;
                            return Ok(format!("{} {} ({})", left_sql, op_sql, right_sql));
                        }
                    }
                }

                let right_sql = self.translate_expression(right)?;
                Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
            },
            Expr::Logical { op, args } => {
                let args_sql: Result<Vec<_>, _> = args
                    .iter()
                    .map(|arg| self.translate_expression(arg))
                    .collect();
                let args_sql = args_sql?;
                
                let op_sql = match op {
                    LogicalOp::And => "AND",
                    LogicalOp::Or => "OR",
                    LogicalOp::Not => "NOT",
                };
                
                if matches!(op, LogicalOp::Not) {
                    Ok(format!("NOT ({})", args_sql[0]))
                } else {
                    Ok(format!("({})", args_sql.join(&format!(" {} ", op_sql))))
                }
            },
            Expr::Function { name, args } => {
                let args_sql: Result<Vec<_>, _> = args
                    .iter()
                    .map(|arg| self.translate_expression(arg))
                    .collect();
                let args_sql = args_sql?;
                
                // 处理聚合函数、内部操作符和 SPARQL 内置函数
                match name.to_uppercase().as_str() {
                    // 1. 聚合函数
                    "COUNT" | "AVG" | "SUM" | "MIN" | "MAX" => {
                        let arg = if args_sql.is_empty() { "*" } else { &args_sql[0] };
                        Ok(format!("{}({})", name, arg))
                    }
                    // 2. 内部逻辑/比较操作符 (由 UnfoldingPass 等生成)
                    "EQ" if args_sql.len() == 2 => Ok(format!("{} = {}", args_sql[0], args_sql[1])),
                    "NEQ" if args_sql.len() == 2 => Ok(format!("{} <> {}", args_sql[0], args_sql[1])),
                    "LT" if args_sql.len() == 2 => Ok(format!("{} < {}", args_sql[0], args_sql[1])),
                    "LTE" if args_sql.len() == 2 => Ok(format!("{} <= {}", args_sql[0], args_sql[1])),
                    "GT" if args_sql.len() == 2 => Ok(format!("{} > {}", args_sql[0], args_sql[1])),
                    "GTE" if args_sql.len() == 2 => Ok(format!("{} >= {}", args_sql[0], args_sql[1])),
                    "AND" => Ok(format!("({})", args_sql.join(" AND "))),
                    "OR" => Ok(format!("({})", args_sql.join(" OR "))),
                    "NOT" if args_sql.len() == 1 => Ok(format!("NOT ({})", args_sql[0])),
                    
                    // 3. SPARQL 内置函数
                    "STR" if args_sql.len() == 1 => Ok(format!("CAST({} AS TEXT)", args_sql[0])),
                    "LCASE" | "LOWER" if args_sql.len() == 1 => Ok(format!("LOWER({})", args_sql[0])),
                    "UCASE" | "UPPER" if args_sql.len() == 1 => Ok(format!("UPPER({})", args_sql[0])),
                    "IF" if args_sql.len() == 3 => Ok(format!(
                        "CASE WHEN {} THEN {} ELSE {} END",
                        args_sql[0], args_sql[1], args_sql[2]
                    )),
                    "CONTAINS" if args_sql.len() == 2 => Ok(format!(
                        "POSITION({} IN {}) > 0",
                        args_sql[1], args_sql[0]
                    )),
                    "NOW" => Ok("CURRENT_TIMESTAMP".to_string()),
                    "RAND" => Ok("RANDOM()".to_string()),
                    "STRLEN" if args_sql.len() == 1 => Ok(format!("LENGTH({})", args_sql[0])),
                    // Date/Time functions
                    "YEAR" if args_sql.len() == 1 => Ok(format!("EXTRACT(YEAR FROM ({}::timestamp))", args_sql[0])),
                    "MONTH" if args_sql.len() == 1 => Ok(format!("EXTRACT(MONTH FROM ({}::timestamp))", args_sql[0])),
                    "DAY" if args_sql.len() == 1 => Ok(format!("EXTRACT(DAY FROM ({}::timestamp))", args_sql[0])),
                    "HOURS" if args_sql.len() == 1 => Ok(format!("EXTRACT(HOUR FROM ({}::timestamp))", args_sql[0])),
                    "MINUTES" if args_sql.len() == 1 => Ok(format!("EXTRACT(MINUTE FROM ({}::timestamp))", args_sql[0])),
                    "SECONDS" if args_sql.len() == 1 => Ok(format!("EXTRACT(SECOND FROM ({}::timestamp))", args_sql[0])),
                    "TIMEZONE" if args_sql.len() == 1 => Ok(format!("EXTRACT(TIMEZONE FROM ({}::timestamptz))", args_sql[0])),
                    "TZ" if args_sql.len() == 1 => Ok(format!("EXTRACT(TIMEZONE FROM ({}::timestamptz))", args_sql[0])),
                    "REGEX" if args_sql.len() >= 2 => {
                        let text = &args_sql[0];
                        let pattern = &args_sql[1];
                        Ok(format!("{} ~ {}", text, pattern))
                    }
                    
                    // 5. GeoSPARQL spatial functions (match uppercase)
                    "SFWITHIN" | "GEOF:SFWITHIN" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/SFWITHIN" if args_sql.len() == 2 => {
                        Ok(format!("ST_Within({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFCONTAINS" | "GEOF:SFCONTAINS" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/SFCONTAINS" if args_sql.len() == 2 => {
                        Ok(format!("ST_Contains({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFINTERSECTS" | "GEOF:SFINTERSECTS" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/SFINTERSECTS" if args_sql.len() == 2 => {
                        Ok(format!("ST_Intersects({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFOVERLAPS" | "GEOF:SFOVERLAPS" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/SFOVERLAPS" if args_sql.len() == 2 => {
                        Ok(format!("ST_Overlaps({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFEQUALS" | "GEOF:SFEQUALS" if args_sql.len() == 2 => {
                        Ok(format!("ST_Equals({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFDISJOINT" | "GEOF:SFDISJOINT" if args_sql.len() == 2 => {
                        Ok(format!("ST_Disjoint({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFCROSSES" | "GEOF:SFCROSSES" if args_sql.len() == 2 => {
                        Ok(format!("ST_Crosses({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "SFTOUCHES" | "GEOF:SFTOUCHES" if args_sql.len() == 2 => {
                        Ok(format!("ST_Touches({}, {})", Self::normalize_geospatial_arg(&args_sql[0]), Self::normalize_geospatial_arg(&args_sql[1])))
                    }
                    "BUFFER" | "GEOF:BUFFER" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/BUFFER" if args_sql.len() >= 2 => {
                        let radius = &args_sql[1];
                        let geom = Self::normalize_geospatial_arg(&args_sql[0]);
                        let unit_is_meter = args_sql.get(2)
                            .map(|u| {
                                let lu = u.to_ascii_lowercase();
                                lu.contains("metre") || lu.contains("meter")
                            })
                            .unwrap_or(false);
                        if unit_is_meter {
                            Ok(format!("ST_Buffer(({})::geography, {})::geometry", geom, radius))
                        } else {
                            Ok(format!("ST_Buffer({}, {})", geom, radius))
                        }
                    }
                    "DISTANCE" | "GEOF:DISTANCE" | "HTTP://WWW.OPENGIS.NET/DEF/FUNCTION/GEOSPARQL/DISTANCE" if args_sql.len() >= 2 => {
                        let left = Self::normalize_geospatial_arg(&args_sql[0]);
                        let right = Self::normalize_geospatial_arg(&args_sql[1]);
                        Ok(format!("ST_Distance({}, {})", left, right))
                    }
                    
                    // 6. 其他普通函数直接映射
                    _ => Ok(format!("{}({})", name, args_sql.join(", "))),
                }
            },
            Expr::Exists { patterns, correlated_vars, filters } => {
                let subquery_sql = self.generate_exists_subquery(patterns, correlated_vars, filters)?;
                Ok(format!("EXISTS ({})", subquery_sql))
            },
            Expr::NotExists { patterns, correlated_vars, filters } => {
                let subquery_sql = self.generate_exists_subquery(patterns, correlated_vars, filters)?;
                Ok(format!("NOT EXISTS ({})", subquery_sql))
            },
            Expr::Arithmetic { left, op, right } => {
                let left_sql = self.translate_expression(left)?;
                let right_sql = self.translate_expression(right)?;
                let op_sql = match op {
                    crate::ir::expr::ArithmeticOp::Add => "+",
                    crate::ir::expr::ArithmeticOp::Sub => "-",
                    crate::ir::expr::ArithmeticOp::Mul => "*",
                    crate::ir::expr::ArithmeticOp::Div => "/",
                };
                Ok(format!("({} {} {})", left_sql, op_sql, right_sql))
            },
        }
    }
    
    /// Generate EXISTS subquery SQL from triple patterns
    fn generate_exists_subquery(&mut self, patterns: &[crate::parser::sparql_parser_v2::TriplePattern], correlated_vars: &[String], filters: &[String]) -> Result<String, GenerationError> {
        if patterns.is_empty() {
            return Ok("SELECT 1".to_string());
        }

        let mappings = match &self.mappings {
            Some(m) => Arc::clone(m),
            None => return Err(GenerationError::Other("EXISTS requires mapping store".to_string())),
        };

        struct PatternTable {
            table_name: String,
            alias: String,
            var_columns: HashMap<String, String>,
            conditions: Vec<String>,
        }

        let mut tables = Vec::new();
        for pattern in patterns {
            let predicate_iri = Self::normalize_predicate(&pattern.predicate);
            let rule = mappings
                .mappings
                .get(&predicate_iri)
                .and_then(|rules| rules.first());

            let Some(rule) = rule else {
                return Ok("SELECT 1 WHERE 1=0".to_string());
            };

            let alias = format!("ex{}", self.alias_manager.next_id());
            let mut var_columns = HashMap::new();
            let mut conditions = Vec::new();

            let subject_col = Self::extract_subject_column(rule);
            let object_col = rule.position_to_column.get(&1).cloned();

            if let Some(var) = Self::pattern_var(&pattern.subject) {
                if let Some(col) = subject_col.clone() {
                    var_columns.insert(var, col);
                }
            } else if let Some(col) = subject_col {
                let term = Self::pattern_token_to_term(&pattern.subject);
                let value_sql = self.translate_term(&term)?;
                conditions.push(format!("{}.{} = {}", alias, col, value_sql));
            }

            if let Some(var) = Self::pattern_var(&pattern.object) {
                if let Some(col) = object_col.clone() {
                    var_columns.insert(var, col);
                }
            } else if let Some(col) = object_col {
                let term = Self::pattern_token_to_term(&pattern.object);
                let value_sql = self.translate_term(&term)?;
                conditions.push(format!("{}.{} = {}", alias, col, value_sql));
            }

            tables.push(PatternTable {
                table_name: rule.table_name.clone(),
                alias,
                var_columns,
                conditions,
            });
        }

        let mut where_parts: Vec<String> = Vec::new();
        for table in &tables {
            where_parts.extend(table.conditions.iter().cloned());
        }

        for i in 0..tables.len() {
            for j in (i + 1)..tables.len() {
                for (var, col_i) in &tables[i].var_columns {
                    if let Some(col_j) = tables[j].var_columns.get(var) {
                        where_parts.push(format!(
                            "{}.{} = {}.{}",
                            tables[i].alias, col_i, tables[j].alias, col_j
                        ));
                    }
                }
            }
        }

        for var in correlated_vars {
            let Some(outer_col) = self.find_column_for_var(var) else {
                return Ok("SELECT 1 WHERE 1=0".to_string());
            };
            let mut linked = false;
            for table in &tables {
                if let Some(col) = table.var_columns.get(var) {
                    where_parts.push(format!("{}.{} = {}", table.alias, col, outer_col));
                    linked = true;
                }
            }
            if !linked {
                return Ok("SELECT 1 WHERE 1=0".to_string());
            }
        }

        let re_simple_filter = regex::Regex::new(r"^\s*(\?\w+)\s*(=|!=|<>|>=|<=|>|<)\s*(.+?)\s*$").ok();
        for f in filters {
            let ft = f.trim();
            if ft.is_empty() || ft.to_ascii_uppercase().starts_with("EXISTS") || ft.to_ascii_uppercase().starts_with("NOT EXISTS") {
                continue;
            }
            if let Some(re) = &re_simple_filter {
                if let Some(cap) = re.captures(ft) {
                    let left = cap.get(1).map(|m| m.as_str().trim_start_matches('?').to_string());
                    let op = cap.get(2).map(|m| m.as_str().to_string());
                    let right_raw = cap.get(3).map(|m| m.as_str().trim().to_string());
                    if let (Some(left), Some(op), Some(right_raw)) = (left, op, right_raw) {
                        let left_sql = tables.iter().find_map(|t| t.var_columns.get(&left).map(|c| format!("{}.{}", t.alias, c)));
                        if let Some(left_sql) = left_sql {
                            let right_sql = if let Some(rv) = right_raw.strip_prefix('?') {
                                tables.iter().find_map(|t| t.var_columns.get(rv).map(|c| format!("{}.{}", t.alias, c)))
                            } else if (right_raw.starts_with('"') && right_raw.ends_with('"')) || (right_raw.starts_with('\'') && right_raw.ends_with('\'')) {
                                Some(format!("'{}'", right_raw[1..right_raw.len()-1].replace("'", "''")))
                            } else {
                                Some(right_raw)
                            };
                            if let Some(right_sql) = right_sql {
                                where_parts.push(format!("{} {} {}", left_sql, op, right_sql));
                            }
                        }
                    }
                }
            }
        }

        let mut from_clause = String::new();
        if let Some(first) = tables.first() {
            from_clause.push_str(&format!("{} AS {}", first.table_name, first.alias));
        }
        for table in tables.iter().skip(1) {
            from_clause.push_str(&format!(" CROSS JOIN {} AS {}", table.table_name, table.alias));
        }

        let where_clause = if where_parts.is_empty() {
            "1=1".to_string()
        } else {
            where_parts.join(" AND ")
        };

        Ok(format!("SELECT 1 FROM {} WHERE {}", from_clause, where_clause))
    }
    
    /// Find column reference for a variable in outer query context
    fn find_column_for_var(&self, var: &str) -> Option<String> {
        // Look in available items for this variable
        let expected_alias = format!("col_{}", var.to_lowercase());
        
        for item in &self.ctx.all_available_items {
            if item.alias == expected_alias || item.alias == var {
                // Extract table alias from expression (e.g., "emp.employee_id" -> "emp")
                if let Some(dot_pos) = item.expression.find('.') {
                    let table_alias = &item.expression[..dot_pos];
                    let col_name = &item.expression[dot_pos + 1..];
                    return Some(format!("{}.{}", table_alias, col_name));
                }
                return Some(item.expression.clone());
            }
        }
        
        None
    }
    
    fn normalize_geospatial_arg(arg: &str) -> String {
        let t = arg.trim();

        if t.starts_with("ST_SetSRID(") || t.starts_with("ST_GeomFromText(") || t.starts_with("ST_Transform(") {
            return t.to_string();
        }

        let lower = t.to_ascii_lowercase();
        if lower.contains("^^geo:wktliteral")
            || lower.contains("^^<http://www.opengis.net/ont/geosparql#wktliteral>")
            || (t.contains("^^") && t.starts_with('"'))
        {
            if let Some(first_quote) = t.find('"') {
                if let Some(second_quote) = t[first_quote + 1..].find('"') {
                    let wkt = &t[first_quote + 1..first_quote + 1 + second_quote];
                    return format!("ST_GeomFromText('{}', 4326)", wkt.replace("'", "''"));
                }
            }
        }

        let upper = t.to_ascii_uppercase();
        if (t.starts_with('"') && t.ends_with('"'))
            || (t.starts_with('\'') && t.ends_with('\''))
            || upper.starts_with("\"POINT(")
            || upper.starts_with("\"LINESTRING(")
            || upper.starts_with("\"POLYGON(")
            || upper.starts_with("'POINT(")
            || upper.starts_with("'LINESTRING(")
            || upper.starts_with("'POLYGON(")
        {
            let wkt = t.trim_matches('"').trim_matches('\'');
            return format!("ST_GeomFromText('{}', 4326)", wkt.replace("'", "''"));
        }

        let is_numeric = t.parse::<f64>().is_ok();
        if !is_numeric {
            return format!("ST_SetSRID({}, 4326)", t);
        }

        t.to_string()
    }

    fn normalize_predicate(predicate: &str) -> String {
        let trimmed = predicate.trim();
        if trimmed == "a" {
            return "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string();
        }
        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            return trimmed[1..trimmed.len() - 1].to_string();
        }
        trimmed.to_string()
    }

    fn pattern_var(token: &str) -> Option<String> {
        let trimmed = token.trim();
        if trimmed.starts_with('?') {
            return Some(trimmed.trim_start_matches('?').to_string());
        }
        None
    }

    fn pattern_token_to_term(token: &str) -> Term {
        let t = token.trim();
        if t.starts_with('?') {
            return Term::Variable(t.trim_start_matches('?').to_string());
        }
        if t.starts_with('<') && t.ends_with('>') && t.len() >= 2 {
            return Term::Constant(t[1..t.len() - 1].to_string());
        }
        if (t.starts_with('\"') && t.ends_with('\"')) || (t.starts_with('\'') && t.ends_with('\'')) {
            return Term::Literal {
                value: t.trim_matches('\"').trim_matches('\'').to_string(),
                datatype: None,
                language: None,
            };
        }
        if t.chars().all(|c| c.is_ascii_digit() || c == '.') {
            return Term::Literal {
                value: t.to_string(),
                datatype: Some("integer".to_string()),
                language: None,
            };
        }
        Term::Constant(t.to_string())
    }

    fn extract_subject_column(rule: &crate::mapping::MappingRule) -> Option<String> {
        let template = rule.subject_template.as_ref()?;
        let start = template.find('{')?;
        let end = template.find('}')?;
        if end > start + 1 {
            Some(template[start + 1..end].to_string())
        } else {
            None
        }
    }

        fn collect_output_vars(node: &LogicNode) -> Vec<String> {
        match node {
            LogicNode::Construction { projected_vars, .. } => projected_vars.clone(),
            LogicNode::Limit { child, .. } => Self::collect_output_vars(child),
            LogicNode::Filter { child, .. } => Self::collect_output_vars(child),
            LogicNode::Aggregation { group_by, aggregates, .. } => {
                let mut vars = group_by.clone();
                vars.extend(aggregates.keys().cloned());
                vars
            }
            LogicNode::ExtensionalData { column_mapping, .. } => column_mapping.keys().cloned().collect(),
            LogicNode::Values { variables, .. } => variables.clone(),
            LogicNode::Join { children, .. } => {
                let mut vars = Vec::new();
                for c in children {
                    vars.extend(Self::collect_output_vars(c));
                }
                vars.sort();
                vars.dedup();
                vars
            }
            _ => Vec::new(),
        }
    }

    fn handle_subquery(&mut self, inner: &LogicNode, correlated_vars: &[String]) -> Result<(), GenerationError> {
        let mut child_gen = self.child_generator();
        let sub_sql = child_gen.generate(inner)?;
        let sub_alias = self.alias_manager.allocate_table_alias("sq");
        let mut output_vars = Self::collect_output_vars(inner);
        output_vars.sort();
        output_vars.dedup();

        let mut projections: Vec<String> = Vec::new();
        let mut alias_pairs: Vec<(String, String)> = Vec::new();
        for v in &output_vars {
            let source_col = v.trim_start_matches('?').to_string();
            let alias_col = self.alias_manager.allocate_var_alias(v);
            projections.push(format!("sub_inner.{} AS {}", source_col, alias_col));
            alias_pairs.push((v.clone(), alias_col));
        }
        let wrapped_sql = if projections.is_empty() {
            format!("SELECT * FROM ({}) AS sub_inner", sub_sql)
        } else {
            format!("SELECT {} FROM ({}) AS sub_inner", projections.join(", "), sub_sql)
        };

        let is_first = self.ctx.from_tables.is_empty();
        let join_condition = if is_first {
            None
        } else if correlated_vars.is_empty() {
            Some("TRUE".to_string())
        } else {
            let mut conds: Vec<String> = Vec::new();
            for v in correlated_vars {
                let v_alias = self.alias_manager.allocate_var_alias(v);
                if let Some(item) = self.ctx.all_available_items.iter().find(|i| i.alias == v_alias || i.alias == *v) {
                    conds.push(format!("{} = {}.{}", item.expression, sub_alias, v_alias));
                }
            }
            if conds.is_empty() { Some("TRUE".to_string()) } else { Some(conds.join(" AND ")) }
        };

        self.ctx.from_tables.push(FromTable {
            table_name: format!("({})", wrapped_sql),
            alias: sub_alias.clone(),
            join_type: if is_first { None } else { Some(JoinType::Inner) },
            join_condition,
            is_subquery: true,
            subquery_sql: Some(wrapped_sql),
        });

        for (raw_var, alias_col) in alias_pairs {
            let expr = format!("{}.{}", sub_alias, alias_col);
            if !self.ctx.all_available_items.iter().any(|i| i.alias == alias_col) {
                self.ctx.all_available_items.push(SelectItem {
                    expression: expr.clone(),
                    alias: alias_col.clone(),
                    is_aggregate: false,
                });
            }
            if !self.ctx.select_items.iter().any(|i| i.alias == alias_col) {
                self.ctx.select_items.push(SelectItem {
                    expression: expr.clone(),
                    alias: alias_col,
                    is_aggregate: false,
                });
            }

            if !self.ctx.all_available_items.iter().any(|i| i.alias == raw_var) {
                self.ctx.all_available_items.push(SelectItem {
                    expression: expr.clone(),
                    alias: raw_var.clone(),
                    is_aggregate: false,
                });
            }
            if !self.ctx.select_items.iter().any(|i| i.alias == raw_var) {
                self.ctx.select_items.push(SelectItem {
                    expression: expr,
                    alias: raw_var,
                    is_aggregate: false,
                });
            }
        }

        Ok(())
    }

    fn format_values_constant(&self, raw: &str) -> String {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            return "''".to_string();
        }

        if (trimmed.starts_with('\"') && trimmed.ends_with('\"'))
            || (trimmed.starts_with('\'') && trimmed.ends_with('\''))
        {
            let inner = trimmed.trim_matches('\"').trim_matches('\'');
            return format!("'{}'", self.escape_sql_string(inner));
        }

        let lower = trimmed.to_ascii_lowercase();
        if lower == "true" || lower == "false" {
            return lower;
        }

        if trimmed.chars().all(|c| c.is_ascii_digit() || c == '.') {
            return trimmed.to_string();
        }

        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            let inner = &trimmed[1..trimmed.len() - 1];
            if let Some(num) = Self::extract_trailing_number(inner) {
                return num;
            }
            return format!("'{}'", self.escape_sql_string(inner));
        }

        if let Some(num) = Self::extract_trailing_number(trimmed) {
            return num;
        }

        format!("'{}'", self.escape_sql_string(trimmed))
    }

    fn extract_trailing_number(value: &str) -> Option<String> {
        let mut digits = String::new();
        for ch in value.chars().rev() {
            if ch.is_ascii_digit() {
                digits.push(ch);
            } else {
                break;
            }
        }
        if digits.is_empty() {
            return None;
        }
        Some(digits.chars().rev().collect::<String>())
    }
    
    /// 翻译术语为 SQL
    fn translate_term(&mut self, term: &Term) -> Result<String, GenerationError> {
        match term {
            Term::Variable(var_name) => {
                let var_alias = self.alias_manager.get_var_alias(var_name).cloned().unwrap_or_else(|| var_name.clone());

                // 1. 在 select_items 中查找
                if let Some(item) = self.ctx.select_items.iter().find(|i| i.alias == var_alias || i.alias == *var_name) {
                    return Ok(item.expression.clone());
                }

                // 2. 在 all_available_items 中查找
                if let Some(item) = self.ctx.all_available_items.iter().find(|i| i.alias == var_alias || i.alias == *var_name) {
                    return Ok(item.expression.clone());
                }

                // 3. 从 from_tables 中回退
                if let Some(from_table) = self.ctx.from_tables.first() {
                    let candidates = vec![
                        format!("{}.{}", from_table.alias, var_alias),
                        format!("{}.{}", from_table.alias, var_name),
                        format!("{}.col_{}", from_table.alias, var_name),
                        format!("{}.col_{}", from_table.alias, to_snake_case(var_name)),
                    ];
                    if let Some(c) = candidates.into_iter().next() {
                        return Ok(c);
                    }
                }

                let available_aliases: Vec<_> = self.ctx.all_available_items.iter()
                    .map(|i| format!("{}:{}", i.alias, i.expression))
                    .collect();
                let table_names: Vec<_> = self.ctx.from_tables.iter()
                    .map(|t| t.table_name.clone())
                    .collect();
                let col_mapping_keys: Vec<String> = self.ctx.all_available_items.iter()
                    .map(|i| i.alias.clone())
                    .filter(|k| k.starts_with("col_"))
                    .map(|k| k.trim_start_matches("col_").to_string())
                    .collect();

                Err(GenerationError::UnmappedVariable(format!(
                    "{} (tables: {:?}, column_mapping_keys: {:?}, available: [{}])",
                    var_name,
                    table_names,
                    col_mapping_keys,
                    available_aliases.join(", ")
                )))
            },
            Term::Constant(value) => {
                if value == "*" {
                    return Ok("*".to_string());
                }

                // Fallback typed-literal handling when parser produced Constant.
                if let Some(pos) = value.find("^^") {
                    let lit = value[..pos].trim();
                    let dtype = value[pos + 2..].trim().to_ascii_lowercase();
                    if ((lit.starts_with('"') && lit.ends_with('"'))
                        || (lit.starts_with('\'') && lit.ends_with('\'')))
                        && lit.len() >= 2
                    {
                        let raw = &lit[1..lit.len() - 1];
                        let escaped = self.escape_sql_string(raw);
                        if dtype.ends_with(":date") || dtype.contains("/date") {
                            return Ok(format!("'{}'::date", escaped));
                        }
                        if dtype.contains("datetime") || dtype.contains("timestamp") {
                            return Ok(format!("'{}'::timestamp", escaped));
                        }
                        return Ok(format!("'{}'", escaped));
                    }
                }

                Ok(format!("'{}'", self.escape_sql_string(value)))
            },
            Term::Literal { value, datatype, language: _ } => {
                let escaped_value = self.escape_sql_string(value);
                match datatype.as_deref() {
                    Some(dt) => {
                        let dt_lower = dt.to_ascii_lowercase();
                        if dt_lower.contains("integer") || dt_lower.ends_with(":int") {
                            Ok(escaped_value)
                        } else if dt_lower.contains("decimal")
                            || dt_lower.contains("double")
                            || dt_lower.contains("float")
                        {
                            Ok(escaped_value)
                        } else if dt_lower.contains("boolean") {
                            Ok(escaped_value)
                        } else if dt_lower.ends_with(":date") || dt_lower.contains("/date") {
                            Ok(format!("'{}'::date", escaped_value))
                        } else if dt_lower.contains("datetime") || dt_lower.contains("timestamp") {
                            Ok(format!("'{}'::timestamp", escaped_value))
                        } else {
                            Ok(format!("'{}'", escaped_value))
                        }
                    }
                    None => Ok(format!("'{}'", escaped_value)),
                }
            }
            Term::Column { table, column } => {
                if let Some(from_table) = self.ctx.from_tables.iter().find(|t| t.table_name == *table || t.alias == *table) {
                    return Ok(format!("{}.{}", from_table.alias, column));
                }
                if let Some(item) = self.ctx.all_available_items.iter().find(|i| i.expression.ends_with(&format!(".{}", column))) {
                    return Ok(item.expression.clone());
                }
                Err(GenerationError::UnmappedVariable(format!(
                    "Column '{}.{}' not found in SQL context", table, column
                )))
            }
            Term::BlankNode(b) => Ok(format!("'{}'", self.escape_sql_string(b))),
        }
    }

    
    /// 翻译比较操作符
    fn translate_comparison_op(&self, op: ComparisonOp) -> &'static str {
        match op {
            ComparisonOp::Eq => "=",
            ComparisonOp::Neq => "<>",
            ComparisonOp::Lt => "<",
            ComparisonOp::Lte => "<=",
            ComparisonOp::Gt => ">",
            ComparisonOp::Gte => ">=",
            ComparisonOp::In => "IN",
            ComparisonOp::NotIn => "NOT IN",
        }
    }
    
    /// 转义 SQL 字符串
    fn escape_sql_string(&self, value: &str) -> String {
        value
            .replace('\'', "''")
            .replace('\\', "\\\\")
    }
    
    /// 拼装最终的扁平 SQL
    fn assemble_sql(&self) -> Result<String, GenerationError> {
        if let Some(union_sql) = &self.ctx.union_sql {
            return Ok(union_sql.clone());
        }

        let mut sql = String::new();
        // SELECT 子句 (去重)
        sql.push_str("SELECT ");
        if self.ctx.select_items.is_empty() {
            sql.push_str("*");
        } else {
            let mut seen_aliases = HashSet::new();
            let select_parts: Vec<String> = self.ctx.select_items
                .iter()
                .filter(|item| seen_aliases.insert(item.alias.clone()))
                .map(|item| {
                    if item.expression == item.alias {
                        item.expression.clone()
                    } else {
                        format!("{} AS {}", item.expression, item.alias)
                    }
                })
                .collect();
            sql.push_str(&select_parts.join(", "));
        }
        
        // FROM 子句
        sql.push_str(" FROM ");
        let from_parts: Vec<String> = self.ctx.from_tables
            .iter()
            .enumerate()
            .map(|(i, table)| {
                if i == 0 {
                    // 第一个表
                    format!("{} AS {}", table.table_name, table.alias)
                } else {
                    // 后续表需要 JOIN
                    let join_type = match table.join_type {
                        Some(JoinType::Inner) => "INNER JOIN",
                        Some(JoinType::Left) => "LEFT JOIN",
                        Some(JoinType::Union) => "UNION",
                        None => "CROSS JOIN",
                    };
                    
                    if let Some(ref condition) = table.join_condition {
                        format!(" {} {} AS {} ON {}", join_type, table.table_name, table.alias, condition)
                    } else {
                        format!(" {} {} AS {}", join_type, table.table_name, table.alias)
                    }
                }
            })
            .collect();
        sql.push_str(&from_parts.join(" "));
        
        // WHERE 子句
        if !self.ctx.where_conditions.is_empty() {
            let where_parts: Vec<String> = self.ctx.where_conditions
                .iter()
                .map(|condition| condition.expression.clone())
                .collect();
            sql.push_str(" WHERE ");
            sql.push_str(&where_parts.join(" AND "));
        }
        
        // GROUP BY 子句
        if !self.ctx.group_by.is_empty() {
            sql.push_str(" GROUP BY ");
            sql.push_str(&self.ctx.group_by.join(", "));
        }
        
        // HAVING 子句
        if !self.ctx.having_conditions.is_empty() {
            let having_parts: Vec<String> = self.ctx.having_conditions
                .iter()
                .map(|condition| condition.expression.clone())
                .collect();
            sql.push_str(" HAVING ");
            sql.push_str(&having_parts.join(" AND "));
        }
        
        // ORDER BY 子句
        if !self.ctx.order_by.is_empty() {
            let order_parts: Vec<String> = self.ctx.order_by
                .iter()
                .map(|item| {
                    match item.direction {
                        SortDirection::Asc => format!("{} ASC", item.expression),
                        SortDirection::Desc => format!("{} DESC", item.expression),
                    }
                })
                .collect();
            sql.push_str(" ORDER BY ");
            sql.push_str(&order_parts.join(", "));
        }
        
        // LIMIT 子句
        if let Some(limit) = self.ctx.limit {
            sql.push_str(&format!(" LIMIT {}", limit));
        }
        
        // OFFSET 子句
        if let Some(offset) = self.ctx.offset {
            sql.push_str(&format!(" OFFSET {}", offset));
        }
        
        Ok(sql)
    }
}

/// 生成错误类型
#[derive(Debug, Clone)]
pub enum GenerationError {
    /// 无效的 JOIN
    InvalidJoin(String),
    /// 未映射的变量
    UnmappedVariable(String),
    /// 未展开的谓词
    UnexpandedPredicate(String),
    /// 表达式错误
    ExpressionError(String),
    /// 其他错误
    Other(String),
}

impl std::fmt::Display for GenerationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GenerationError::InvalidJoin(msg) => write!(f, "Invalid join: {}", msg),
            GenerationError::UnmappedVariable(msg) => write!(f, "Unmapped variable: {}", msg),
            GenerationError::UnexpandedPredicate(msg) => write!(f, "Unexpanded predicate: {}", msg),
            GenerationError::ExpressionError(msg) => write!(f, "Expression error: {}", msg),
            GenerationError::Other(msg) => write!(f, "Generation error: {}", msg),
        }
    }
}

impl std::error::Error for GenerationError {}
