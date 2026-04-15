from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

old='''                if pattern.subject.starts_with('?') {
                    let var = pattern.subject.trim_start_matches('?').to_string();
                    let var_lower = var.to_lowercase();

                    // [Fix] 鍙湁褰撳彉閲忕‘瀹炰綔涓?subject 鍑虹幇鍦ㄦ琛ㄧ殑妯″紡涓椂锛屾墠浣跨敤 join_var_mappings
                    let var_is_subject_in_table = table_patterns_list.iter()
                        .any(|p| p.subject.trim_start_matches('?') == var);

                    let col = if var_is_subject_in_table {
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
                }'''
new='''                if pattern.subject.starts_with('?') {
                    let var = pattern.subject.trim_start_matches('?').to_string();
                    if !column_mapping.contains_key(&var) {
                        let var_lower = var.to_lowercase();

                        let mapped_subject_col_from_rule = if let Some(store) = mappings {
                            let pred_iri = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                                pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                            } else if !pattern.predicate.starts_with('?') && pattern.predicate.contains(':') {
                                pattern.predicate.to_string()
                            } else {
                                pattern.predicate.to_string()
                            };

                            store.mappings.get(&pred_iri)
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

                        let var_is_subject_in_table = table_patterns_list.iter()
                            .any(|p| p.subject.trim_start_matches('?') == var);

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
                }'''
if old not in s:
    raise SystemExit('subject block not found')
s=s.replace(old,new,1)

# avoid object var overwrite too
s=s.replace('''                if pattern.object.starts_with('?') {
                    let var = pattern.object.trim_start_matches('?').to_string();''','''                if pattern.object.starts_with('?') {
                    let var = pattern.object.trim_start_matches('?').to_string();
                    if column_mapping.contains_key(&var) {
                        continue;
                    }''',1)

p.write_text(s,encoding='utf-8')
print('patched stable subject mapping by rule subject_template and no remap overwrite')
