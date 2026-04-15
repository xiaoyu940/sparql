from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

text, n1 = re.subn(
    r'let _ = request\.respond\(\s*Response::from_string\("\{\\"error\\":\\"Internal server error\\"\}"\)\s*\.with_status_code\(StatusCode\(500\)\),\s*\);',
    'let response = Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                            .with_status_code(StatusCode(500));\n                                      let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));',
    text,
    count=1,
    flags=re.S,
)
text, n2 = re.subn(
    r'let _ = request\.respond\(\s*Response::from_string\(format!\("\{\{\\"error\\":\\"\{\}\\"\}\}", error_msg\)\)\s*\.with_status_code\(StatusCode\(500\)\),\s*\);',
    'let response = Response::from_string(format!("{\\"error\\":\\"{}\\"}", error_msg))\n                                .with_status_code(StatusCode(500));\n                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));',
    text,
    count=1,
    flags=re.S,
)
text, n3 = re.subn(
    r'let _ = request\.respond\(\s*Response::from_string\("\{\\"error\\":\\"Not Found\\"\}"\)\s*\.with_status_code\(StatusCode\(404\)\),\s*\);',
    'let response = Response::from_string("{\\"error\\":\\"Not Found\\"}")\n                    .with_status_code(StatusCode(404));\n                let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));',
    text,
    count=1,
    flags=re.S,
)

p.write_text(text,encoding='utf-8')
print('replacements', n1, n2, n3)