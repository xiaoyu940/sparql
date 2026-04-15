from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
text, n1 = re.subn(r"\}\s*else if var_is_subject_in_table \{[\s\S]*?\}\s*else \{", "} else if var_is_subject_in_table {\n                              Self::map_var_to_column(&var, metadata, &used_cols)\n                          } else {", text, count=1)
text, n2 = re.subn(r"\}\s*else if let Some\(mapped_col\) = join_var_mappings\.get\(&var_lower\) \{[\s\S]*?\}\s*else \{", "} else {", text, count=1)
text = text.replace('let join_var_mappings: HashMap<String, String> = [\n                ("dept".to_string(), "department_id".to_string()),\n                ("emp".to_string(), "employee_id".to_string()),\n                ("location".to_string(), "location".to_string()),\n            ].into_iter().collect();\n\n', '')
p.write_text(text,encoding='utf-8')
print('replacements',n1,n2)