from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
if 'use spargebra::Query;' not in text:
    text=text.replace('use tiny_http::{Header, Method, Response, Server, StatusCode};','use tiny_http::{Header, Method, Response, Server, StatusCode};\nuse spargebra::Query;')

start=text.find('fn validate_sparql_format_for_http(sparql: &str) -> Option<String> {')
end=text.find('\nfn to_sparql_term',start)
new_fn='''fn validate_sparql_format_for_http(sparql: &str) -> Option<String> {
    let upper = sparql.to_ascii_uppercase();
    if !upper.contains("ORDER BY") {
        let syntax = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| Query::parse(sparql, None)));
        match syntax {
            Ok(Ok(_)) => {}
            Ok(Err(e)) => return Some(format!("Invalid SPARQL format: {}", e)),
            Err(_) => return Some("Invalid SPARQL format: parser panic".to_string()),
        }
    }

    let parser = SparqlParserV2::default();
    let parsed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| parser.parse(sparql)));
    match parsed {
        Ok(Ok(_)) => None,
        Ok(Err(e)) => Some(format!("Invalid SPARQL format: {}", e)),
        Err(_) => Some("Invalid SPARQL format: parser panic".to_string()),
    }
}

'''
if start<0 or end<0:
    raise SystemExit('function bounds not found')
text=text[:start]+new_fn+text[end+1:]
p.write_text(text,encoding='utf-8')
print('enhanced format checker with spargebra syntax validation')