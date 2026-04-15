from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
old='''        filter_expressions.retain(|f| {
            let vars = extract_vars_from_expr(f);
            vars.iter().all(|v| allowed_vars.contains(v))
        });'''
new='''        let _ = &allowed_vars;'''
if old not in s:
    raise SystemExit('retain block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('temporarily disabled filter whitelist retain')
