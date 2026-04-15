from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
old='''                  if trimmed.starts_with('?') {
                      // 这是一个完整的三元组（以变量开头），提取主语
                      result.push_str(trimmed);
                      result.push_str(" .\\n");
'''
new='''                  if trimmed.starts_with('?') {
                      // 这是一个完整的三元组（以变量开头），提取主语
                      if let Some(first_space) = trimmed.find(' ') {
                          current_subject = Some(trimmed[..first_space].to_string());
                      }
                      result.push_str(trimmed);
                      result.push_str(" .\\n");
'''
if old not in s:
    raise SystemExit('target block not found for restoring current_subject assignment')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('restored current_subject assignment in main segment parser loop')
