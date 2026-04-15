from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/mapping/r2rml_loader.rs')
text=p.read_text(encoding='utf-8')
old='''                if rule.position_to_column.is_empty() {
                    errors.push(format!(
                        "Predicate '{}' has empty position_to_column",
                        predicate
                    ));
                }
'''
new='''                if rule.position_to_column.is_empty() {
                    // 允许 rr:class 断言映射：仅有 subject_template、无 object 列绑定
                    if rule.subject_template.is_none() {
                        errors.push(format!(
                            "Predicate '{}' has empty position_to_column",
                            predicate
                        ));
                    }
                }
'''
if old in text:
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched mapping validation to allow class assertion rules')