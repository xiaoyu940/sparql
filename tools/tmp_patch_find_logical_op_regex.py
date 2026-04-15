from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
pattern=r"if c == b'<' && paren_depth == 0 \{[\s\S]*?\} else if c == b'\('\s*\{"
repl="""if c == b'<' && paren_depth == 0 {
                          let next = bytes.get(i + 1).copied().unwrap_or(b' ');
                          let iri_start = next.is_ascii_alphabetic();
                          if iri_start {
                              in_iri = true;
                          } else if !in_iri && filter[i..].starts_with(op) {
                              return Some(i);
                          }
                      } else if c == b'(' {"""
new,n=re.subn(pattern,repl,text,count=1)
if n!=1:
    raise SystemExit(f'patch failed {n}')
p.write_text(new,encoding='utf-8')
print('patched find_logical_op with regex')