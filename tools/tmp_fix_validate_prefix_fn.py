from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
start=text.find('fn validate_prefix_declarations(sparql: &str) -> Option<String> {')
end=text.find('fn extract_where_block', start)
if start<0 or end<0:
    raise SystemExit('bounds not found')
new_fn='''fn validate_prefix_declarations(sparql: &str) -> Option<String> {
    let prefix_re = regex::Regex::new(r"(?im)^\\s*PREFIX\\s+([^\\s:]+):\\s*<([^>]*)>\\s*$").ok()?;
    for cap in prefix_re.captures_iter(sparql) {
        let prefix = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let iri = cap.get(2).map(|m| m.as_str()).unwrap_or("");
        if iri.is_empty() || iri.contains('`') || iri.chars().any(|c| c.is_whitespace()) {
            return Some(format!("Invalid PREFIX declaration for '{}': IRI must be a clean <...> value", prefix));
        }
    }
    None
}

'''
text=text[:start]+new_fn+text[end:]
p.write_text(text,encoding='utf-8')
print('rewrote validate_prefix_declarations function cleanly')