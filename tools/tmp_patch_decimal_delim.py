from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''        } else if (ch == '.' || ch == ';') && !in_iri && !in_string {
''','''        } else if (ch == ';' || (ch == '.' && !prev_char.is_ascii_digit())) && !in_iri && !in_string {
''',1)
p.write_text(text,encoding='utf-8')
print('patched shorthand delimiter to avoid splitting decimal literals')