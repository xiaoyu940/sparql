from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
start=text.find('fn validate_sparql_format_for_http(sparql: &str) -> Option<String> {')
end=text.find('\nfn to_sparql_term', start)
if start<0 or end<0:
    raise SystemExit('format function bounds not found')
new_fn='''fn validate_sparql_format_for_http(sparql: &str) -> Option<String> {
    let parser = SparqlParserV2::default();
    let parsed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| parser.parse(sparql)));
    match parsed {
        Ok(Ok(_)) => None,
        Ok(Err(e)) => Some(format!("Invalid SPARQL format: {}", e)),
        Err(_) => Some("Invalid SPARQL format: parser panic".to_string()),
    }
}

'''
text=text[:start]+new_fn+text[end+1:]
p.write_text(text,encoding='utf-8')
print('hardened format validator with catch_unwind')