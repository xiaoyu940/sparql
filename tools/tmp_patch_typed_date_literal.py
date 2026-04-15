from pathlib import Path

# 1) parser: token_to_term 支持 "..."^^xsd:date
p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
anchor = '''          if (t.starts_with('"') && t.ends_with('"'))
              || (t.starts_with('\'') && t.ends_with('\''))
          {
'''
insert = '''          if let Ok(typed_re) = regex::Regex::new(r#"^\"(.*)\"\^\^([^\s]+)$"#) {
              if let Some(caps) = typed_re.captures(t) {
                  let value = caps.get(1).map(|m| m.as_str()).unwrap_or("").to_string();
                  let dt_raw = caps.get(2).map(|m| m.as_str()).unwrap_or("");
                  let datatype = dt_raw
                      .trim_start_matches('<')
                      .trim_end_matches('>')
                      .to_string();
                  return Term::Literal {
                      value,
                      datatype: Some(datatype),
                      language: None,
                  };
              }
          }

'''
if anchor not in text:
    raise SystemExit('token_to_term anchor not found')
text = text.replace(anchor, insert + anchor, 1)
p.write_text(text, encoding='utf-8')

# 2) sql: typed literal date/dateTime 渲染
p2 = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text2 = p2.read_text(encoding='utf-8')
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
if old not in text2:
    raise SystemExit('translate_term literal block not found')
text2 = text2.replace(old, new, 1)
p2.write_text(text2, encoding='utf-8')

print('patched typed date literal parsing + rendering')