from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')

# helper signature/body
text=text.replace('''fn with_cors_headers<R: std::io::Read>(
    mut response: Response<R>,
    request: Option<&tiny_http::Request>,
) -> Response<R> {''','''fn with_cors_headers<R: std::io::Read>(
    mut response: Response<R>,
    requested_headers: Option<&str>,
) -> Response<R> {''',1)

text=text.replace('''    let requested_headers = request.and_then(|req| {
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
''','''    let allow_headers = requested_headers
        .unwrap_or("Content-Type, Accept, Authorization, Origin, X-Requested-With");
    if let Ok(h) = Header::from_bytes(
        &b"Access-Control-Allow-Headers"[..],
        allow_headers.as_bytes(),
    ) {
''',1)

# add extraction variable near method/path
anchor='''                  let path = request.url().to_string();
                  let method = request.method().clone();
                  consecutive_errors = 0;
'''
insert='''                  let path = request.url().to_string();
                  let method = request.method().clone();
                  let requested_cors_headers = request
                      .headers()
                      .iter()
                      .find(|h| h.field.equiv("Access-Control-Request-Headers"))
                      .map(|h| h.value.as_str().to_string());
                  consecutive_errors = 0;
'''
if anchor not in text:
    raise SystemExit('loop anchor not found')
text=text.replace(anchor,insert,1)

text=text.replace('with_cors_headers(response, Some(&request))','with_cors_headers(response, requested_cors_headers.as_deref())')

p.write_text(text,encoding='utf-8')
print('fixed CORS helper borrow issue')