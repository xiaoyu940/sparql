from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
old='''            if ft.starts_with("EXISTS") || ft.starts_with("NOT EXISTS") {
                return true;
            }
'''
new='''            if ft.starts_with("EXISTS") || ft.starts_with("NOT EXISTS") || ft.contains("SELECT") {
                return true;
            }
'''
if old not in text:
    raise SystemExit('filter retain block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched filter retention for scalar subquery')