from pathlib import Path
# patch ir_converter panic-prone unwrap/index
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('let metadata = table_metadata.get(&group_key).unwrap();','let Some(metadata) = table_metadata.get(&group_key) else { continue; };',1)

old='''          if table_nodes.len() == 1 {
              table_nodes.into_iter().next().unwrap().1
          } else {
              // 构建左深树join，并基于共享变量创建join条件
              let mut result = table_nodes[0].1.clone();
'''
new='''          if table_nodes.is_empty() {
              if preserve_on_impossible {
                  LogicNode::Values {
                      variables: vec!["__unit".to_string()],
                      rows: vec![vec![Term::Constant("1".to_string())]],
                  }
              } else {
                  LogicNode::Values {
                      variables: Vec::new(),
                      rows: Vec::new(),
                  }
              }
          } else if table_nodes.len() == 1 {
              table_nodes.into_iter().next().map(|n| n.1).unwrap_or_else(|| LogicNode::Values {
                  variables: Vec::new(),
                  rows: Vec::new(),
              })
          } else {
              // 构建左深树join，并基于共享变量创建join条件
              let mut result = table_nodes[0].1.clone();
'''
if old in text:
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# patch listener no panic on header expect and formatting
p2=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text2=p2.read_text(encoding='utf-8')
old_block='''                          Ok(Ok(bindings)) => {
                              let out = format_sparql_response(&sparql_query, bindings);
                              let response = Response::from_string(out.to_string())
                                  .with_chunked_threshold(0)
                                  .with_header(
                                      tiny_http::Header::from_bytes(
                                          &b"Content-Type"[..],
                                          &b"application/sparql-results+json; charset=utf-8"[..],
                                      )
                                      .expect("should create header"),
                                  );
                              let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                          }
'''
new_block='''                          Ok(Ok(bindings)) => {
                              let render = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                                  format_sparql_response(&sparql_query, bindings)
                              }));

                              match render {
                                  Ok(out) => {
                                      let mut response = Response::from_string(out.to_string())
                                          .with_chunked_threshold(0);
                                      if let Ok(h) = tiny_http::Header::from_bytes(
                                          &b"Content-Type"[..],
                                          &b"application/sparql-results+json; charset=utf-8"[..],
                                      ) {
                                          response = response.with_header(h);
                                      }
                                      let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                                  }
                                  Err(_) => {
                                      let response = Response::from_string("{\"error\":\"Internal error: response rendering panic\"}")
                                          .with_status_code(StatusCode(500));
                                      let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                                  }
                              }
                          }
'''
if old_block in text2:
    text2=text2.replace(old_block,new_block,1)

p2.write_text(text2,encoding='utf-8')
print('patched panic hardening in ir_converter and listener')