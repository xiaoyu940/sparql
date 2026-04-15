from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''                                      let _ = request.respond(
                                          Response::from_string("{\"error\":\"Internal server error\"}")
                                              .with_status_code(StatusCode(500)),
                                      );''','''                                      let response = Response::from_string("{\"error\":\"Internal server error\"}")
                                              .with_status_code(StatusCode(500));
                                      let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));''',1)
text=text.replace('''                              let _ = request.respond(
                                  Response::from_string(error_response.to_string())
                                      .with_status_code(StatusCode(status_code)),
                              );''','''                              let response = Response::from_string(error_response.to_string())
                                      .with_status_code(StatusCode(status_code));
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));''',1)
text=text.replace('''                              let _ = request.respond(
                                  Response::from_string(format!("{{\"error\":\"{}\"}}", error_msg))
                                      .with_status_code(StatusCode(500)),
                              );''','''                              let response = Response::from_string(format!("{{\"error\":\"{}\"}}", error_msg))
                                      .with_status_code(StatusCode(500));
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));''',1)
text=text.replace('''                  let _ = request.respond(
                      Response::from_string("{\"error\":\"Not Found\"}")
                          .with_status_code(StatusCode(404)),
                  );''','''                  let response = Response::from_string("{\"error\":\"Not Found\"}")
                          .with_status_code(StatusCode(404));
                  let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));''',1)
p.write_text(text,encoding='utf-8')
print('wrapped remaining responses with CORS')