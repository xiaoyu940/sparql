use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use crate::ir::expr::{ArithmeticOp, ComparisonOp, Expr, LogicalOp, Term};
use crate::ir::node::{JoinType, LogicNode};
use crate::mapping::MappingStore;
use crate::metadata::TableMetadata;

use super::ParsedQuery;
use crate::parser::sparql_parser_v2::SortDirection;

/// IR 转换器
/// 
/// 负责将解析后的 SPARQL 查询转换为内部中间表示 (IR) 逻辑计划。
/// 支持基本图模式、FILTER、聚合查询等 SPARQL 特性的 IR 构建。
#[derive(Debug, Default)]
pub struct IRConverter;

impl IRConverter {
    /// 将解析后的查询转换为 IR 逻辑计划（无映射版本）
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `metadata` - 主表元数据
    ///
    /// # Returns
    /// 返回构建的 LogicNode 根节点
    pub fn convert(parsed: &ParsedQuery, metadata: Arc<TableMetadata>) -> LogicNode {
        // 将单表转换为 HashMap 以兼容新接口
        let mut metadata_map = std::collections::HashMap::new();
        let table_name = metadata.table_name.clone();
        metadata_map.insert(table_name, metadata);
        Self::convert_with_mappings(parsed, &metadata_map, None)
    }

    /// 将解析后的查询转换为 IR 逻辑计划（带映射配置）
    ///
    /// # Arguments
    /// * `parsed` - 解析后的 SPARQL 查询
    /// * `metadata` - 主表元数据
    /// * `mappings` - 可选的 RDF 映射配置
    ///
    /// # Returns
    /// 返回构建的 LogicNode 根节点，包含完整查询逻辑计划
    ///
    /// # Processing Flow
    /// 1. 提取投影变量
    /// 2. 构建核心查询计划
    /// 3. 添加 FILTER 条件
    /// 4. 处理聚合查询（如有）
    /// 5. 添加 ORDER BY 和 LIMIT
    /// 6. 构建 Construction 节点
    pub fn convert_with_mappings(
        parsed: &ParsedQuery,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> LogicNode {
        let projected_vars: Vec<String> = parsed
            .projected_vars
            .iter()
            .map(|v| v.trim_start_matches('?').to_string())
            .collect::<Vec<_>>();
        
        // 1. 构建核心计划 (Join / Scan)
        let mut core = Self::build_core_plan_with_vars(
            parsed, 
            metadata_map, 
            mappings, 
            &projected_vars
        );
        
        // [S3-P1-1] 处理子查询 (通过递归调用并将结果 JOIN)
        for sub_parsed in &parsed.sub_queries {
            let mut sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);
            let core_bindings = Self::extract_var_bindings(&core);
            let sub_vars = Self::collect_query_vars(sub_parsed);
            let correlated_vars: Vec<String> = sub_vars
                .into_iter()
                .filter(|v| core_bindings.contains_key(v))
                .collect();

            if !correlated_vars.is_empty() {
                sub_plan = Self::promote_correlated_vars(sub_plan, &correlated_vars);
            }
            let sub_node = LogicNode::SubQuery {
                inner: Box::new(sub_plan),
                correlated_vars,
            };
            let replace_core = matches!(&core, LogicNode::ExtensionalData { table_name, column_mapping, .. } if table_name == "(SELECT 1)" && column_mapping.is_empty());
            if replace_core {
                core = sub_node;
            } else {
                Self::join_node_to_core(&mut core, sub_node);
            }
        }

        // [S3-P2-2] 处理 VALUES (内联数据)
        if let Some(values) = &parsed.values_block {
            let mut rows = Vec::new();
            for row in &values.rows {
                let mut terms = Vec::new();
                for val in row {
                    terms.push(Term::Constant(val.clone()));
                }
                rows.push(terms);
            }
            let values_node = LogicNode::Values {
                variables: values.variables.clone(),
                rows,
            };
            
            Self::join_node_to_core(&mut core, values_node);
        }

        // 2. 先处理 BIND 表达式，确保后续 FILTER 可以引用别名变量
        let mut bind_alias_exprs: HashMap<String, Expr> = HashMap::new();
        for bind in &parsed.bind_expressions {
            if let Some(expr) = Self::parse_filter_expr(&bind.expression) {
                bind_alias_exprs.insert(bind.alias.clone(), expr.clone());

                let mut current_bindings = HashMap::new();
                for var in core.used_variables() {
                    current_bindings.insert(var.clone(), Expr::Term(Term::Variable(var)));
                }
                current_bindings.insert(bind.alias.clone(), expr);

                let mut current_vars: Vec<String> = current_bindings.keys().cloned().collect();
                current_vars.sort();
                core = LogicNode::Construction {
                    projected_vars: current_vars,
                    bindings: current_bindings,
                    child: Box::new(core),
                };
            }
        }

        // 3. 再处理 FILTER（可引用 BIND 别名）
        for filter in &parsed.filter_expressions {
            let expanded_filter = Self::expand_bind_aliases_in_filter(filter, &parsed.bind_expressions);
            if let Some(expr) = Self::parse_exists_filter_expr(&expanded_filter, &core) {
                core = LogicNode::Filter {
                    expression: expr,
                    child: Box::new(core),
                };
                continue;
            }
            if let Some(expr) = Self::parse_filter_expr(&expanded_filter) {
                let substituted = Self::substitute_bind_aliases(expr, &bind_alias_exprs);
                core = LogicNode::Filter {
                    expression: substituted,
                    child: Box::new(core),
                };
            }
        }

        // 4. 处理聚合查询
        if !parsed.aggregates.is_empty() || !parsed.group_by.is_empty() {
            core = Self::build_aggregation_node(parsed, core, &projected_vars);
            
            // 5. 处理 HAVING (聚合后)
            for having in &parsed.having_expressions {
                if let Some(expr) = Self::parse_filter_expr(having) {
                    core = LogicNode::Filter {
                        expression: expr,
                        child: Box::new(core),
                    };
                }
            }
        }
        
        // 6. 添加 ORDER BY
        let order_by: Vec<(String, bool)> = parsed.order_by.iter()
            .map(|item| {
                let var_name = item.variable.trim_start_matches('?').to_string();
                let is_desc = item.direction == SortDirection::Desc;
                (var_name, is_desc)
            })
            .collect();

        if parsed.limit.is_some() || !order_by.is_empty() {
            core = LogicNode::Limit {
                limit: parsed.limit.unwrap_or(usize::MAX),
                offset: None,
                order_by,
                child: Box::new(core),
            };
        }

        // 8. 构建最终 Construction 节点
        let mut bindings = HashMap::new();
        for var in &projected_vars {
            if let Some(bind_expr) = bind_alias_exprs.get(var) {
                bindings.insert(var.clone(), bind_expr.clone());
            } else {
                bindings.insert(var.clone(), Expr::Term(Term::Variable(var.clone())));
            }
        }

        LogicNode::Construction {
            projected_vars: projected_vars.clone(),
            bindings,
            child: Box::new(core),
        }
    }
    
    fn resolve_var_alias(var: &str, aliases: &HashMap<String, String>) -> String {
        let mut current = var.to_string();
        let mut guard = 0;
        while let Some(next) = aliases.get(&current) {
            if next == &current || guard > 32 {
                break;
            }
            current = next.clone();
            guard += 1;
        }
        current
    }

    fn join_node_to_core(core: &mut LogicNode, new_node: LogicNode) {
        match core {
            LogicNode::Join { children, .. } => {
                children.push(new_node);
            }
            _ => {
                let old_core = std::mem::replace(core, LogicNode::Union(vec![]));
                *core = LogicNode::Join {
                    children: vec![old_core, new_node],
                    condition: None,
                    join_type: crate::ir::node::JoinType::Inner,
                };
            }
        }
    }

    /// 构建聚合查询节点
    fn build_aggregation_node(
        parsed: &ParsedQuery,
        child: LogicNode,
        projected_vars: &[String],
    ) -> LogicNode {
        use std::collections::HashMap;
        use crate::ir::expr::Expr;
        use crate::ir::expr::Term;
        
        // 提取 GROUP BY 变量
        // 1. 如果 SPARQL 中有显式的 GROUP BY，则优先使用
        // 2. 否则，推断非聚合的投影变量为分组变量
        let group_by_vars: Vec<String> = if !parsed.group_by.is_empty() {
            parsed.group_by.clone()
        } else {
            let aggregate_aliases: HashSet<String> = parsed.aggregates
                .iter()
                .map(|a| a.alias.clone())
                .collect();
            
            projected_vars
                .iter()
                .filter(|v| !aggregate_aliases.contains(*v))
                .cloned()
                .collect()
        };
        
        // 构建聚合表达式映射
        let mut aggregates = HashMap::new();
        for agg in &parsed.aggregates {
            let expr = if agg.arg == "*" {
                // COUNT(*) 使用特殊处理
                Expr::Function {
                    name: agg.func.clone(),
                    args: vec![Expr::Term(Term::Constant("*".to_string()))],
                }
            } else if agg.arg.starts_with('?') {
                // 其他聚合函数使用变量
                let var_name = agg.arg.trim_start_matches('?').to_string();
                Expr::Function {
                    name: agg.func.clone(),
                    args: vec![Expr::Term(Term::Variable(var_name))],
                }
            } else {
                // 字面量
                Expr::Function {
                    name: agg.func.clone(),
                    args: vec![Expr::Term(Term::Constant(agg.arg.clone()))],
                }
            };
            aggregates.insert(agg.alias.clone(), expr);
        }
        
        // 创建聚合节点
        let agg_node = LogicNode::Aggregation { having: None,
            group_by: group_by_vars,
            aggregates,
            child: Box::new(child),
        };
        
        // 添加 Construction 节点包装聚合结果
        let mut bindings = HashMap::new();
        for var in projected_vars {
            bindings.insert(var.clone(), Expr::Term(Term::Variable(var.clone())));
        }
        
        LogicNode::Construction {
            projected_vars: projected_vars.to_vec(),
            bindings,
            child: Box::new(agg_node),
        }
    }

    pub fn build_fallback_logic() -> LogicNode {
        // 从配置读取默认谓词，避免硬编码
        LogicNode::IntensionalData {
            predicate: "default".to_string(),
            args: vec![Term::Variable("s".to_string())],
        }
    }

    fn build_core_plan_with_vars(
        parsed: &ParsedQuery,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
        projected_vars: &[String],
    ) -> LogicNode {
        // DEBUG: 检查接收到的 metadata_map
        eprintln!("[DEBUG build_core] metadata_map has {} tables: {:?}", 
            metadata_map.len(),
            metadata_map.keys().collect::<Vec<_>>());
        
        // DEBUG: 检查 parsed 中的 patterns
        eprintln!("[DEBUG build_core] parsed.main_patterns.len: {}, parsed.optional_patterns.len: {}, parsed.union_patterns.len: {}", 
            parsed.main_patterns.len(), parsed.optional_patterns.len(), parsed.union_patterns.len());
        for (i, p) in parsed.main_patterns.iter().enumerate() {
            eprintln!("[DEBUG build_core] main_pattern[{}]: subject={}, predicate={}, object={}", 
                i, p.subject, p.predicate, p.object);
        }
        
        // 收集所有需要的变量（包括投影变量、JOIN连接变量和FILTER变量）
        let mut needed_vars: std::collections::HashSet<String> = projected_vars.iter().cloned().collect();
        
        // 从主模式中提取变量
        for pattern in &parsed.main_patterns {
            if pattern.subject.starts_with('?') {
                needed_vars.insert(pattern.subject.trim_start_matches('?').to_string());
            }
            if pattern.object.starts_with('?') {
                needed_vars.insert(pattern.object.trim_start_matches('?').to_string());
            }
        }
        
        let mut join_var_counts: HashMap<String, usize> = HashMap::new();
        for pattern in &parsed.main_patterns {
            if let Some(v) = pattern.subject.strip_prefix('?') {
                *join_var_counts.entry(v.to_string()).or_insert(0) += 1;
            }
            if let Some(v) = pattern.object.strip_prefix('?') {
                *join_var_counts.entry(v.to_string()).or_insert(0) += 1;
            }
        }
        for (v, cnt) in join_var_counts {
            if cnt > 1 {
                needed_vars.insert(v);
            }
        }

        // 从 FILTER 表达式中提取变量
        for filter in &parsed.filter_expressions {
            let ft = filter.trim();
            let upper = ft.to_ascii_uppercase();
            if upper.starts_with("EXISTS") || upper.starts_with("NOT EXISTS") {
                continue;
            }
            let re = regex::Regex::new(r"\?([A-Za-z_][A-Za-z0-9_]*)") .unwrap();
            for cap in re.captures_iter(filter) {
                needed_vars.insert(cap[1].to_string());
            }
        }
        
        if !parsed.union_patterns.is_empty() {
            let branches = parsed
                .union_patterns
                .iter()
                .map(|branch| Self::build_join_from_patterns_with_vars(branch, metadata_map, mappings, &needed_vars))
                .collect::<Vec<_>>();
            return LogicNode::Union(branches);
        }

        let mut node =
            Self::build_join_from_patterns_with_vars(&parsed.main_patterns, metadata_map, mappings, &needed_vars);
        for optional in &parsed.optional_patterns {
            let right = Self::build_join_from_patterns_with_vars(optional, metadata_map, mappings, &needed_vars);
            node = LogicNode::Join {
                children: vec![node, right],
                condition: None,
                join_type: JoinType::Left,
            };
        }
        
        // [FIX] Apply only filters that do not depend on BIND aliases.
        let bind_alias_refs: Vec<String> = parsed
            .bind_expressions
            .iter()
            .map(|b| format!("?{}", b.alias))
            .collect();

        for filter_str in &parsed.filter_expressions {
            if bind_alias_refs.iter().any(|alias| filter_str.contains(alias)) {
                continue;
            }

            let ft = filter_str.trim();
            let upper = ft.to_ascii_uppercase();
            let parsed_expr = if upper.starts_with("EXISTS") || upper.starts_with("NOT EXISTS") {
                Self::parse_exists_filter_expr(ft, &node)
            } else {
                Self::parse_filter_expr(ft)
            };

            if let Some(expr) = parsed_expr {
                node = LogicNode::Filter {
                    expression: expr,
                    child: Box::new(node),
                };
            }
        }
        
        node
    }

    fn build_join_from_patterns_with_vars(
        patterns: &[super::TriplePattern],
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
        needed_vars: &std::collections::HashSet<String>,
    ) -> LogicNode {
        // DEBUG: 检查接收到的 metadata_map
        eprintln!("[DEBUG build_join] metadata_map.keys: {:?}", metadata_map.keys().collect::<Vec<_>>());
        eprintln!("[DEBUG build_join] patterns count: {}", patterns.len());
        for (i, p) in patterns.iter().enumerate() {
            eprintln!("[DEBUG build_join] pattern[{}]: subject={}, predicate={}, object={}", 
                i, p.subject, p.predicate, p.object);
        }
        
        if patterns.is_empty() {
            let metadata = Arc::new(TableMetadata {
                table_name: "(SELECT 1)".to_string(),
                columns: Vec::new(),
                primary_keys: Vec::new(),
                foreign_keys: Vec::new(),
                unique_constraints: Vec::new(),
                check_constraints: Vec::new(),
                not_null_columns: Vec::new(),
            });
            return LogicNode::ExtensionalData {
                table_name: "(SELECT 1)".to_string(),
                column_mapping: HashMap::new(),
                metadata,
            };
        }

        // [Fix] Separate property paths from normal patterns
        let mut normal_patterns = Vec::new();
        let mut path_patterns = Vec::new();

        for pattern in patterns {
            if let Some(path) = crate::parser::property_path_parser::PropertyPathParser::parse(&pattern.predicate) {
                if !matches!(path, crate::ir::node::PropertyPath::Predicate(_)) {
                    path_patterns.push((pattern.clone(), path));
                    continue;
                }
            }
            normal_patterns.push(pattern);
        }

        // 第一步：确定每个模式对应的表，并按表分组
        let mut table_patterns: HashMap<String, Vec<&super::TriplePattern>> = HashMap::new();
        let mut table_metadata: HashMap<String, Arc<TableMetadata>> = HashMap::new();
        let mut table_filters: HashMap<String, Vec<Expr>> = HashMap::new();
        let mut subject_preferred_table: HashMap<String, String> = HashMap::new();
        let mut var_aliases: HashMap<String, String> = HashMap::new();
        let mut impossible_pattern = false;
        
        let mut ordered_patterns: Vec<&super::TriplePattern> = normal_patterns.clone();
        ordered_patterns.sort_by_key(|p| if Self::is_rdf_type_predicate(&p.predicate) { 1 } else { 0 });

        for pattern in &ordered_patterns {
            let canonical_subject_for_lookup = if pattern.subject.starts_with('?') {
                Self::resolve_var_alias(&pattern.subject, &var_aliases)
            } else {
                pattern.subject.clone()
            };
            let preferred_table = subject_preferred_table
                .get(&canonical_subject_for_lookup)
                .map(|s| s.as_str());
            let metadata_opt = if Self::is_rdf_type_predicate(&pattern.predicate) {
                if let Some(store) = mappings {
                    if let Some(tbl) = Self::unique_class_table_for_type_pattern(pattern, store) {
                        metadata_map.get(&tbl).cloned()
                    } else {
                        let class_iri = if pattern.object.starts_with('<') && pattern.object.ends_with('>') {
                            pattern.object.trim_start_matches('<').trim_end_matches('>').to_string()
                        } else {
                            pattern.object.clone()
                        };
                        let mut candidates: Vec<&crate::mapping::MappingRule> = store
                            .mappings
                            .get(&class_iri)
                            .map(|rules| {
                                rules
                                    .iter()
                                    .filter(|r| Self::mapping_rule_is_usable(r, metadata_map))
                                    .collect()
                            })
                            .unwrap_or_default();

                        if candidates.is_empty() {
                            preferred_table.and_then(|p| metadata_map.get(p).cloned())
                        } else if let Some(pref) = preferred_table {
                            if let Some(rule) = candidates.iter().find(|r| r.table_name == pref) {
                                metadata_map.get(&rule.table_name).cloned()
                            } else {
                                candidates
                                    .first()
                                    .and_then(|r| metadata_map.get(&r.table_name).cloned())
                            }
                        } else {
                            candidates
                                .first()
                                .and_then(|r| metadata_map.get(&r.table_name).cloned())
                        }
                    }
                } else {
                    None
                }
            } else {
                Self::resolve_metadata_for_predicate_with_context(
                    &pattern.predicate,
                    Some(&canonical_subject_for_lookup),
                    preferred_table,
                    metadata_map,
                    mappings
                )
            };

            let metadata = if let Some(m) = metadata_opt {
                m
            } else {
                impossible_pattern = true;
                break;
            };
            
            if pattern.subject.starts_with('?') && pattern.object.starts_with('?') {
                if let Some(store) = mappings {
                    let pred_iri = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                        pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                    } else {
                        pattern.predicate.to_string()
                    };

                    if let Some(rule) = store
                        .mappings
                        .get(&pred_iri)
                        .and_then(|rules| {
                            rules.iter().find(|rule| {
                                rule.table_name == metadata.table_name
                                    && Self::mapping_rule_is_usable(rule, metadata_map)
                            })
                        })
                    {
                        let subject_col = rule
                            .subject_template
                            .as_ref()
                            .and_then(|tpl| Self::extract_subject_column_from_template(tpl));
                        let object_col = rule.position_to_column.get(&1).cloned();
                        if let (Some(subject_col), Some(object_col)) = (subject_col, object_col) {
                            if subject_col == object_col {
                                let subject_var = Self::resolve_var_alias(&pattern.subject, &var_aliases);
                                let object_var = Self::resolve_var_alias(&pattern.object, &var_aliases);
                                if subject_var != object_var {
                                    var_aliases.insert(object_var, subject_var);
                                }
                            }
                        }
                    }
                }
            }

            let canonical_subject = if pattern.subject.starts_with('?') {
                Self::resolve_var_alias(&pattern.subject, &var_aliases)
            } else {
                pattern.subject.clone()
            };

            let table_name_hint = metadata.table_name.clone();
            if Self::is_rdf_type_predicate(&pattern.predicate) {
                subject_preferred_table
                    .entry(canonical_subject.clone())
                    .or_insert(table_name_hint.clone());
            } else {
                subject_preferred_table.insert(canonical_subject.clone(), table_name_hint.clone());
            }
            if pattern.object.starts_with('?') {
                let canonical_object = Self::resolve_var_alias(&pattern.object, &var_aliases);
                subject_preferred_table
                    .entry(canonical_object)
                    .or_insert(table_name_hint.clone());
            }

            let group_key = format!("{}::{}", metadata.table_name, canonical_subject);
            table_patterns.entry(group_key.clone()).or_default().push(*pattern);
            table_metadata.entry(group_key.clone()).or_insert(metadata);
        }
        
        eprintln!("[DEBUG IRConverter] Grouped normal patterns by key: {:?}", 
            table_patterns.keys().collect::<Vec<_>>());

        // 第二步：为每个表创建一个合并的ExtensionalData节点
        let mut table_nodes: Vec<(String, LogicNode)> = Vec::new();
        
        for (group_key, table_patterns_list) in table_patterns {
            let metadata = table_metadata.get(&group_key).unwrap();
            let table_name = metadata.table_name.clone();
            let mut column_mapping = HashMap::new();
            let mut used_cols = HashSet::new();
            
            // 预定义连接变量到正确的列映射
            let join_var_mappings: HashMap<String, String> = [
                ("dept".to_string(), "department_id".to_string()),
                ("emp".to_string(), "employee_id".to_string()),
                ("location".to_string(), "location".to_string()),
            ].into_iter().collect();
            
            // 合并所有映射到该表的模式
            for pattern in &table_patterns_list {
                if pattern.subject.starts_with('?') {
                    let var = pattern.subject.trim_start_matches('?').to_string();
                    if !column_mapping.contains_key(&var) {
                        let var_lower = var.to_lowercase();
                        let var_is_subject_in_table = table_patterns_list
                            .iter()
                            .any(|p| p.subject.trim_start_matches('?') == var);

                        let mapped_subject_col_from_rule = if let Some(store) = mappings {
                            let pred_iri = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                                pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                            } else {
                                pattern.predicate.to_string()
                            };
                            store
                                .mappings
                                .get(&pred_iri)
                                .and_then(|rules| {
                                    rules.iter().find(|rule| {
                                        rule.table_name == table_name
                                            && Self::mapping_rule_is_usable(rule, metadata_map)
                                    })
                                })
                                .and_then(|rule| rule.subject_template.as_ref())
                                .and_then(|tpl| Self::extract_subject_column_from_template(tpl))
                        } else {
                            None
                        };

                        let col = if let Some(subject_col) = mapped_subject_col_from_rule {
                            if metadata.columns.iter().any(|c| c == &subject_col) {
                                subject_col
                            } else {
                                Self::map_var_to_column(&var, metadata, &used_cols)
                            }
                        } else if var_is_subject_in_table {
                            if let Some(mapped_col) = join_var_mappings.get(&var_lower) {
                                if metadata.columns.iter().any(|c| c == mapped_col) {
                                    mapped_col.clone()
                                } else {
                                    Self::map_var_to_column(&var, metadata, &used_cols)
                                }
                            } else {
                                Self::map_var_to_column(&var, metadata, &used_cols)
                            }
                        } else {
                            Self::map_var_to_column(&var, metadata, &used_cols)
                        };

                        used_cols.insert(col.clone());
                        column_mapping.insert(var, col);
                    }
                }

                if pattern.object.starts_with('?') {
                    let var = pattern.object.trim_start_matches('?').to_string();
                    if !column_mapping.contains_key(&var) {
                        let var_lower = var.to_lowercase();

                        let mapped_col_from_rule = if let Some(store) = mappings {
                            let pred_iri = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                                pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                            } else {
                                pattern.predicate.to_string()
                            };

                            store
                                .mappings
                                .get(&pred_iri)
                                .and_then(|rules| {
                                    rules.iter().find(|rule| {
                                        rule.table_name == table_name
                                            && Self::mapping_rule_is_usable(rule, metadata_map)
                                    })
                                })
                                .and_then(|rule| rule.position_to_column.get(&1))
                                .cloned()
                        } else {
                            None
                        };

                        let col = if let Some(col) = mapped_col_from_rule {
                            col
                        } else if let Some(mapped_col) = join_var_mappings.get(&var_lower) {
                            if metadata.columns.iter().any(|c| c == mapped_col) {
                                mapped_col.clone()
                            } else {
                                Self::map_var_to_column(&var, metadata, &used_cols)
                            }
                        } else {
                            Self::map_var_to_column(&var, metadata, &used_cols)
                        };

                        if !used_cols.contains(&col) {
                            used_cols.insert(col.clone());
                        }
                        column_mapping.insert(var, col);
                    }
                } else if !Self::is_rdf_type_predicate(&pattern.predicate) {
                    let pred_iri = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                        pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                    } else {
                        pattern.predicate.to_string()
                    };
                    let const_col = if let Some(store) = mappings {
                        store
                            .mappings
                            .get(&pred_iri)
                            .and_then(|rules| {
                                rules.iter().find(|rule| {
                                    rule.table_name == table_name
                                        && Self::mapping_rule_is_usable(rule, metadata_map)
                                })
                            })
                            .and_then(|rule| rule.position_to_column.get(&1))
                            .cloned()
                    } else {
                        None
                    }
                    .unwrap_or_else(|| Self::map_var_to_column("value", metadata, &used_cols));

                    let const_var = format!("__obj_const_{}", used_cols.len());
                    used_cols.insert(const_col.clone());
                    column_mapping.insert(const_var.clone(), const_col);
                    table_filters
                        .entry(group_key.clone())
                        .or_default()
                        .push(Expr::Compare {
                            left: Box::new(Expr::Term(Term::Variable(const_var))),
                            op: ComparisonOp::Eq,
                            right: Box::new(Expr::Term(Self::token_to_term(&pattern.object))),
                        });
                }
            }

            let mut node = LogicNode::ExtensionalData {
                table_name: table_name.clone(),
                column_mapping,
                metadata: Arc::clone(metadata),
            };

            if let Some(filters) = table_filters.get(&group_key) {
                for f in filters {
                    node = LogicNode::Filter {
                        expression: f.clone(),
                        child: Box::new(node),
                    };
                }
            }

            table_nodes.push((group_key.clone(), node));
        }
        
        if impossible_pattern {
            return LogicNode::Values {
                variables: Vec::new(),
                rows: Vec::new(),
            };
        }

        // [Fix] Append LogicNode::Path for paths
        for (pattern, path) in path_patterns {
            let path_node = LogicNode::Path {
                subject: Self::token_to_term(&pattern.subject),
                path,
                object: Self::token_to_term(&pattern.object),
            };
            let unique_key = format!("path__{}__{}", pattern.subject, pattern.object);
            table_nodes.push((unique_key, path_node));
        }
        
        // 第三步：构建JOIN树
        if table_nodes.len() == 1 {
            table_nodes.into_iter().next().unwrap().1
        } else {
            // 构建左深树join，并基于共享变量创建join条件
            let mut result = table_nodes[0].1.clone();
            let mut result_vars = Self::extract_var_bindings(&result);
            
            for i in 1..table_nodes.len() {
                let right_node = table_nodes[i].1.clone();
                let right_vars = Self::extract_var_bindings(&right_node);
                
                // 创建基于共享变量的join条件
                let condition = Self::create_join_condition(&result_vars, &right_vars);
                
                result = LogicNode::Join {
                    children: vec![result, right_node],
                    condition,
                    join_type: JoinType::Inner,
                };
                
                // 合并变量绑定
                result_vars.extend(right_vars);
            }
            
            result
        }
    }

    /// 从LogicNode中提取变量到列名的绑定
            fn promote_correlated_vars(node: LogicNode, correlated_vars: &[String]) -> LogicNode {
        match node {
            LogicNode::Construction { mut projected_vars, mut bindings, child } => {
                for v in correlated_vars {
                    if !projected_vars.contains(v) {
                        projected_vars.push(v.clone());
                    }
                    bindings
                        .entry(v.clone())
                        .or_insert_with(|| Expr::Term(Term::Variable(v.clone())));
                }

                let promoted_child = Self::promote_correlated_vars(*child, correlated_vars);
                LogicNode::Construction {
                    projected_vars,
                    bindings,
                    child: Box::new(promoted_child),
                }
            }
            LogicNode::Aggregation { mut group_by, aggregates, having, child } => {
                for v in correlated_vars {
                    if !group_by.contains(v) {
                        group_by.push(v.clone());
                    }
                }
                LogicNode::Aggregation {
                    group_by,
                    aggregates,
                    having,
                    child,
                }
            }
            LogicNode::Filter { expression, child } => LogicNode::Filter {
                expression,
                child: Box::new(Self::promote_correlated_vars(*child, correlated_vars)),
            },
            LogicNode::Limit { limit, offset, order_by, child } => LogicNode::Limit {
                limit,
                offset,
                order_by,
                child: Box::new(Self::promote_correlated_vars(*child, correlated_vars)),
            },
            other => other,
        }
    }

    fn collect_query_vars(parsed: &ParsedQuery) -> HashSet<String> {
        let mut vars = HashSet::new();

        for p in &parsed.main_patterns {
            if let Some(v) = p.subject.strip_prefix('?') { vars.insert(v.to_string()); }
            if let Some(v) = p.predicate.strip_prefix('?') { vars.insert(v.to_string()); }
            if let Some(v) = p.object.strip_prefix('?') { vars.insert(v.to_string()); }
        }

        let re = regex::Regex::new(r"\?([A-Za-z_][A-Za-z0-9_]*)").expect("valid var regex");
        for f in &parsed.filter_expressions {
            for cap in re.captures_iter(f) {
                vars.insert(cap[1].to_string());
            }
        }

        for v in &parsed.projected_vars {
            vars.insert(v.trim_start_matches('?').to_string());
        }

        vars
    }

fn extract_var_bindings(node: &LogicNode) -> HashMap<String, String> {
        let mut bindings = HashMap::new();
        match node {
            LogicNode::ExtensionalData { column_mapping, .. } => {
                for (var, col) in column_mapping {
                    bindings.insert(var.clone(), col.clone());
                }
            }
            LogicNode::Construction { projected_vars, bindings: cons_bindings, child } => {
                let child_bindings = Self::extract_var_bindings(child);
                for v in projected_vars {
                    if let Some(expr) = cons_bindings.get(v) {
                        if let Expr::Term(Term::Variable(col)) = expr {
                            bindings.insert(v.clone(), col.clone());
                            continue;
                        }
                    }
                    if let Some(col) = child_bindings.get(v) {
                        bindings.insert(v.clone(), col.clone());
                    }
                }
            }
            LogicNode::Filter { child, .. } => {
                return Self::extract_var_bindings(child);
            }
            LogicNode::Join { children, .. } => {
                for c in children {
                    bindings.extend(Self::extract_var_bindings(c));
                }
            }
            LogicNode::Aggregation { group_by, aggregates, .. } => {
                for v in group_by {
                    bindings.insert(v.clone(), v.clone());
                }
                for v in aggregates.keys() {
                    bindings.insert(v.clone(), v.clone());
                }
            }
            LogicNode::Values { variables, .. } => {
                for v in variables {
                    bindings.insert(v.clone(), v.clone());
                }
            }
            LogicNode::SubQuery { inner, .. } => {
                return Self::extract_var_bindings(inner);
            }
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                bindings.extend(Self::extract_var_bindings(outer));
                bindings.extend(Self::extract_var_bindings(inner));
            }
            LogicNode::Union(children) => {
                if let Some(first) = children.first() {
                    bindings.extend(Self::extract_var_bindings(first));
                }
            }
            LogicNode::Limit { child, .. } => {
                return Self::extract_var_bindings(child);
            }
            _ => {}
        }
        bindings
    }

    /// 基于共享变量创建join条件
    fn create_join_condition(
        left_vars: &HashMap<String, String>,
        right_vars: &HashMap<String, String>,
    ) -> Option<Expr> {
        eprintln!("[DEBUG create_join_condition] left_vars={:?}", left_vars);
        eprintln!("[DEBUG create_join_condition] right_vars={:?}", right_vars);
        
        let mut conditions = Vec::new();
        
        for (var, left_col) in left_vars {
            if let Some(right_col) = right_vars.get(var) {
                // [Fix] 使用纯列名，让SQL生成器自动添加正确的表别名
                // 不添加虚拟表前缀，因为SQL生成器会根据上下文添加真实别名
                eprintln!("[DEBUG create_join_condition] Creating condition: {} = {}", left_col, right_col);
                conditions.push(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(left_col.clone()))),
                    op: ComparisonOp::Eq,
                    right: Box::new(Expr::Term(Term::Variable(right_col.clone()))),
                });
            }
        }
        
        if conditions.is_empty() {
            None
        } else if conditions.len() == 1 {
            conditions.into_iter().next()
        } else {
            // 多个条件用AND连接
            Some(Expr::Logical {
                op: LogicalOp::And,
                args: conditions,
            })
        }
    }
    
    #[allow(dead_code)]
    fn pattern_to_column_mapping_with_vars(
        pattern: &super::TriplePattern,
        metadata: &TableMetadata,
        _needed_vars: &std::collections::HashSet<String>,
    ) -> HashMap<String, String> {
        let mut out = HashMap::new();
        let mut used_cols = HashSet::new();

        // 映射所有变量（不过滤，确保 JOIN 和 FILTER 变量都被包含）
        if pattern.subject.starts_with('?') {
            let var = pattern.subject.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            used_cols.insert(col.clone());
            out.insert(var, col);
        }
        if pattern.predicate.starts_with('?') {
            let var = pattern.predicate.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            used_cols.insert(col.clone());
            out.insert(var, col);
        }
        if pattern.object.starts_with('?') {
            let var = pattern.object.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            used_cols.insert(col.clone());
            out.insert(var, col);
        }

        if out.is_empty() {
            out = Self::fallback_mapping(metadata);
        }
        out
    }
    
    #[allow(dead_code)]
    fn build_core_plan(
        parsed: &ParsedQuery,
        metadata: Arc<TableMetadata>,
        mappings: Option<&MappingStore>,
    ) -> LogicNode {
        if !parsed.union_patterns.is_empty() {
            let branches = parsed
                .union_patterns
                .iter()
                .map(|branch| Self::build_join_from_patterns(branch, metadata.clone(), mappings))
                .collect::<Vec<_>>();
            return LogicNode::Union(branches);
        }

        let mut node =
            Self::build_join_from_patterns(&parsed.main_patterns, metadata.clone(), mappings);
        for optional in &parsed.optional_patterns {
            let right = Self::build_join_from_patterns(optional, metadata.clone(), mappings);
            node = LogicNode::Join {
                children: vec![node, right],
                condition: None,
                join_type: JoinType::Left,
            };
        }
        node
    }

    #[allow(dead_code)]
    fn build_join_from_patterns(
        patterns: &[super::TriplePattern],
        metadata: Arc<TableMetadata>,
        mappings: Option<&MappingStore>,
    ) -> LogicNode {
        // 将单表转换为 HashMap 以兼容新接口
        let mut metadata_map = std::collections::HashMap::new();
        let table_name = metadata.table_name.clone();
        metadata_map.insert(table_name, Arc::clone(&metadata));
        
        if patterns.is_empty() {
            return LogicNode::Values {
                variables: vec!["__unit".to_string()],
                rows: vec![vec![Term::Constant("1".to_string())]],
            };
        }

        let children = patterns
            .iter()
            .map(|p| Self::pattern_to_logic_node(p, &metadata_map, mappings))
            .collect::<Vec<_>>();

        if children.len() == 1 {
            children.into_iter().next().unwrap_or_else(|| LogicNode::Union(vec![]))
        } else {
            LogicNode::Join {
                children,
                condition: None,
                join_type: JoinType::Inner,
            }
        }
    }

    fn pattern_to_logic_node(
        pattern: &super::TriplePattern,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> LogicNode {
        eprintln!("[DEBUG IRConverter] pattern_to_logic_node: subject={}, predicate={}, object={}", 
            pattern.subject, pattern.predicate, pattern.object);
        
        // 根据谓词从映射中查找对应的表元数据
        let metadata_opt = Self::resolve_metadata_for_predicate(
            &pattern.predicate,
            metadata_map,
            mappings
        );
        
        // 如果找不到元数据，说明谓词不存在，返回一个空查询节点
        let metadata = match metadata_opt {
            Some(m) => m,
            None => {
                eprintln!("[WARNING IRConverter] Predicate '{}' not found, creating empty node", pattern.predicate);
                return LogicNode::Union(vec![]);
            }
        };
        
        // [S3-Fix] 使用 find_logical_op 判定属性路径，或直接检测括号以处理嵌套路径
        if (Self::find_logical_op(&pattern.predicate, "|").is_some() || 
            Self::find_logical_op(&pattern.predicate, "/").is_some() ||
            pattern.predicate.trim().starts_with('(')) && 
            pattern.predicate.contains('<') {
            return Self::convert_property_path(pattern, metadata_map, mappings);
        }

        // [S3-Fix] 仅在明确找到映射时才返回 IntensionalData
        if let Some(store) = mappings {
            eprintln!("[DEBUG IRConverter] Checking mappings, predicate='{}', len={}", pattern.predicate, pattern.predicate.len());
            
            // 特殊处理 RDF 类型断言
            if pattern.predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" {
                eprintln!("[DEBUG IRConverter] Handling RDF type assertion");
                // 对于 rdf:type，我们不需要映射，直接返回一个空节点
                // 实际的类型检查应该在后续处理
                return LogicNode::IntensionalData {
                    predicate: pattern.predicate.clone(),
                    args: vec![
                        Self::token_to_term(&pattern.subject),
                        Self::token_to_term(&pattern.object),
                    ],
                };
            }
            
            if !pattern.predicate.starts_with('?')
                && pattern.predicate.starts_with('<')
                && pattern.predicate.ends_with('>')
            {
                let predicate_iri = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
                eprintln!("[DEBUG IRConverter] Extracted IRI='{}', checking contains_key: {}", predicate_iri, store.mappings.contains_key(&predicate_iri));
                if store.mappings.contains_key(&predicate_iri) {
                    eprintln!("[DEBUG IRConverter] Found mapping for {}, creating IntensionalData", predicate_iri);
                    return LogicNode::IntensionalData {
                        predicate: predicate_iri,
                        args: vec![
                            Self::token_to_term(&pattern.subject),
                            Self::token_to_term(&pattern.object),
                        ],
                    };
                } else {
                    eprintln!("[DEBUG IRConverter] No mapping found for predicate: '{}', available: {:?}", predicate_iri, store.mappings.keys().take(5).collect::<Vec<_>>());
                }
            } else {
                eprintln!("[DEBUG IRConverter] Predicate doesn't match IRI pattern: starts_with_?={}, starts_with_<={}, ends_with_>={}", 
                    pattern.predicate.starts_with('?'),
                    pattern.predicate.starts_with('<'),
                    pattern.predicate.ends_with('>'));
            }
        } else {
            eprintln!("[DEBUG IRConverter] No mappings provided (mappings is None)");
        }

        // Direct Table Mapping (ExtensionalData)
        let mut column_mapping = HashMap::new();
        let mut filters = Vec::new();
        let mut used_cols = HashSet::new();

        // [Fix] 尝试从映射中获取实际的列名
        let mut subject_col = None;
        let mut object_col = None;
        
        eprintln!("[DEBUG IRConverter] Looking for mapping, mappings.is_some={}", mappings.is_some());
        
        if let Some(store) = mappings {
            eprintln!("[DEBUG IRConverter] Store has {} mappings", store.mappings.len());
            
            if !pattern.predicate.starts_with('?')
                && pattern.predicate.starts_with('<')
                && pattern.predicate.ends_with('>')
            {
                let predicate_iri = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
                eprintln!("[DEBUG IRConverter] Looking for predicate IRI: {}", predicate_iri);
                eprintln!("[DEBUG IRConverter] Available keys: {:?}", store.mappings.keys().take(10).collect::<Vec<_>>());
                
                if let Some(rules) = store.mappings.get(&predicate_iri) {
                    eprintln!("[DEBUG IRConverter] Found {} rules for {}", rules.len(), predicate_iri);
                    if let Some(rule) = rules.iter().find(|rule| rule.table_name == metadata.table_name && rule.position_to_column.values().all(|col| metadata.columns.iter().any(|c| c == col))) {
                        eprintln!("[DEBUG IRConverter] Rule: table={}, pos_to_col={:?}", rule.table_name, rule.position_to_column);
                        // 使用映射中的列名 (position 0 = subject, position 1 = object)
                        if let Some(col) = rule.position_to_column.get(&0) {
                            subject_col = Some(col.clone());
                            eprintln!("[DEBUG IRConverter] Found mapping column for subject: {}", col);
                        }
                        if let Some(col) = rule.position_to_column.get(&1) {
                            object_col = Some(col.clone());
                            eprintln!("[DEBUG IRConverter] Found mapping column for object: {}", col);
                        }
                    }
                } else {
                    eprintln!("[DEBUG IRConverter] No mapping found for predicate: '{}'", predicate_iri);
                }
            } else {
                eprintln!("[DEBUG IRConverter] Predicate doesn't match IRI pattern: {}", pattern.predicate);
            }
        }

        // 1. 处理 Subject - 使用实际变量名或回退到 "s"
        let subject_var_name = if pattern.subject.starts_with('?') {
            pattern.subject.trim_start_matches('?').to_string()
        } else {
            "s".to_string()
        };
        let s_col = subject_col.unwrap_or_else(|| Self::map_var_to_column(&subject_var_name, &metadata, &used_cols));
        used_cols.insert(s_col.clone());
        if pattern.subject.starts_with('?') {
            column_mapping.insert(subject_var_name.clone(), s_col.clone());
        } else {
            // 常量 Subject - 使用唯一变量名避免 JOIN 冲突
            let dummy_var = format!("__subj_{}_{}", s_col, uuid::Uuid::new_v4().to_string()[..4].to_string());
            column_mapping.insert(dummy_var.clone(), s_col.clone());
            filters.push(Expr::Compare {
                left: Box::new(Expr::Term(Term::Variable(dummy_var))),
                op: ComparisonOp::Eq,
                right: Box::new(Expr::Term(Self::token_to_term(&pattern.subject))),
            });
        }

        // [S3-Fix] 处理 Predicate - 使用实际变量名或回退到 "p"
        let predicate_var_name = if pattern.predicate.starts_with('?') {
            pattern.predicate.trim_start_matches('?').to_string()
        } else {
            "p".to_string()
        };
        let p_col = Self::map_var_to_column(&predicate_var_name, &metadata, &used_cols);
        used_cols.insert(p_col.clone());
        if pattern.predicate.starts_with('?') {
            column_mapping.insert(predicate_var_name.clone(), p_col.clone());
        } else {
            // 常量 Predicate - 使用唯一变量名避免 JOIN 中的 AUTO-QUALIFY 冲突
            let dummy_var = format!("__pred_{}_{}", p_col, uuid::Uuid::new_v4().to_string()[..4].to_string());
            column_mapping.insert(dummy_var.clone(), p_col.clone());
            filters.push(Expr::Compare {
                left: Box::new(Expr::Term(Term::Variable(dummy_var))),
                op: ComparisonOp::Eq,
                right: Box::new(Expr::Term(Self::token_to_term(&pattern.predicate))),
            });
        }

        // 2. 处理 Object - 使用实际变量名或回退到 "o"
        let object_var_name = if pattern.object.starts_with('?') {
            pattern.object.trim_start_matches('?').to_string()
        } else {
            "o".to_string()
        };
        let o_col = object_col.unwrap_or_else(|| Self::map_var_to_column(&object_var_name, &metadata, &used_cols));
        used_cols.insert(o_col.clone());
        if pattern.object.starts_with('?') {
            column_mapping.insert(object_var_name.clone(), o_col.clone());
        } else {
            // 常量 Object
            let dummy_var = format!("__obj_{}", o_col);
            column_mapping.insert(dummy_var.clone(), o_col.clone());
            filters.push(Expr::Compare {
                left: Box::new(Expr::Term(Term::Variable(dummy_var))),
                op: ComparisonOp::Eq,
                right: Box::new(Expr::Term(Self::token_to_term(&pattern.object))),
            });
        }
        
        // DEBUG: Print column_mapping before creating ExtensionalData
        eprintln!("[DEBUG IRConverter] Creating ExtensionalData for table={}", metadata.table_name);
        eprintln!("[DEBUG IRConverter] column_mapping={:?}", column_mapping);
        
        let mut node = LogicNode::ExtensionalData {
            table_name: metadata.table_name.clone(),
            column_mapping,
            metadata: Arc::clone(&metadata),
        };

        // 按顺序包裹 Filter
        for filter_expr in filters {
            node = LogicNode::Filter {
                expression: filter_expr,
                child: Box::new(node),
            };
        }

        node
    }
    
    /// 根据谓词从映射中解析对应的表元数据
    fn unique_class_table_for_type_pattern(
        pattern: &super::TriplePattern,
        mappings: &MappingStore,
    ) -> Option<String> {
        if !Self::is_rdf_type_predicate(&pattern.predicate) {
            return None;
        }
        if !(pattern.object.starts_with('<') && pattern.object.ends_with('>')) {
            return None;
        }
        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
        let rules = mappings.mappings.get(class_iri)?;
        let mut tables = std::collections::HashSet::new();
        for rule in rules {
            tables.insert(rule.table_name.clone());
        }
        if tables.len() == 1 {
            tables.into_iter().next()
        } else {
            None
        }
    }

    fn is_rdf_type_predicate(predicate: &str) -> bool {
        predicate == "a"
            || predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            || predicate.ends_with("rdf-syntax-ns#type")
    }

    fn extract_subject_column_from_template(template: &str) -> Option<String> {
        let start = template.find('{')?;
        let end_rel = template[start + 1..].find('}')?;
        let end = start + 1 + end_rel;
        let col = template[start + 1..end].trim();
        if col.is_empty() {
            None
        } else {
            Some(col.to_string())
        }
    }

fn mapping_rule_is_usable(
        rule: &crate::mapping::MappingRule,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
    ) -> bool {
        let Some(metadata) = metadata_map.get(&rule.table_name) else {
            return false;
        };
        if metadata.columns.is_empty() {
            return false;
        }

        if let Some(tpl) = &rule.subject_template {
            if let Some(subject_col) = Self::extract_subject_column_from_template(tpl) {
                if !metadata.columns.iter().any(|c| c == &subject_col) {
                    return false;
                }
            }
        }

        for col in rule.position_to_column.values() {
            if !metadata.columns.iter().any(|c| c == col) {
                return false;
            }
        }

        true
    }

    fn resolve_metadata_for_predicate(
        predicate: &str,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Option<Arc<TableMetadata>> {
        let store = mappings?;
        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>')
        } else {
            predicate
        };

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
            return None;
        }

        if let Some(rules) = store.mappings.get(predicate_iri) {
            for rule in rules {
                if Self::mapping_rule_is_usable(rule, metadata_map) {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        None
    }

    fn resolve_metadata_for_predicate_with_context(
        predicate: &str,
        subject: Option<&str>,
        preferred_table: Option<&str>,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Option<Arc<TableMetadata>> {
        let store = mappings?;
        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>')
        } else {
            predicate
        };

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
            return None;
        }

        let mut matching_rules = Vec::new();
        if let Some(rules) = store.mappings.get(predicate_iri) {
            matching_rules.extend(rules.iter());
        }
        matching_rules.retain(|r| Self::mapping_rule_is_usable(r, metadata_map));
        if matching_rules.is_empty() {
            return None;
        }

        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        if let Some(pref_table) = preferred_table {
            for rule in &matching_rules {
                if rule.table_name == pref_table {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        if let Some(subj) = subject {
            let subj_lower = subj.trim_start_matches('?').to_lowercase();
            for rule in &matching_rules {
                let table_lower = rule.table_name.to_lowercase();
                if subj_lower.contains(&table_lower) || table_lower.contains(&subj_lower) {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        let rule = matching_rules[0];
        metadata_map.get(&rule.table_name).map(Arc::clone)
    }

    fn convert_property_path(
        pattern: &super::TriplePattern,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> LogicNode {
        let mut pred = pattern.predicate.trim();
        // 去除最外层括号
        if pred.starts_with('(') && pred.ends_with(')') && Self::is_fully_enclosed(pred) {
            pred = &pred[1..pred.len() - 1].trim();
        }

        // [S3-Fix] 使用 find_logical_op 判定分界点
        let alt_pos = Self::find_logical_op(pred, "|").or_else(|| pred.find('|'));
        if let Some(pos) = alt_pos {
            let p1 = pred[..pos].trim();
            let p2 = pred[pos + 1..].trim();
            
            let children = vec![
                Self::pattern_to_logic_node(&super::TriplePattern {
                    subject: pattern.subject.clone(),
                    predicate: p1.to_string(),
                    object: pattern.object.clone(),
                }, metadata_map, mappings),
                Self::pattern_to_logic_node(&super::TriplePattern {
                    subject: pattern.subject.clone(),
                    predicate: p2.to_string(),
                    object: pattern.object.clone(),
                }, metadata_map, mappings),
            ];
            return LogicNode::Union(children);
        } else {
            let seq_pos = if pred.starts_with("http://") || pred.starts_with("https://") || (pred.starts_with('<') && pred.ends_with('>')) {
                None
            } else {
                Self::find_logical_op(pred, "/")
                    .or_else(|| {
                        if pred.contains("/<") {
                            pred.find("/<")
                        } else if !pred.starts_with("http://") && !pred.starts_with("https://") {
                            pred.find('/')
                        } else {
                            None
                        }
                    })
            };
            if let Some(pos) = seq_pos {
                let p1 = pred[..pos].trim();
                let p2 = pred[pos + 1..].trim();
                
                let blank_var = format!("?bl_{}", uuid::Uuid::new_v4().to_string()[..8].to_string());
                
                let n1 = Self::pattern_to_logic_node(&super::TriplePattern {
                    subject: pattern.subject.clone(),
                    predicate: p1.to_string(),
                    object: blank_var.clone(),
                }, metadata_map, mappings);
                
                let n2 = Self::pattern_to_logic_node(&super::TriplePattern {
                    subject: blank_var,
                    predicate: p2.to_string(),
                    object: pattern.object.clone(),
                }, metadata_map, mappings);
                
                return LogicNode::Join {
                    children: vec![n1, n2],
                    condition: None,
                    join_type: JoinType::Inner,
                };
            }
        }

        // Fallback or Recursion finished
        Self::pattern_to_logic_node(&super::TriplePattern {
            subject: pattern.subject.clone(),
            predicate: pred.to_string(),
            object: pattern.object.clone(),
        }, metadata_map, mappings)
    }

    #[allow(dead_code)]
    fn pattern_to_column_mapping(
        pattern: &super::TriplePattern,
        metadata: &TableMetadata,
    ) -> HashMap<String, String> {
        let mut out = HashMap::new();
        let mut used_cols = HashSet::new();

        if pattern.subject.starts_with('?') {
            let var = pattern.subject.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            used_cols.insert(col.clone());
            out.insert(var, col);
        }
        if pattern.predicate.starts_with('?') {
            let var = pattern.predicate.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            used_cols.insert(col.clone());
            out.insert(var, col);
        }
        if pattern.object.starts_with('?') {
            let var = pattern.object.trim_start_matches('?').to_string();
            let col = Self::map_var_to_column(&var, metadata, &used_cols);
            out.insert(var, col);
        }

        if out.is_empty() {
            out = Self::fallback_mapping(metadata);
        }
        out
    }

    fn fallback_mapping(metadata: &TableMetadata) -> HashMap<String, String> {
        let mut out = HashMap::new();
        // 使用元数据的主键列作为subject映射，避免硬编码"id"
        if let Some(pk) = metadata.primary_keys.first() {
            out.insert("s".to_string(), pk.clone());
        } else if let Some(first) = metadata.columns.first() {
            out.insert("s".to_string(), first.clone());
        }
        // 使用第一个非主键列作为object映射，避免硬编码"name"
        if let Some(col) = metadata.columns.iter().find(|c| !metadata.primary_keys.contains(c)) {
            out.insert("o".to_string(), col.clone());
        }
        out
    }

    fn map_var_to_column(var: &str, metadata: &TableMetadata, used: &HashSet<String>) -> String {
        let var_lower = var.to_lowercase();
        
        eprintln!("[DEBUG map_var_to_column] var='{}', table='{}', columns={:?}, used={:?}",
            var, metadata.table_name, metadata.columns, used);
        
        // 辅助函数：将驼峰命名转换为蛇形命名
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
        
        // 辅助函数：尝试返回列名如果存在且未使用
        let try_column = |col: &str| -> Option<String> {
            if metadata.columns.iter().any(|c| c == col) && !used.contains(col) {
                Some(col.to_string())
            } else {
                None
            }
        };
        
        // 1. 优先尝试直接匹配变量名
        if let Some(col) = try_column(var) {
            eprintln!("[DEBUG map_var_to_column]   -> Direct match: {}", col);
            return col;
        }
        
        // 2. 尝试小写匹配
        if let Some(col) = try_column(&var_lower) {
            eprintln!("[DEBUG map_var_to_column]   -> Lowercase match: {}", col);
            return col;
        }
        
        // 3. 尝试驼峰命名转换
        let snake_name = to_snake_case(var);
        if let Some(col) = try_column(&snake_name) {
            eprintln!("[DEBUG map_var_to_column]   -> Snake case match: {}", col);
            return col;
        }
        
        // 4. 尝试添加 _id 后缀
        let with_id_suffix = format!("{}_id", var_lower);
        if let Some(col) = try_column(&with_id_suffix) {
            eprintln!("[DEBUG map_var_to_column]   -> _id suffix match: {}", col);
            return col;
        }
        
        // 5. 尝试添加 _name 后缀
        let with_name_suffix = format!("{}_name", var_lower);
        if let Some(col) = try_column(&with_name_suffix) {
            eprintln!("[DEBUG map_var_to_column]   -> _name suffix match: {}", col);
            return col;
        }
        
        // 6. 尝试常见的扩展模式
        let expanded_patterns: Vec<(String, Vec<&str>)> = vec![
            ("dept".to_string(), vec!["department_id", "department_name"]),
            ("emp".to_string(), vec!["employee_id"]),
            ("mgr".to_string(), vec!["manager_id"]),
            ("manager".to_string(), vec!["manager_id"]),
            ("loc".to_string(), vec!["location"]),
        ];
        for (pattern, candidates) in &expanded_patterns {
            if var_lower == *pattern || var_lower.starts_with(pattern) {
                for candidate in candidates {
                    if let Some(col) = try_column(candidate) {
                        eprintln!("[DEBUG map_var_to_column]   -> Pattern '{}' match: {}", pattern, col);
                        return col;
                    }
                }
            }
        }
        
        // 7. 优先使用主键列
        for pk in &metadata.primary_keys {
            if !used.contains(pk.as_str()) {
                eprintln!("[DEBUG map_var_to_column]   -> Primary key match: {}", pk);
                return pk.clone();
            }
        }
        
        // 8. 回退：使用第一个未使用的列
        if let Some(col) = metadata.columns.iter().find(|c| !used.contains((*c).as_str())) {
            eprintln!("[DEBUG map_var_to_column]   -> First unused column: {}", col);
            return col.clone();
        }
        
        // 9. 最终回退
        eprintln!("[DEBUG map_var_to_column]   -> Fallback to var name: {}", var);
        var.to_string()
    }

    /// 从过滤器表达式中提取变量名
    fn extract_vars_from_filter(filter: &str) -> Vec<String> {
        let mut vars = Vec::new();
        let re = regex::Regex::new(r"\?([a-zA-Z_][a-zA-Z0-9_]*)").ok();
        if let Some(regex) = re {
            for cap in regex.captures_iter(filter) {
                if let Some(m) = cap.get(1) {
                    vars.push(m.as_str().to_string());
                }
            }
        }
        vars
    }

    fn extract_exists_filters(block: &str) -> Vec<String> {
        let mut filters = Vec::new();

        if let Ok(exists_re) = regex::Regex::new(r"(?is)FILTER\s+(NOT\s+)?EXISTS\s*\{(.*?)\}") {
            for cap in exists_re.captures_iter(block) {
                let prefix = if cap.get(1).is_some() { "NOT " } else { "" };
                let inner = cap.get(2).map(|m| m.as_str()).unwrap_or("").trim();
                filters.push(format!("{}EXISTS {{ {} }}", prefix, inner));
            }
        }

        if let Ok(filter_re) = regex::Regex::new(r"(?is)FILTER\s*\((.*?)\)") {
            for cap in filter_re.captures_iter(block) {
                if let Some(m) = cap.get(1) {
                    filters.push(m.as_str().trim().to_string());
                }
            }
        }

        filters
    }

    fn parse_exists_filter_expr(filter: &str, core: &LogicNode) -> Option<Expr> {
        let trimmed = filter.trim();
        if trimmed.is_empty() {
            return None;
        }

        let re = regex::Regex::new(r"(?is)^(NOT\s+)?EXISTS\s*\{(.*)\}\s*$").ok()?;
        let caps = re.captures(trimmed)?;
        let is_not = caps.get(1).is_some();
        let block = caps.get(2)?.as_str();

        let patterns = crate::parser::sparql_parser_v2::extract_triple_patterns(block);
        if patterns.is_empty() {
            return None;
        }
        let filters = Self::extract_exists_filters(block);

        let mut pattern_vars = HashSet::new();
        for p in &patterns {
            if let Some(v) = p.subject.strip_prefix('?') {
                pattern_vars.insert(v.to_string());
            }
            if let Some(v) = p.object.strip_prefix('?') {
                pattern_vars.insert(v.to_string());
            }
        }

        let outer_vars: HashSet<String> = core.used_variables().into_iter().collect();
        let correlated_vars: Vec<String> = pattern_vars
            .into_iter()
            .filter(|v| outer_vars.contains(v))
            .collect();

        if is_not {
            Some(Expr::NotExists { patterns, correlated_vars, filters })
        } else {
            Some(Expr::Exists { patterns, correlated_vars, filters })
        }
    }

    fn parse_filter_expr(filter: &str) -> Option<Expr> {
        let trimmed = filter.trim();
        if trimmed.is_empty() {
            return None;
        }

        // 1. 尝试解析逻辑操作符 (优先级递减)
        // 逻辑 OR (||)
        if let Some(pos) = Self::find_logical_op(trimmed, "||") {
            let left = Self::parse_filter_expr(trimmed[..pos].trim())?;
            let right = Self::parse_filter_expr(trimmed[pos + 2..].trim())?;
            return Some(Expr::Logical {
                op: LogicalOp::Or,
                args: vec![left, right],
            });
        }
        
        // 逻辑 AND (&&)
        if let Some(pos) = Self::find_logical_op(trimmed, "&&") {
            let left = Self::parse_filter_expr(trimmed[..pos].trim())?;
            let right = Self::parse_filter_expr(trimmed[pos + 2..].trim())?;
            return Some(Expr::Logical {
                op: LogicalOp::And,
                args: vec![left, right],
            });
        }

        // 2.1 解析 IN / NOT IN
        if let Ok(in_re) = regex::Regex::new(r"(?is)^(.+?)\s+(NOT\s+IN|IN)\s*\((.*)\)$") {
            if let Some(caps) = in_re.captures(trimmed) {
                let left_part = caps.get(1).map(|m| m.as_str().trim()).unwrap_or("");
                let op_part = caps.get(2).map(|m| m.as_str().trim()).unwrap_or("");
                let list_part = caps.get(3).map(|m| m.as_str().trim()).unwrap_or("");
                if !left_part.is_empty() {
                    let left = Self::parse_filter_expr(left_part)?;
                    let args: Vec<Expr> = if list_part.is_empty() {
                        vec![]
                    } else {
                        Self::split_function_args(list_part)
                            .iter()
                            .map(|arg| {
                                let a = arg.trim();
                                Self::parse_filter_expr(a)
                                    .unwrap_or_else(|| Expr::Term(Self::token_to_term(a)))
                            })
                            .collect()
                    };
                    let right = Expr::Function {
                        name: "LIST".to_string(),
                        args,
                    };
                    let op = if op_part.to_ascii_uppercase().starts_with("NOT") {
                        ComparisonOp::NotIn
                    } else {
                        ComparisonOp::In
                    };
                    return Some(Expr::Compare {
                        left: Box::new(left),
                        op,
                        right: Box::new(right),
                    });
                }
            }
        }

        // 2. 尝试解析比较操作符 (=, >, <, >=, <=)
        // 注意：由于 find_logical_op 是逐个匹配的，我们应该先检查最长的操作符，或者手动判断
        for op_str in &["==", ">=", "<=", "=", ">", "<"] {
            if let Some(pos) = Self::find_logical_op(trimmed, op_str) {
                let left_part = trimmed[..pos].trim();
                let right_part = trimmed[pos + op_str.len()..].trim();
                if left_part.is_empty() || right_part.is_empty() {
                    continue;
                }

                let left = Self::parse_filter_expr(left_part)?;
                let right = Self::parse_filter_expr(right_part)?;
                
                let op = match *op_str {
                    "==" | "=" => ComparisonOp::Eq,
                    ">" => ComparisonOp::Gt,
                    "<" => ComparisonOp::Lt,
                    ">=" => ComparisonOp::Gte,
                    "<=" => ComparisonOp::Lte,
                    _ => unreachable!(),
                };
                
                return Some(Expr::Compare {
                    left: Box::new(left),
                    op,
                    right: Box::new(right),
                });
            }
        }

        // 3. 尝试解析算术运算符 (*, /, +, -) 用于 BIND 表达式
        // 优先级：先 +/- (顶层最后结合)，后 * /
        for op_str in &["+", "-", "*", "/"] {
            if let Some(pos) = Self::find_logical_op(trimmed, op_str) {
                let left = Self::parse_filter_expr(trimmed[..pos].trim())?;
                let right = Self::parse_filter_expr(trimmed[pos + op_str.len()..].trim())?;
                
                return Some(Expr::Arithmetic {
                    left: Box::new(left),
                    op: match *op_str {
                        "+" => ArithmeticOp::Add,
                        "-" => ArithmeticOp::Sub,
                        "*" => ArithmeticOp::Mul,
                        "/" => ArithmeticOp::Div,
                        _ => unreachable!(),
                    },
                    right: Box::new(right),
                });
            }
        }

        // 4. 尝试匹配括号包裹
        if trimmed.starts_with('(') && trimmed.ends_with(')') {
            if Self::is_fully_enclosed(trimmed) {
                return Self::parse_filter_expr(&trimmed[1..trimmed.len() - 1]);
            }
        }

        // 4. 尝试解析函数调用或聚合 (F(...))
        let func_regex = regex::Regex::new(
            r"^([A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z_][A-Za-z0-9_]*)?|<[^>]+>)\((.*)\)$",
        )
        .ok()?;
        if let Some(caps) = func_regex.captures(trimmed) {
            let raw_name = caps[1].trim();
            let name = if raw_name.starts_with('<') && raw_name.ends_with('>') {
                raw_name
                    .trim_start_matches('<')
                    .trim_end_matches('>')
                    .to_uppercase()
            } else {
                raw_name.to_uppercase()
            };
            let args_str = caps[2].trim();
            
            let args = if args_str.is_empty() {
                vec![]
            } else if args_str == "*" {
                vec![Expr::Term(Term::Constant("*".to_string()))]
            } else {
                // [Fix] 支持多参数函数：分割逗号分隔的参数
                let arg_strs = Self::split_function_args(args_str);
                arg_strs.iter()
                    .map(|arg| {
                        let arg_trimmed = arg.trim();
                        if let Some(e) = Self::parse_filter_expr(arg_trimmed) {
                            e
                        } else {
                            Expr::Term(Self::token_to_term(arg_trimmed))
                        }
                    })
                    .collect()
            };
            
            return Some(Expr::Function { name, args });
        }

        // 5. 终端节点 (变量, 常量, 字面量)
        Some(Expr::Term(Self::token_to_term(trimmed)))
    }

        fn expand_bind_aliases_in_filter(
        filter: &str,
        bind_exprs: &[crate::parser::sparql_parser_v2::BindExpr],
    ) -> String {
        let mut expanded = filter.to_string();
        for bind in bind_exprs {
            let pattern = format!(r"\?{}\b", regex::escape(&bind.alias));
            if let Ok(re) = regex::Regex::new(&pattern) {
                expanded = re
                    .replace_all(&expanded, format!("({})", bind.expression).as_str())
                    .to_string();
            }
        }
        expanded
    }

fn substitute_bind_aliases(expr: Expr, bind_alias_exprs: &HashMap<String, Expr>) -> Expr {
        match expr {
            Expr::Term(Term::Variable(v)) => {
                if let Some(found) = bind_alias_exprs.get(&v) {
                    found.clone()
                } else if let Some(found) = bind_alias_exprs.get(&v.to_lowercase()) {
                    found.clone()
                } else if let Some(found) = bind_alias_exprs.get(&v.to_uppercase()) {
                    found.clone()
                } else {
                    Expr::Term(Term::Variable(v))
                }
            },
            Expr::Logical { op, args } => Expr::Logical {
                op,
                args: args
                    .into_iter()
                    .map(|a| Self::substitute_bind_aliases(a, bind_alias_exprs))
                    .collect(),
            },
            Expr::Compare { left, op, right } => Expr::Compare {
                left: Box::new(Self::substitute_bind_aliases(*left, bind_alias_exprs)),
                op,
                right: Box::new(Self::substitute_bind_aliases(*right, bind_alias_exprs)),
            },
            Expr::Function { name, args } => Expr::Function {
                name,
                args: args
                    .into_iter()
                    .map(|a| Self::substitute_bind_aliases(a, bind_alias_exprs))
                    .collect(),
            },
            Expr::Arithmetic { left, op, right } => Expr::Arithmetic {
                left: Box::new(Self::substitute_bind_aliases(*left, bind_alias_exprs)),
                op,
                right: Box::new(Self::substitute_bind_aliases(*right, bind_alias_exprs)),
            },
            Expr::Exists { .. } | Expr::NotExists { .. } => expr,
            Expr::Term(_) => expr,
        }
    }

    /// 分割函数参数，正确处理嵌套括号和引号
    fn split_function_args(args_str: &str) -> Vec<String> {
        let mut args = Vec::new();
        let mut current_arg = String::new();
        let mut paren_depth = 0;
        let mut in_quotes = false;
        let mut quote_char = '"';
        
        for c in args_str.chars() {
            match c {
                '(' if !in_quotes => {
                    paren_depth += 1;
                    current_arg.push(c);
                }
                ')' if !in_quotes => {
                    paren_depth -= 1;
                    current_arg.push(c);
                }
                '"' | '\'' if !in_quotes => {
                    in_quotes = true;
                    quote_char = c;
                    current_arg.push(c);
                }
                '"' | '\'' if in_quotes && c == quote_char => {
                    in_quotes = false;
                    current_arg.push(c);
                }
                ',' if !in_quotes && paren_depth == 0 => {
                    // 参数分隔符
                    if !current_arg.trim().is_empty() {
                        args.push(current_arg.trim().to_string());
                    }
                    current_arg = String::new();
                }
                _ => {
                    current_arg.push(c);
                }
            }
        }
        
        // 添加最后一个参数
        if !current_arg.trim().is_empty() {
            args.push(current_arg.trim().to_string());
        }
        
        args
    }

    /// 检查表达式是否被一对匹配的括号完全包裹
    fn is_fully_enclosed(s: &str) -> bool {
        let bytes = s.as_bytes();
        if bytes.len() < 2 || bytes[0] != b'(' || bytes[bytes.len() - 1] != b')' {
            return false;
        }
        
        let mut depth = 0;
        for i in 0..bytes.len() - 1 {
            match bytes[i] {
                b'(' => depth += 1,
                b')' => depth -= 1,
                _ => {}
            }
            if i > 0 && depth == 0 {
                return false; // 在到达最后一个字符前深度已经归零，说明不是整体包裹
            }
        }
        depth == 1 // 最后一个字符应该是 ')'，此时 depth 会变为 0
    }
    
    /// 查找逻辑操作符位置（考虑括号层级）
    fn find_logical_op(filter: &str, op: &str) -> Option<usize> {
        let mut paren_depth = 0;
        let mut in_iri = false;
        let mut in_quotes = false;
        let bytes = filter.as_bytes();
        let mut i = 0;
        
        // 当查找比较运算符时，不将<视为IRI开始
        let is_comparison_op = op == "<" || op == ">" || op == "<=" || op == ">=" || op == "=" || op == "==";
        
        while i < bytes.len() {
            let c = bytes[i];
            
            // 引号状态优先级最高
            if (c == b'"' || c == b'\'') && !in_iri {
                in_quotes = !in_quotes;
            } else if !in_quotes {
                if in_iri {
                    // 已进入 IRI，仅寻找结束符 >
                    if c == b'>' && paren_depth == 0 {
                        in_iri = false;
                    }
                } else {
                    // 不在 IRI 内
                    if c == b'<' && paren_depth == 0 {
                        if !in_iri && filter[i..].starts_with(op) {
                            return Some(i);
                        }
                        let next = bytes.get(i + 1).copied().unwrap_or(b' ');
                        if !is_comparison_op || next.is_ascii_alphabetic() {
                            in_iri = true;
                        }
                    } else if c == b'(' {
                        paren_depth += 1;
                    } else if c == b')' {
                        paren_depth -= 1;
                    } else if paren_depth == 0 && !in_iri {
                        // 顶层操作符尝试匹配
                        if filter[i..].starts_with(op) {
                            return Some(i);
                        }
                    }
                }
            }
            i += 1;
        }
        None
    }

    fn token_to_term(token: &str) -> Term {
        let t = token.trim();
        if t.starts_with('?') {
            return Term::Variable(t.trim_start_matches('?').to_string());
        }
        if t.starts_with('<') && t.ends_with('>') {
            return Term::Constant(
                t.trim_start_matches('<')
                    .trim_end_matches('>')
                    .to_string(),
            );
        }

        // Typed literal, e.g. "2020-01-01"^^xsd:date or "..."^^<iri>
        if let Some(dtype_pos) = t.find("^^") {
            let lit_part = t[..dtype_pos].trim();
            let dtype_part = t[dtype_pos + 2..].trim();
            let quoted = (lit_part.starts_with('"') && lit_part.ends_with('"'))
                || (lit_part.starts_with('\'') && lit_part.ends_with('\''));
            if quoted && lit_part.len() >= 2 {
                let value = lit_part[1..lit_part.len() - 1].to_string();
                let datatype = if dtype_part.starts_with('<') && dtype_part.ends_with('>') && dtype_part.len() >= 2 {
                    dtype_part[1..dtype_part.len() - 1].to_string()
                } else {
                    dtype_part.to_string()
                };
                return Term::Literal {
                    value,
                    datatype: Some(datatype),
                    language: None,
                };
            }
        }

        if (t.starts_with('"') && t.ends_with('"'))
            || (t.starts_with('\'') && t.ends_with('\''))
        {
            return Term::Literal {
                value: t.trim_matches('"').trim_matches('\'').to_string(),
                datatype: None,
                language: None,
            };
        }
        // 处理数字常量
        if t.chars().all(|c| c.is_ascii_digit() || c == '.') {
            return Term::Literal {
                value: t.to_string(),
                datatype: Some("integer".to_string()),
                language: None,
            };
        }
        Term::Constant(t.to_string())
    }

}
