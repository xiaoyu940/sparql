from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
anchor = "        if (t.starts_with('\\"') && t.ends_with('\\"'))\n"
insert = "        if let Ok(typed_re) = regex::Regex::new(r#\"^\\\"(.*)\\\"\\^\\^([^\\s]+)$\"#) {\n            if let Some(caps) = typed_re.captures(t) {\n                let value = caps.get(1).map(|m| m.as_str()).unwrap_or(\"\").to_string();\n                let dt_raw = caps.get(2).map(|m| m.as_str()).unwrap_or(\"\");\n                let datatype = dt_raw\n                    .trim_start_matches('<')\n                    .trim_end_matches('>')\n                    .to_string();\n                return Term::Literal {\n                    value,\n                    datatype: Some(datatype),\n                    language: None,\n                };\n            }\n        }\n\n"
if anchor not in text:
    raise SystemExit('anchor not found')
text = text.replace(anchor, insert + anchor, 1)
p.write_text(text, encoding='utf-8')
print('patched parser typed literal')