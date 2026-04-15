from pathlib import Path
import re

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
marker = 'for op_str in &["==", ">=", "<=", "=", ">", "<"] {'
insert = '''          // 2.1 尝试解析 IN 操作符
          if let Ok(in_re) = regex::Regex::new(r"(?is)^(.+?)\\s+IN\\s*\\((.+)\\)\\s*$") {
              if let Some(cap) = in_re.captures(trimmed) {
                  let left_part = cap.get(1).map(|m| m.as_str().trim()).unwrap_or("");
                  let right_list = cap.get(2).map(|m| m.as_str().trim()).unwrap_or("");
                  if !left_part.is_empty() && !right_list.is_empty() {
                      let mut args = Vec::new();
                      args.push(Self::parse_filter_expr(left_part)?);
                      for item in Self::split_function_args(right_list) {
                          let item_trimmed = item.trim();
                          if item_trimmed.is_empty() {
                              continue;
                          }
                          if let Some(e) = Self::parse_filter_expr(item_trimmed) {
                              args.push(e);
                          }
                      }
                      if args.len() >= 2 {
                          return Some(Expr::Function {
                              name: "IN".to_string(),
                              args,
                          });
                      }
                  }
              }
          }

'''
if marker not in text:
    raise SystemExit('parser marker not found')
text = text.replace(marker, insert + '          ' + marker, 1)
p.write_text(text, encoding='utf-8')

p2 = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text2 = p2.read_text(encoding='utf-8')
pat = r'("NOT"\s+if\s+args_sql\.len\(\)\s*==\s*1\s*=>\s*Ok\(format!\("NOT \(\{\}\)",\s*args_sql\[0\]\)\),)'
repl = r'\1\n                    "IN" if args_sql.len() >= 2 => Ok(format!("{} IN ({})", args_sql[0], args_sql[1..].join(", "))),'
text3, n = re.subn(pat, repl, text2, count=1)
if n != 1:
    raise SystemExit('sql replace failed')
p2.write_text(text3, encoding='utf-8')

print('patched IN filter parse + SQL render')