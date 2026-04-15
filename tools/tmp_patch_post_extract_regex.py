from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/listener.rs')
text=p.read_text(encoding='utf-8')
pattern=r'if method == Method::Post \{[\s\S]*?\} else if method == Method::Get \{'
repl='''if method == Method::Post {
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
                      } else if method == Method::Get {'''
text,n=re.subn(pattern,repl,text,count=1)
if n!=1:
    raise SystemExit(f'pattern replace failed {n}')
p.write_text(text,encoding='utf-8')
print('patched post form query extraction')