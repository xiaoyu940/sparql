from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''        for filter in &parsed.filter_expressions {
            // 提取 ?var 格式的变量
            let re = regex::Regex::new(r"\?([A-Za-z_][A-Za-z0-9_]*)").unwrap();
            for cap in re.captures_iter(filter) {
                needed_vars.insert(cap[1].to_string());
            }
        }'''
new='''        for filter in &parsed.filter_expressions {
            let ft = filter.trim();
            let upper = ft.to_ascii_uppercase();
            if upper.starts_with("EXISTS") || upper.starts_with("NOT EXISTS") {
                continue;
            }
            let re = regex::Regex::new(r"\?([A-Za-z_][A-Za-z0-9_]*)").unwrap();
            for cap in re.captures_iter(filter) {
                needed_vars.insert(cap[1].to_string());
            }
        }'''
if old not in s:
    raise SystemExit('needed_vars filter extraction block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched needed_vars extraction to skip EXISTS/NOT EXISTS inner vars')
