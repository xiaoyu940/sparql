from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
old='''                } else {
                    for var in &vars {
                        if let Some(v) = map.get(var) {
                            obj.insert(var.clone(), to_sparql_term(v.clone()));
                            continue;
                        }
                        let col_name = format!("col_{}", var);
                        if let Some(v) = map.get(&col_name) {
                            obj.insert(var.clone(), to_sparql_term(v.clone()));
                        }
                    }
                }
'''
new='''                } else {
                    for var in &vars {
                        let var_lower = var.to_ascii_lowercase();
                        let var_snake = var
                            .chars()
                            .enumerate()
                            .fold(String::new(), |mut acc, (i, c)| {
                                if c.is_ascii_uppercase() {
                                    if i > 0 {
                                        acc.push('_');
                                    }
                                    acc.push(c.to_ascii_lowercase());
                                } else {
                                    acc.push(c);
                                }
                                acc
                            });

                        let candidates = [
                            var.clone(),
                            format!("col_{}", var),
                            var_lower.clone(),
                            format!("col_{}", var_lower),
                            var_snake.clone(),
                            format!("col_{}", var_snake),
                        ];

                        let mut found: Option<serde_json::Value> = None;
                        for key in candidates {
                            if let Some(v) = map.get(&key) {
                                found = Some(v.clone());
                                break;
                            }
                        }

                        if found.is_none() {
                            for (k, v) in &map {
                                if k.eq_ignore_ascii_case(var) || k.eq_ignore_ascii_case(&format!("col_{}", var)) {
                                    found = Some(v.clone());
                                    break;
                                }
                            }
                        }

                        if let Some(v) = found {
                            obj.insert(var.clone(), to_sparql_term(v));
                        }
                    }
                }
'''
if old not in text:
    raise SystemExit('target block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched case-insensitive binding variable lookup')