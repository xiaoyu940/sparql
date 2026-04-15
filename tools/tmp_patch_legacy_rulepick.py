from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''                if let Some(rules) = store.mappings.get(predicate_iri) {
                    if let Some(rule) = rules.first() {
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
                }'''
new='''                if let Some(rules) = store.mappings.get(predicate_iri) {
                    if let Some(rule) = rules.iter().find(|rule| {
                        if rule.table_name != metadata.table_name {
                            return false;
                        }
                        for col in rule.position_to_column.values() {
                            if !metadata.columns.iter().any(|c| c == col) {
                                return false;
                            }
                        }
                        true
                    }) {
                        eprintln!("[DEBUG IRConverter] Rule: table={}, pos_to_col={:?}", rule.table_name, rule.position_to_column);
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
                }'''
if old not in s:
    raise SystemExit('rules.first block in table-node builder not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched legacy table-node mapping rule pick by current metadata table and existing cols')
