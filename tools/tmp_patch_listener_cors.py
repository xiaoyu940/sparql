from pathlib import Path
import re
p = Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text = p.read_text(encoding='utf-8')

old_fn = '''fn with_cors_headers<R: std::io::Read>(mut response: Response<R>) -> Response<R> {
    if let Ok(h) = Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]) {
        response = response.with_header(h);
    }
    if let Ok(h) = Header::from_bytes(&b"Access-Control-Allow-Methods"[..], &b"GET, POST, OPTIONS"[..]) {
        response = response.with_header(h);
    }
    if let Ok(h) = Header::from_bytes(&b"Access-Control-Allow-Headers"[..], &b"Content-Type, Accept"[..]) {
        response = response.with_header(h);
    }
    response
}
'''
new_fn = '''fn with_cors_headers<R: std::io::Read>(
    mut response: Response<R>,
    request: Option<&tiny_http::Request>,
) -> Response<R> {
    if let Ok(h) = Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]) {
        response = response.with_header(h);
    }
    if let Ok(h) = Header::from_bytes(&b"Access-Control-Allow-Methods"[..], &b"GET, POST, OPTIONS"[..]) {
        response = response.with_header(h);
    }

    let requested_headers = request.and_then(|req| {
        req.headers()
            .iter()
            .find(|h| h.field.equiv("Access-Control-Request-Headers"))
            .map(|h| h.value.as_str().to_string())
    });
    let allow_headers = requested_headers
        .unwrap_or_else(|| "Content-Type, Accept, Authorization, Origin, X-Requested-With".to_string());
    if let Ok(h) = Header::from_bytes(
        &b"Access-Control-Allow-Headers"[..],
        allow_headers.as_bytes(),
    ) {
        response = response.with_header(h);
    }

    if let Ok(h) = Header::from_bytes(&b"Access-Control-Max-Age"[..], &b"86400"[..]) {
        response = response.with_header(h);
    }
    if let Ok(h) = Header::from_bytes(
        &b"Vary"[..],
        &b"Origin, Access-Control-Request-Method, Access-Control-Request-Headers"[..],
    ) {
        response = response.with_header(h);
    }
    response
}
'''
if old_fn not in text:
    raise SystemExit('old CORS helper not found')
text = text.replace(old_fn, new_fn, 1)

text = text.replace(
    'if method == Method::Options && (path.starts_with("/sparql") || path.starts_with("/ontology")) {\n                        let response = Response::empty(StatusCode(204));\n                        let _ = request.respond(with_cors_headers(response));\n                        continue;\n                    }',
    'if method == Method::Options {\n                        let response = Response::empty(StatusCode(204));\n                        let _ = request.respond(with_cors_headers(response, Some(&request)));\n                        continue;\n                    }',
    1
)

# update existing with_cors_headers(response) calls
text = text.replace('with_cors_headers(response));', 'with_cors_headers(response, Some(&request)));')

# wrap remaining plain request.respond(...) branches with CORS when response is direct
repls = [
    ('let _ = request.respond(\n                                                Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                                    .with_status_code(StatusCode(500)),\n                                            );',
     'let response = Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                                    .with_status_code(StatusCode(500));\n                                            let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                                          Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                              .with_status_code(StatusCode(500)),\n                                      );',
     'let response = Response::from_string("{\\"error\\":\\"Internal server error\\"}")\n                                              .with_status_code(StatusCode(500));\n                                      let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                                Response::from_string("{\\"error\\":\\"Engine not initialized\\"}")\n                                    .with_status_code(StatusCode(503)),\n                            );',
     'let response = Response::from_string("{\\"error\\":\\"Engine not initialized\\"}")\n                                    .with_status_code(StatusCode(503));\n                            let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                                Response::from_string(format!("{{\\"error\\":\\"{}\\"}}", e))\n                                    .with_status_code(StatusCode(500)),\n                            );',
     'let response = Response::from_string(format!("{{\\"error\\":\\"{}\\"}}", e))\n                                    .with_status_code(StatusCode(500));\n                            let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                                  Response::from_string(error_response.to_string())\n                                      .with_status_code(StatusCode(status_code)),\n                              );',
     'let response = Response::from_string(error_response.to_string())\n                                      .with_status_code(StatusCode(status_code));\n                              let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                                  Response::from_string(format!("{{\\"error\\":\\"{}\\"}}", error_msg))\n                                      .with_status_code(StatusCode(500)),\n                              );',
     'let response = Response::from_string(format!("{{\\"error\\":\\"{}\\"}}", error_msg))\n                                      .with_status_code(StatusCode(500));\n                              let _ = request.respond(with_cors_headers(response, Some(&request)));'),
    ('let _ = request.respond(\n                      Response::from_string("{\\"error\\":\\"Not Found\\"}")\n                          .with_status_code(StatusCode(404)),\n                  );',
     'let response = Response::from_string("{\\"error\\":\\"Not Found\\"}")\n                          .with_status_code(StatusCode(404));\n                  let _ = request.respond(with_cors_headers(response, Some(&request)));')
]
for old, new in repls:
    text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
print('patched listener CORS handling comprehensively')