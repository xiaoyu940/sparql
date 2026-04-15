from pathlib import Path
import re

# listener replace block via regex
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
pattern=r'Ok\(Ok\(bindings\)\) => \{[\s\S]*?\n\s*\}\n\s*Ok\(Err\(e\)\) => \{'
replacement='''Ok(Ok(bindings)) => {
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
                                      let response = Response::from_string("{\\"error\\":\\"Internal error: response rendering panic\\"}")
                                          .with_status_code(StatusCode(500));
                                      let _ = request.respond(with_cors_headers(response, requested_cors_headers.as_deref()));
                                  }
                              }
                          }
                          Ok(Err(e)) => {'''
text,new_n=re.subn(pattern,replacement,text,count=1)
p.write_text(text,encoding='utf-8')
print('listener replaced',new_n)

# ir_converter replace join tail via regex
p2=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text2=p2.read_text(encoding='utf-8')
text2=text2.replace('let metadata = table_metadata.get(&group_key).unwrap();','let Some(metadata) = table_metadata.get(&group_key) else { continue; };',1)
pattern2=r'if table_nodes\.len\(\) == 1 \{[\s\S]*?let mut result = table_nodes\[0\]\.1\.clone\(\);'
replacement2='''if table_nodes.is_empty() {
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
              let mut result = table_nodes[0].1.clone();'''
text2,n2=re.subn(pattern2,replacement2,text2,count=1)
p2.write_text(text2,encoding='utf-8')
print('ir replaced',n2)