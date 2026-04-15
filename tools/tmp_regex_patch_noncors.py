from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

patterns=[
(r"let _ = request\.respond\(\s*Response::from_string\(\"\\\{\\\"error\\\":\\\"Internal server error\\\"\\\}\"\)\s*\.with_status_code\(StatusCode\(500\)\),\s*\);",
 'let response = Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                            .with_status_code(StatusCode(500));\n                                    let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));'),
(r"let _ = request\.respond\(\s*Response::from_string\(error_response\.to_string\(\)\)\s*\.with_status_code\(StatusCode\(status_code\)\),\s*\);",
 'let response = Response::from_string(error_response.to_string())\n                                .with_status_code(StatusCode(status_code));\n                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));'),
(r"let _ = request\.respond\(\s*Response::from_string\(format!\(\"\{\\\"error\\\":\\\"\{\}\"\}\", error_msg\)\)\s*\.with_status_code\(StatusCode\(500\)\),\s*\);",
 'let response = Response::from_string(format!("{\\"error\\":\\"{}\\"}", error_msg))\n                                .with_status_code(StatusCode(500));\n                            let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));'),
(r"let _ = request\.respond\(\s*Response::from_string\(\"\\\{\\\"error\\\":\\\"Not Found\\\"\\\}\"\)\s*\.with_status_code\(StatusCode\(404\)\),\s*\);",
 'let response = Response::from_string("{\\"error\\":\\"Not Found\\"}")\n                    .with_status_code(StatusCode(404));\n                let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));')
]

for pat,repl in patterns:
    text, n = re.subn(pat,repl,text,count=1,flags=re.S)
    print('replaced',n)

p.write_text(text,encoding='utf-8')
print('regex patched remaining plain responses')