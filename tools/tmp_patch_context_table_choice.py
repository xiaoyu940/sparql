from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')

insert_after = '''    fn normalize_predicate_iri_for_lookup(iri: &str) -> String {
        let expanded = if let Some((prefix, local)) = iri.split_once(':') {
            if !local.is_empty() {
                match prefix {
                    "ex" => format!("http://example.org/{}", local),
                    "rdf" => format!("http://www.w3.org/1999/02/22-rdf-syntax-ns#{}", local),
                    "rdfs" => format!("http://www.w3.org/2000/01/rdf-schema#{}", local),
                    _ => iri.to_string(),
                }
            } else {
                iri.to_string()
            }
        } else {
            iri.to_string()
        };

        match expanded.as_str() {
            "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
            "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
            _ => expanded,
        }
    }
'''

helper = '''
    fn predicate_local_name(iri: &str) -> String {
        let raw = iri
            .rsplit(['#', '/', ':'])
            .next()
            .unwrap_or(iri)
            .trim();
        raw.chars()
            .map(|c| if c.is_ascii_alphanumeric() { c.to_ascii_lowercase() } else { '_' })
            .collect::<String>()
            .trim_matches('_')
            .to_string()
    }

    fn table_has_predicate_like_column(metadata: &TableMetadata, predicate_iri: &str) -> bool {
        let local = Self::predicate_local_name(predicate_iri);
        if local.is_empty() {
            return false;
        }

        metadata.columns.iter().any(|c| {
            let col = c.to_ascii_lowercase();
            col == local
                || col == format!("{}_id", local)
                || col.contains(&local)
                || local.contains(&col)
        })
    }
'''

if helper in text:
    pass
else:
    if insert_after not in text:
        raise SystemExit('normalize function anchor not found')
    text = text.replace(insert_after, insert_after + helper, 1)

old_block = '''        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        if let Some(pref_table) = preferred_table {
            for rule in &matching_rules {
                if rule.table_name == pref_table {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        let rule = matching_rules[0];
        metadata_map.get(&rule.table_name).map(Arc::clone)
'''
new_block = '''        if let Some(pref_table) = preferred_table {
            if let Some(pref_meta) = metadata_map.get(pref_table) {
                let subject_is_var = subject.map(|s| s.starts_with('?')).unwrap_or(false);
                if subject_is_var && Self::table_has_predicate_like_column(pref_meta, &predicate_iri) {
                    return Some(Arc::clone(pref_meta));
                }
            }

            for rule in &matching_rules {
                if rule.table_name == pref_table {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }

        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }

        let rule = matching_rules[0];
        metadata_map.get(&rule.table_name).map(Arc::clone)
'''
if old_block not in text:
    raise SystemExit('target resolve block not found')
text = text.replace(old_block, new_block, 1)

p.write_text(text, encoding='utf-8')
print('patched generic context-aware predicate table selection')