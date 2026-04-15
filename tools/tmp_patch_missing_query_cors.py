from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
s=p.read_text(encoding='utf-8')
old='''                      if sparql_query.is_empty() {
                          let _ = request.respond(
                              Response::from_string("{\"error\":\"Missing query parameter\"}")
                                  .with_status_code(StatusCode(400)),
                          );
                          continue;
                      }
'''
new='''                      if sparql_query.is_empty() {
                          let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                              .with_status_code(StatusCode(400));
                          let _ = request.respond(with_cors_headers(response));
                          continue;
                      }
'''
if old not in s:
    raise SystemExit('target missing-query block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched missing query response with CORS headers')
