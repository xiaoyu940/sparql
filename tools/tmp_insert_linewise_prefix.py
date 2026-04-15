from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
lines=p.read_text(encoding='utf-8').splitlines()
out=[]
inserted=False
for ln in lines:
    if (not inserted) and 'log!("rs-ontop-core: Received SPARQL query' in ln:
        out.append('                      if let Some(msg) = validate_prefix_declarations_for_http(&sparql_query) {')
        out.append('                            let response = Response::from_string(format!("{\\"error\\":\\"{}\\"}", msg))')
        out.append('                                .with_status_code(StatusCode(400));')
        out.append('                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));')
        out.append('                            continue;')
        out.append('                      }')
        out.append('')
        inserted=True
    out.append(ln)
p.write_text('\n'.join(out)+'\n',encoding='utf-8')
print('inserted=',inserted)