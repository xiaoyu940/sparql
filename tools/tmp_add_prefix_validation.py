from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''        if trimmed.is_empty() {
            return Err(OntopError::IRError("Empty SPARQL query".to_string()));
        }

        // 只对不含 ORDER BY 的查询使用 spargebra 验证
''','''        if trimmed.is_empty() {
            return Err(OntopError::IRError("Empty SPARQL query".to_string()));
        }

        if let Some(err) = validate_prefix_declarations(trimmed) {
            return Err(OntopError::IRError(err));
        }

        // 只对不含 ORDER BY 的查询使用 spargebra 验证
''',1)

if 'fn validate_prefix_declarations(sparql: &str) -> Option<String>' not in text:
    insert='''
fn validate_prefix_declarations(sparql: &str) -> Option<String> {
    let prefix_re = regex::Regex::new(r"(?im)^\s*PREFIX\s+([^\s:]+):\s*<([^>]*)>\s*$").ok()?;
    for cap in prefix_re.captures_iter(sparql) {
        let prefix = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let iri = cap.get(2).map(|m| m.as_str()).unwrap_or("");
        if iri.is_empty() || iri.contains('`') || iri.contains(' ') || iri.contains('\t') || iri.contains('\n') || iri.contains('\r') {
            return Some(format!("Invalid PREFIX declaration for '{}': IRI must be a clean <...> value", prefix));
        }
    }
    None
}

'''
    marker='fn extract_where_block'
    idx=text.find(marker)
    if idx!=-1:
        text=text[:idx]+insert+text[idx:]

p.write_text(text,encoding='utf-8')
print('added PREFIX validation in parser')