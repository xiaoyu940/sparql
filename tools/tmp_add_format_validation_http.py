from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

# insert call in /sparql handler after prefix validation
needle='''                        if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {
                              let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                                  .with_status_code(StatusCode(400));
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                              continue;
                        }

                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
'''
insert='''                        if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {
                              let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                                  .with_status_code(StatusCode(400));
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                              continue;
                        }

                        if let Some(msg) = validate_sparql_format_for_http(&sparql_query) {
                              let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                                  .with_status_code(StatusCode(400));
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                              continue;
                        }

                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
'''
if needle in text:
    text=text.replace(needle,insert,1)
else:
    raise SystemExit('handler insertion anchor not found')

# add function if absent
if 'fn validate_sparql_format_for_http(sparql: &str) -> Option<String>' not in text:
    anchor='fn to_sparql_term(v: serde_json::Value) -> serde_json::Value {'
    fn_code='''fn validate_sparql_format_for_http(sparql: &str) -> Option<String> {
    let parser = SparqlParserV2::default();
    if let Err(e) = parser.parse(sparql) {
        return Some(format!("Invalid SPARQL format: {}", e));
    }
    None
}

'''
    if anchor not in text:
        raise SystemExit('format fn anchor not found')
    text=text.replace(anchor, fn_code + anchor, 1)

p.write_text(text,encoding='utf-8')
print('added generic SPARQL format validation in HTTP handler')