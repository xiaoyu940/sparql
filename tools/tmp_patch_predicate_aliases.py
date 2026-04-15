from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')

insert_anchor = '''    fn resolve_metadata_for_predicate(
'''
helper = '''    fn normalize_predicate_iri_for_lookup(iri: &str) -> String {
        match iri {
            "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
            "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
            _ => iri.to_string(),
        }
    }

'''
if insert_anchor not in text:
    raise SystemExit('insert anchor not found')
text = text.replace(insert_anchor, helper + insert_anchor, 1)

text = text.replace(
'''        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>')
        } else {
            predicate
        };

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
''',
'''        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>').to_string()
        } else {
            predicate.to_string()
        };
        let predicate_iri = Self::normalize_predicate_iri_for_lookup(&predicate_iri);

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
''',
1)

text = text.replace(
'''        if let Some(rules) = store.mappings.get(predicate_iri) {
''',
'''        if let Some(rules) = store.mappings.get(&predicate_iri) {
''',
1)

text = text.replace(
'''        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>')
        } else {
            predicate
        };

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
''',
'''        let predicate_iri = if predicate.starts_with('<') && predicate.ends_with('>') {
            predicate.trim_start_matches('<').trim_end_matches('>').to_string()
        } else {
            predicate.to_string()
        };
        let predicate_iri = Self::normalize_predicate_iri_for_lookup(&predicate_iri);

        if predicate_iri.is_empty() || predicate_iri.starts_with('?') {
''',
1)

text = text.replace(
'''        if let Some(rules) = store.mappings.get(predicate_iri) {
''',
'''        if let Some(rules) = store.mappings.get(&predicate_iri) {
''',
1)

text = text.replace(
'''                let predicate_iri = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
''',
'''                let predicate_iri_raw = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
                let predicate_iri = Self::normalize_predicate_iri_for_lookup(&predicate_iri_raw);
''',
1)

text = text.replace(
'''                  let predicate_iri = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
''',
'''                  let predicate_iri_raw = pattern.predicate.trim_start_matches('<').trim_end_matches('>').to_string();
                  let predicate_iri = Self::normalize_predicate_iri_for_lookup(&predicate_iri_raw);
''',
1)

p.write_text(text, encoding='utf-8')
print('patched predicate alias lookup')