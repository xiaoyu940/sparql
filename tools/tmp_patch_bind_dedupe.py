from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''        let mut bind_alias_exprs: HashMap<String, Expr> = HashMap::new();
        for bind in &parsed.bind_expressions {
            if let Some(expr) = Self::parse_filter_expr(&bind.expression) {
                bind_alias_exprs.insert(bind.alias.clone(), expr.clone());

                let mut current_bindings = HashMap::new();
'''
new='''        let mut bind_alias_exprs: HashMap<String, Expr> = HashMap::new();
        let mut seen_bind_aliases: std::collections::HashSet<String> = std::collections::HashSet::new();
        for bind in &parsed.bind_expressions {
            if !seen_bind_aliases.insert(bind.alias.clone()) {
                continue;
            }
            if let Some(expr) = Self::parse_filter_expr(&bind.expression) {
                bind_alias_exprs.insert(bind.alias.clone(), expr.clone());

                let mut current_bindings = HashMap::new();
'''
if old not in text:
    raise SystemExit('bind loop block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched bind alias dedupe (first-wins)')