from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
s=p.read_text(encoding='utf-8')
pat=re.compile(r'if sparql_query\.is_empty\(\) \{[\s\S]*?continue;\n\s*\}', re.M)
m=pat.search(s)
if not m:
    raise SystemExit('missing-query if block not found by regex')
new='''if sparql_query.is_empty() {
                          let response = Response::from_string("{\"error\":\"Missing query parameter\"}")
                              .with_status_code(StatusCode(400));
                          let _ = request.respond(with_cors_headers(response));
                          continue;
                      }'''
s=s[:m.start()]+new+s[m.end():]
p.write_text(s,encoding='utf-8')
print('patched missing-query block via regex')
