from pathlib import Path
import re

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
pattern = r'(Some\(dt\) if dt\.contains\("boolean"\) => Ok\(escaped_value\),\s*\n\s*)_ => Ok\(format!\("\'\{\}\'", escaped_value\)\),'
repl = r'\1Some(dt) if dt.contains("dateTime") || dt.contains("date") => Ok(format!("\'{}\'::date", escaped_value)),\n                      Some(dt) if dt.contains("time") => Ok(format!("\'{}\'::time", escaped_value)),\n                      _ => Ok(format!("\'{}\'", escaped_value)),'
new, n = re.subn(pattern, repl, text, count=1)
if n != 1:
    raise SystemExit(f'regex replace failed: {n}')
p.write_text(new, encoding='utf-8')
print('ok flat literal regex')