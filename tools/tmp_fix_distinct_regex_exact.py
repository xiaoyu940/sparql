from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('r"(?is)^(?:\\s*(?:PREFIX\\s+[^\\s:]+:\\s*<[^>]+>|BASE\\s+<[^>]+>)\\s*)*SELECT\\s+DISTINC"','r"(?is)^(?:\\s*(?:PREFIX\\s+[^\\s:]+:\\s*<[^>]+>|BASE\\s+<[^>]+>)\\s*)*SELECT\\s+DISTINCT\\b"',1)
p.write_text(text,encoding='utf-8')
print('fixed DISTINCT regex exact token')