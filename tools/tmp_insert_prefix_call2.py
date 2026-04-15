from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
needle='                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);\n'
insert='''                      if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {
                            let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                                .with_status_code(StatusCode(400));
                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                            continue;
                      }

'''
if insert not in text:
    text=text.replace(needle,insert+needle,1)
p.write_text(text,encoding='utf-8')
print('inserted validation before log')