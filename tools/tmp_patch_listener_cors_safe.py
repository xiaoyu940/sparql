from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

text=text.replace('request: Option<&tiny_http::Request>,','requested_headers: Option<&str>,',1)
text=text.replace('let requested_headers = request.and_then(|req| {\n        req.headers()\n            .iter()\n            .find(|h| h.field.equiv("Access-Control-Request-Headers"))\n            .map(|h| h.value.as_str().to_string())\n    });\n    let allow_headers = requested_headers\n        .unwrap_or_else(|| "Content-Type, Accept, Authorization, Origin, X-Requested-With".to_string());','let allow_headers = requested_headers\n        .unwrap_or("Content-Type, Accept, Authorization, Origin, X-Requested-With");',1)

text=text.replace('''                  let path = request.url().to_string();
                  let method = request.method().clone();
                  consecutive_errors = 0;
''','''                  let path = request.url().to_string();
                  let method = request.method().clone();
                  let requested_cors_headers = request
                      .headers()
                      .iter()
                      .find(|h| h.field.equiv("Access-Control-Request-Headers"))
                      .map(|h| h.value.as_str().to_string());
                  consecutive_errors = 0;
''',1)

text=text.replace('if method == Method::Options && (path.starts_with("/sparql") || path.starts_with("/ontology")) {','if method == Method::Options {',1)
text=text.replace('with_cors_headers(response, Some(&request))','with_cors_headers(response, requested_cors_headers.as_deref())')

p.write_text(text,encoding='utf-8')
print('patched listener borrow-safe cors headers')