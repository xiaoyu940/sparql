from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
anchor = '''        if (t.starts_with('"') && t.ends_with('"'))
'''
insert = '''        if let Ok(typed_re) = regex::Regex::new(r#"^\"(.*)\"\^\^([^\s]+)$"#) {
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
    raise SystemExit('anchor not found')
text = text.replace(anchor, insert + anchor, 1)
p.write_text(text, encoding='utf-8')
print('ok parser')