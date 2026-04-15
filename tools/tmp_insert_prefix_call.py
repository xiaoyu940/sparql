from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
old='''                      if sparql_query.is_empty() {
                            let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                                .with_status_code(StatusCode(400));
                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                            continue;
                        }

                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
'''
new='''                      if sparql_query.is_empty() {
                            let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                                .with_status_code(StatusCode(400));
                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                            continue;
                        }

                      if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {
                            let response = Response::from_string(format!("{{\"error\":\"{}\"}}", msg))
                                .with_status_code(StatusCode(400));
                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                            continue;
                      }

                      log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
'''
if old not in text:
    raise SystemExit('target block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('inserted prefix validation call in /sparql handler')