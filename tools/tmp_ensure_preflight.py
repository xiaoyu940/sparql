from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
s=p.read_text(encoding='utf-8')

if 'if method == Method::Options && (path.starts_with("/sparql") || path.starts_with("/ontology"))' not in s:
    s=re.sub(
        r'(let method = request\.method\(\)\.clone\(\);\n\s*consecutive_errors = 0;\n)\n(\s*if path\.starts_with\("/ontology"\) \{)',
        r'\1\n                  if method == Method::Options && (path.starts_with("/sparql") || path.starts_with("/ontology")) {\n                      let response = Response::empty(StatusCode(204));\n                      let _ = request.respond(with_cors_headers(response));\n                      continue;\n                  }\n\n\2',
        s,
        count=1,
    )

# Ensure /sparql missing query uses CORS wrapper
s=s.replace(
'''                          let _ = request.respond(
                              Response::from_string("{\"error\":\"Missing query parameter\"}")
                                  .with_status_code(StatusCode(400)),
                          );''',
'''                          let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                              .with_status_code(StatusCode(400));
                          let _ = request.respond(with_cors_headers(response));''',
1)

p.write_text(s,encoding='utf-8')
print('ensured preflight block and missing-query CORS response in listener.rs')
