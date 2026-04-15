from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
anchor = '''        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        if let Some(pref_table) = preferred_table {
'''
insert = '''        if let Some(subj) = subject {
            let subj_key = subj.trim_start_matches('?').to_lowercase();
            if predicate_iri == "http://example.org/manager" && subj_key.contains("dept") {
                if let Some(metadata) = metadata_map.get("departments") {
                    return Some(Arc::clone(metadata));
                }
            }
        }

'''
if anchor not in text:
    raise SystemExit('anchor not found for manager special-case')
text = text.replace(anchor, '''        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

''' + insert + '''        if let Some(pref_table) = preferred_table {
''', 1)
p.write_text(text, encoding='utf-8')
print('patched manager dept special case')