from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace(
'r#"(?m)(\\?\\w+)\\s+([^?\\s][^\\s]*)\\s+(\\?\\w+|<[^>]+>|"[^"]*"(?:\\^\\^<[^>]+>)?)\\s*[.;]"#',
'r#"(?mi)(\\?\\w+)\\s+([^?\\s][^\\s]*)\\s+(\\?\\w+|<[^>]+>|"[^"]*"(?:\\^\\^<[^>]+>)?|true|false|-?\\d+(?:\\.\\d+)?|[A-Za-z_][A-Za-z0-9_:-]*)\\s*[.;]"#',
1)
p.write_text(text,encoding='utf-8')
print('patched triple pattern object regex to support booleans/numbers/prefixed names')