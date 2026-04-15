from pathlib import Path
s=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs').read_text(encoding='utf-8')
for i in range(2):
    idx=s.find("if trimmed.starts_with('?') {", 0 if i==0 else idx+1)
    print('idx',idx)
    if idx!=-1:
        print(s[idx-60:idx+200])
