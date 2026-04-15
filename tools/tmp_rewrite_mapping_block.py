from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
pattern=r"\n\s*// 预定义连接变量到正确的列映射[\s\S]*?\n\s*\} else if !Self::is_rdf_type_predicate\(&pattern\.predicate\) \{"
replacement='''

              // 合并所有映射到该表的模式
              for pattern in &table_patterns_list {
                  if pattern.subject.starts_with('?') {
                      let var = pattern.subject.trim_start_matches('?').to_string();
                      if !column_mapping.contains_key(&var) {
                          let var_is_subject_in_table = table_patterns_list
                              .iter()
                              .any(|p| p.subject.trim_start_matches('?') == var);

                          let mapped_subject_col_from_rule = if let Some(store) = mappings {
                              let pred_iri_raw = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                                  pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                              } else {
                                  pattern.predicate.to_string()
                              };
                              let pred_iri = Self::normalize_predicate_iri_for_lookup(&pred_iri_raw);
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
                              Self::map_var_to_column(&var, metadata, &used_cols)
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
                          let mapped_col_from_rule = if let Some(store) = mappings {
                              let pred_iri_raw = if pattern.predicate.starts_with('<') && pattern.predicate.ends_with('>') {
                                  pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string()
                              } else {
                                  pattern.predicate.to_string()
                              };
                              let pred_iri = Self::normalize_predicate_iri_for_lookup(&pred_iri_raw);

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
                          } else {
                              Self::map_var_to_column(&var, metadata, &used_cols)
                          };

                          if !used_cols.contains(&col) {
                              used_cols.insert(col.clone());
                          }
                          column_mapping.insert(var, col);
                      }
                  } else if !Self::is_rdf_type_predicate(&pattern.predicate) {
'''
new, n = re.subn(pattern, replacement, text, count=1)
if n != 1:
    raise SystemExit(f'block replace failed: {n}')
p.write_text(new, encoding='utf-8')
print('rewrote mapping block cleanly')