from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
start=text.find('fn validate_prefix_declarations(sparql: &str) -> Option<String> {')
end=text.find('fn extract_where_block', start)
new_fn='''fn validate_prefix_declarations(sparql: &str) -> Option<String> {
    let strict = regex::Regex::new(r"(?i)^\s*PREFIX\s+([^\s:]+):\s*<([^>]+)>\s*$").ok()?;
    for raw_line in sparql.lines() {
        let line = raw_line.trim();
        if line.to_ascii_uppercase().starts_with("PREFIX") {
            let Some(caps) = strict.captures(line) else {
                return Some("Invalid PREFIX declaration syntax".to_string());
            };
            let prefix = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let iri = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            if iri.is_empty() || iri.contains('`') || iri.chars().any(|c| c.is_whitespace()) {
                return Some(format!("Invalid PREFIX declaration for '{}': IRI must be a clean <...> value", prefix));
            }
        }
    }
    None
}

'''
text=text[:start]+new_fn+text[end:]
p.write_text(text,encoding='utf-8')
print('strengthened PREFIX line validation')