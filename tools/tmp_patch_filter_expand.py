from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

# add helper before substitute_bind_aliases
anchor='''    fn substitute_bind_aliases(
        expr: Expr,
        bind_alias_exprs: &HashMap<String, Expr>,
    ) -> Expr {'''
helper='''    fn expand_bind_aliases_in_filter(filter: &str, bind_exprs: &[crate::parser::sparql_parser_v2::BindExpression]) -> String {
        let mut expanded = filter.to_string();
        for bind in bind_exprs {
            let pattern = format!(r"\\?{}\\b", regex::escape(&bind.alias));
            if let Ok(re) = regex::Regex::new(&pattern) {
                expanded = re
                    .replace_all(&expanded, format!("({})", bind.expression).as_str())
                    .to_string();
            }
        }
        expanded
    }

'''
if helper not in s:
    idx=s.find(anchor)
    if idx==-1:
        raise SystemExit('anchor not found')
    s=s[:idx]+helper+s[idx:]

# update filter loop to use expanded_filter
old='''        for filter in &parsed.filter_expressions {
            eprintln!("[DEBUG] Parsing filter: {}", filter);
            let expr = if let Some(exists_expr) = Self::parse_exists_filter_expr(filter, &core) {
                exists_expr
            } else if let Some(normal_expr) = Self::parse_filter_expr(filter) {
                Self::substitute_bind_aliases(normal_expr, &bind_alias_exprs)
            } else {
                continue;
            };'''
new='''        for filter in &parsed.filter_expressions {
            eprintln!("[DEBUG] Parsing filter: {}", filter);
            let expanded_filter = Self::expand_bind_aliases_in_filter(filter, &parsed.bind_expressions);
            let expr = if let Some(exists_expr) = Self::parse_exists_filter_expr(&expanded_filter, &core) {
                exists_expr
            } else if let Some(normal_expr) = Self::parse_filter_expr(&expanded_filter) {
                Self::substitute_bind_aliases(normal_expr, &bind_alias_exprs)
            } else {
                continue;
            };'''
if old not in s:
    raise SystemExit('filter loop block not found')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('patched filter textual bind alias expansion')
