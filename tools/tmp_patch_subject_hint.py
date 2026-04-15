from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
old = '''        if let Some(subj) = subject {
            let subj_lower = subj.trim_start_matches('?').to_lowercase();
            for rule in &matching_rules {
                let table_lower = rule.table_name.to_lowercase();
                if subj_lower.contains(&table_lower) || table_lower.contains(&subj_lower) {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }
'''
new = '''        if let Some(subj) = subject {
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
'''
if old not in text:
    raise SystemExit('subject heuristic block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched subject table hint heuristic')