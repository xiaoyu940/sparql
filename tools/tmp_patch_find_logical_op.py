from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''                      if c == b'<' && paren_depth == 0 {
                          if !in_iri && filter[i..].starts_with(op) {
                              return Some(i);
                          }
                          let next = bytes.get(i + 1).copied().unwrap_or(b' ');
                          if !is_comparison_op || next.is_ascii_alphabetic() {
                              in_iri = true;
                          }
                      } else if c == b'(' {
'''
new='''                      if c == b'<' && paren_depth == 0 {
                          let next = bytes.get(i + 1).copied().unwrap_or(b' ');
                          let iri_start = next.is_ascii_alphabetic();
                          if iri_start {
                              in_iri = true;
                          } else if !in_iri && filter[i..].starts_with(op) {
                              return Some(i);
                          }
                      } else if c == b'(' {
'''
if old not in text:
    raise SystemExit('target block not found for find_logical_op patch')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched comparator scan to avoid matching < at IRI start')