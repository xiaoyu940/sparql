from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

# Add impossible flag and table_filters map
s=s.replace('''        let mut table_patterns: HashMap<String, Vec<&super::TriplePattern>> = HashMap::new();
        let mut table_metadata: HashMap<String, Arc<TableMetadata>> = HashMap::new();
        let mut subject_preferred_table: HashMap<String, String> = HashMap::new();
        let mut var_aliases: HashMap<String, String> = HashMap::new();''','''        let mut table_patterns: HashMap<String, Vec<&super::TriplePattern>> = HashMap::new();
        let mut table_metadata: HashMap<String, Arc<TableMetadata>> = HashMap::new();
        let mut table_filters: HashMap<String, Vec<Expr>> = HashMap::new();
        let mut subject_preferred_table: HashMap<String, String> = HashMap::new();
        let mut var_aliases: HashMap<String, String> = HashMap::new();
        let mut impossible_pattern = false;''',1)

old_meta='''            let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&canonical_subject_for_lookup),
                preferred_table,
                metadata_map,
                mappings
            );

            let metadata = metadata_opt.unwrap_or_else(|| {
                metadata_map.values().next().cloned().unwrap_or_else(|| Arc::new(TableMetadata::default()))
            });'''
new_meta='''            let metadata_opt = if Self::is_rdf_type_predicate(&pattern.predicate) {
                if let Some(store) = mappings {
                    Self::unique_class_table_for_type_pattern(pattern, store)
                        .and_then(|tbl| metadata_map.get(&tbl).cloned())
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
            };'''
if old_meta not in s:
    raise SystemExit('metadata resolve block not found')
s=s.replace(old_meta,new_meta,1)

# Add impossible early return before path append
marker='''        // [Fix] Append LogicNode::Path for paths'''
if marker in s and 'if impossible_pattern {' not in s[s.find('for pattern in &normal_patterns'):s.find(marker)]:
    s=s.replace(marker,'''        if impossible_pattern {
            return LogicNode::Values {
                variables: Vec::new(),
                rows: Vec::new(),
            };
        }

        // [Fix] Append LogicNode::Path for paths''',1)

# Add constant object handling and filter push in per-table loop
old_obj_block='''                if pattern.object.starts_with('?') {
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
                }'''
new_obj_block='''                if pattern.object.starts_with('?') {
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
                } else {
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
                }'''
if old_obj_block not in s:
    raise SystemExit('object block not found')
s=s.replace(old_obj_block,new_obj_block,1)

# apply filters to node
s=s.replace('''            let mut node = LogicNode::ExtensionalData {
                table_name: table_name.clone(),
                column_mapping,
                metadata: Arc::clone(metadata),
            };

            table_nodes.push((group_key.clone(), node));''','''            let mut node = LogicNode::ExtensionalData {
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

            table_nodes.push((group_key.clone(), node));''',1)

p.write_text(s,encoding='utf-8')
print('patched metadata resolution, impossible pattern handling, and object-constant filters')
