from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
needle='let distinct = extract_select_distinct(trimmed);'
if needle in text and '[DEBUG parse] distinct=' not in text:
    text=text.replace(needle, needle+'\n        eprintln!("[DEBUG parse] distinct={}", distinct);',1)
p.write_text(text,encoding='utf-8')
print('inserted temporary distinct debug')