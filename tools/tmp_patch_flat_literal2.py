from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
needle = '                      Some(dt) if dt.contains("boolean") => Ok(escaped_value),\n                      _ => Ok(format!("\'{}\'", escaped_value)),\n'
repl = '                      Some(dt) if dt.contains("boolean") => Ok(escaped_value),\n                      Some(dt) if dt.contains("dateTime") || dt.contains("date") => Ok(format!("\'{}\'::date", escaped_value)),\n                      Some(dt) if dt.contains("time") => Ok(format!("\'{}\'::time", escaped_value)),\n                      _ => Ok(format!("\'{}\'", escaped_value)),\n'
if needle not in text:
    raise SystemExit('needle not found')
text = text.replace(needle, repl, 1)
p.write_text(text, encoding='utf-8')
print('ok flat literal')