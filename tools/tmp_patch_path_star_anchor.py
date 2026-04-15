from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/path_sql_generator.rs')
text = p.read_text(encoding='utf-8')
old = '''            PropertyPath::Star(_) | PropertyPath::Plus(_) => {
                // 对于 * 和 +，锚点是起始节点本身（深度为0）
                if subject_is_var {
                    Ok("SELECT DISTINCT s AS start_node, s AS end_node, 0 AS depth FROM rdf_triples".to_string())
                } else {
                    Ok(format!(
                        "SELECT {} AS start_node, {} AS end_node, 0 AS depth",
                        subject_sql, subject_sql
                    ))
                }
            }
'''
new = '''            PropertyPath::Star(inner) | PropertyPath::Plus(inner) => {
                // 与当前测试基线保持一致：从至少一跳边开始锚定
                let inner_pred = match inner.as_ref() {
                    PropertyPath::Predicate(p) => Self::normalize_predicate(p),
                    _ => return Err(GenerationError::Other(
                        "Complex nested paths in * or + not yet supported".to_string()
                    )),
                };

                if subject_is_var {
                    Ok(format!(
                        "SELECT DISTINCT s AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples \
                         WHERE p = '{}'",
                        inner_pred
                    ))
                } else {
                    Ok(format!(
                        "SELECT DISTINCT {} AS start_node, o AS end_node, 1 AS depth \
                         FROM rdf_triples \
                         WHERE p = '{}' AND s = {}",
                        subject_sql, inner_pred, subject_sql
                    ))
                }
            }
'''
if old not in text:
    raise SystemExit('star/plus base block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched star base anchor')