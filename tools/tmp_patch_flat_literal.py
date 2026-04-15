from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
old = '''              Term::Literal { value, datatype, language: _ } => {
                  let escaped_value = self.escape_sql_string(value);
                  match datatype.as_deref() {
                      Some(dt) if dt.contains("integer") => Ok(escaped_value),
                      Some(dt) if dt.contains("decimal") => Ok(escaped_value),
                      Some(dt) if dt.contains("boolean") => Ok(escaped_value),
                      _ => Ok(format!("'{}'", escaped_value)),
                  }
              }
'''
new = '''              Term::Literal { value, datatype, language: _ } => {
                  let escaped_value = self.escape_sql_string(value);
                  match datatype.as_deref() {
                      Some(dt) if dt.contains("integer") => Ok(escaped_value),
                      Some(dt) if dt.contains("decimal") => Ok(escaped_value),
                      Some(dt) if dt.contains("boolean") => Ok(escaped_value),
                      Some(dt) if dt.contains("dateTime") || dt.contains("date") => Ok(format!("'{}'::date", escaped_value)),
                      Some(dt) if dt.contains("time") => Ok(format!("'{}'::time", escaped_value)),
                      _ => Ok(format!("'{}'", escaped_value)),
                  }
              }
'''
if old not in text:
    raise SystemExit('literal block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('ok flat')