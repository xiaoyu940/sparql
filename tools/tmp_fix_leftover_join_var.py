from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''                          } else if var_is_subject_in_table {
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
''','''                          } else if var_is_subject_in_table {
                              Self::map_var_to_column(&var, metadata, &used_cols)
                          } else {
''',1)
text=text.replace('''                          } else if let Some(mapped_col) = join_var_mappings.get(&var_lower) {
                              if metadata.columns.iter().any(|c| c == mapped_col) {
                                  mapped_col.clone()
                              } else {
                                  Self::map_var_to_column(&var, metadata, &used_cols)
                              }
                          } else {
''','''                          } else {
''',1)
p.write_text(text,encoding='utf-8')
print('fixed leftover join_var_mappings refs')