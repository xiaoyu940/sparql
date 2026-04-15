from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')

s=s.replace(r'r"(?is)VALUES\s+(?:\?\w+|\(\s*(?:\?\w+\s*)+\))\s*\{\s*(.+?)\s*\}"',
            r'r"(?is)VALUES\s+(?:\?\w+|\(\s*(?:\?\w+\s*)+\))\s*\{\s*(.*?)\s*\}"',1)

old='''    if variables.is_empty() || rows.is_empty() {
        return None;
    }

    Some(ValuesBlock { variables, rows })'''
new='''    if variables.is_empty() {
        return None;
    }

    Some(ValuesBlock { variables, rows })'''
if old not in s:
    raise SystemExit('rows empty return block not found')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('patched VALUES parser for empty block support')
