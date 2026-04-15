from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
old='''                      if method == Method::Post {
                          let mut content = String::new();
                          let _ = request.as_reader().read_to_string(&mut content);
                          sparql_query = content;
                      } else if method == Method::Get {
'''
new='''                      if method == Method::Post {
                          let mut content = String::new();
                          let _ = request.as_reader().read_to_string(&mut content);

                          let mut extracted = None;
                          for (key, val) in url::form_urlencoded::parse(content.as_bytes()) {
                              if key == "query" {
                                  extracted = Some(val.into_owned());
                                  break;
                              }
                          }

                          sparql_query = extracted.unwrap_or(content);
                      } else if method == Method::Get {
'''
if old not in text:
    raise SystemExit('post extract block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched POST body parsing for query=form-urlencoded')