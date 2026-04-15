from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')

# 1) function calls
text = text.replace(
    '.map(|branch| Self::build_join_from_patterns_with_vars(branch, metadata_map, mappings, &needed_vars, false))',
    '.map(|branch| Self::build_join_from_patterns_with_vars(branch, metadata_map, mappings, &needed_vars, false, None))',
    1
)
text = text.replace(
    'let mut node =\n            Self::build_join_from_patterns_with_vars(&parsed.main_patterns, metadata_map, mappings, &needed_vars, false);',
    'let mut node =\n            Self::build_join_from_patterns_with_vars(&parsed.main_patterns, metadata_map, mappings, &needed_vars, false, None);\n\n        let mut main_subject_hints: std::collections::HashMap<String, String> = std::collections::HashMap::new();\n        for p in &parsed.main_patterns {\n            if !p.subject.starts_with(\'?\') {\n                continue;\n            }\n            if let Some(meta) = Self::resolve_metadata_for_predicate(&p.predicate, metadata_map, mappings) {\n                let key = p.subject.trim_start_matches(\'?\').to_string();\n                main_subject_hints.entry(key).or_insert(meta.table_name.clone());\n            }\n        }',
    1
)
text = text.replace(
    'let right = Self::build_join_from_patterns_with_vars(optional, metadata_map, mappings, &needed_vars, true);',
    'let right = Self::build_join_from_patterns_with_vars(optional, metadata_map, mappings, &needed_vars, true, Some(&main_subject_hints));',
    1
)

# 2) signature
text = text.replace(
    'fn build_join_from_patterns_with_vars(\n        patterns: &[super::TriplePattern],\n        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,\n        mappings: Option<&MappingStore>,\n        needed_vars: &std::collections::HashSet<String>,\n        preserve_on_impossible: bool,\n    ) -> LogicNode {',
    'fn build_join_from_patterns_with_vars(\n        patterns: &[super::TriplePattern],\n        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,\n        mappings: Option<&MappingStore>,\n        _needed_vars: &std::collections::HashSet<String>,\n        preserve_on_impossible: bool,\n        subject_hints: Option<&std::collections::HashMap<String, String>>,\n    ) -> LogicNode {',
    1
)

# 3) init subject_preferred_table from hints
text = text.replace(
    'let mut subject_preferred_table: HashMap<String, String> = HashMap::new();',
    'let mut subject_preferred_table: HashMap<String, String> = subject_hints\n            .cloned()\n            .unwrap_or_default();',
    1
)

# 4) remove hardcoded join_var_mappings block and branches
text = text.replace(
'''            // 预定义连接变量到正确的列映射
            let join_var_mappings: HashMap<String, String> = [
                ("dept".to_string(), "department_id".to_string()),
                ("emp".to_string(), "employee_id".to_string()),
                ("location".to_string(), "location".to_string()),
            ].into_iter().collect();

''',
'',
1)

text = text.replace(
'''                          } else if var_is_subject_in_table {
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
''',
'''                          } else if var_is_subject_in_table {
                              Self::map_var_to_column(&var, metadata, &used_cols)
                          } else {
''',
1)

text = text.replace(
'''                          } else if let Some(mapped_col) = join_var_mappings.get(&var_lower) {
                              if metadata.columns.iter().any(|c| c == mapped_col) {
                                  mapped_col.clone()
                              } else {
                                  Self::map_var_to_column(&var, metadata, &used_cols)
                              }
                          } else {
''',
'''                          } else {
''',
1)

# remove now-unused var_lower declarations in two spots
text = text.replace('let var_lower = var.to_lowercase();\n', '', 2)

# 5) remove hardcoded manager special case and subject-name hints
text = text.replace(
'''        if let Some(subj) = subject {
            let subj_key = subj.trim_start_matches('?').to_lowercase();
            if predicate_iri == "http://example.org/manager" && subj_key.contains("dept") {
                if let Some(metadata) = metadata_map.get("departments") {
                    return Some(Arc::clone(metadata));
                }
            }
        }

''',
'',
1)

text = text.replace(
'''        if let Some(subj) = subject {
            let subj_lower = subj.trim_start_matches('?').to_lowercase();
            let mut hints = vec![subj_lower.clone()];
            if subj_lower.starts_with("dept") {
                hints.push("department".to_string());
            }
            if subj_lower.starts_with("emp") {
                hints.push("employee".to_string());
            }
            if subj_lower.starts_with("proj") {
                hints.push("project".to_string());
            }
            if subj_lower.starts_with("mgr") {
                hints.push("manager".to_string());
            }

            for rule in &matching_rules {
                let table_lower = rule.table_name.to_lowercase();
                if hints.iter().any(|h| h.contains(&table_lower) || table_lower.contains(h)) {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

''',
'',
1)

p.write_text(text, encoding='utf-8')
print('patched generic subject hints + removed hardcoded table-name heuristics')