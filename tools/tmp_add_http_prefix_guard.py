from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

insert_block='''
                      if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {
                          let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                              .with_status_code(StatusCode(400));
                          let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                          continue;
                      }

'''
anchor='''                      if sparql_query.is_empty() {
                            let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                                .with_status_code(StatusCode(400));
                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                            continue;
                        }

                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
'''
if insert_block not in text:
    text=text.replace(anchor,anchor.replace('\n\n                      log!','\n\n'+insert_block+'                      log!'),1)

if 'fn validate_prefix_declarations_for_http' not in text:
    fn_txt='''
fn validate_prefix_declarations_for_http(sparql: &str) -> Option<String> {
    let strict = regex::Regex::new(r"(?i)^\\s*PREFIX\\s+([^\\s:]+):\\s*<([^>]+)>\\s*$").ok()?;
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
    idx=text.find('fn to_sparql_term')
    text=text[:idx]+fn_txt+text[idx:]

p.write_text(text,encoding='utf-8')
print('added http prefix validation guard')