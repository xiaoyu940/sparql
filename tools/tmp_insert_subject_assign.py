from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
old="""                if trimmed.starts_with('?') {
                    result.push_str(trimmed);
                    result.push_str(\" .\\n\");
"""
new="""                if trimmed.starts_with('?') {
                    if let Some(first_space) = trimmed.find(' ') {
                        current_subject = Some(trimmed[..first_space].to_string());
                    }
                    result.push_str(trimmed);
                    result.push_str(\" .\\n\");
"""
if old not in s:
    raise SystemExit('first block pattern not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('inserted current_subject assignment in first segment block')
