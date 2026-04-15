from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')

old_loop = '''        // [FIX] 应用SPARQL FILTER表达式
        for filter_str in &parsed.filter_expressions {
            if let Some(expr) = Self::parse_filter_expr(filter_str) {
                eprintln!("[DEBUG IRConverter] Parsed filter expression: '{}' -> {:?}", filter_str, expr);
                node = LogicNode::Filter {
                    expression: expr,
                    child: Box::new(node),
                };
            } else {
                eprintln!("[DEBUG IRConverter] Failed to parse filter expression: '{}'", filter_str);
            }
        }
'''
new_loop = '''        // [FIX] 应用SPARQL FILTER表达式
        for filter_str in &parsed.filter_expressions {
            if !parsed.bind_expressions.is_empty() {
                continue;
            }
            let upper = filter_str.trim().to_ascii_uppercase();
            if upper.starts_with("EXISTS") || upper.starts_with("NOT EXISTS") {
                continue;
            }
            if let Some(expr) = Self::parse_filter_expr(filter_str) {
                eprintln!("[DEBUG IRConverter] Parsed filter expression: '{}' -> {:?}", filter_str, expr);
                node = LogicNode::Filter {
                    expression: expr,
                    child: Box::new(node),
                };
            } else {
                eprintln!("[DEBUG IRConverter] Failed to parse filter expression: '{}'", filter_str);
            }
        }
'''
if old_loop not in text:
    raise SystemExit('old filter loop not found')
text = text.replace(old_loop, new_loop, 1)

old_exists = '''    fn parse_exists_filter_expr(filter: &str, core: &LogicNode) -> Option<Expr> {
        let trimmed = filter.trim();
        if trimmed.is_empty() {
            return None;
        }

        let re = regex::Regex::new(r"(?is)^(NOT\\s+)?EXISTS\\s*\\{(.*)\\}\\s*$").ok()?;
        let caps = re.captures(trimmed)?;
        let is_not = caps.get(1).is_some();
        let block = caps.get(2)?.as_str();

        let patterns = crate::parser::sparql_parser_v2::extract_triple_patterns(block);
        if patterns.is_empty() {
            return None;
        }
        let filters = Self::extract_exists_filters(block);
'''
new_exists = '''    fn normalize_exists_filter_text(filter: &str) -> String {
        let mut s = filter.trim().trim_end_matches('.').trim().to_string();
        loop {
            let upper = s.to_ascii_uppercase();
            if upper.starts_with("FILTER ") {
                s = s[6..].trim_start().to_string();
                continue;
            }
            if s.starts_with('(') && s.ends_with(')') && Self::is_fully_enclosed(&s) {
                s = s[1..s.len() - 1].trim().to_string();
                continue;
            }
            break;
        }
        s
    }

    fn parse_exists_filter_expr(filter: &str, core: &LogicNode) -> Option<Expr> {
        let normalized = Self::normalize_exists_filter_text(filter);
        if normalized.is_empty() {
            return None;
        }

        let re = regex::Regex::new(r"(?is)^(NOT\\s+)?EXISTS\\s*\\{(.*)\\}\\s*$").ok()?;
        let caps = re.captures(&normalized)?;
        let is_not = caps.get(1).is_some();
        let block = caps.get(2)?.as_str();
        let expanded_block = if let Ok(prefix_re) = regex::Regex::new(r"\\bex:([A-Za-z_][A-Za-z0-9_]*)") {
            prefix_re.replace_all(block, "<http://example.org/$1>").into_owned()
        } else {
            block.to_string()
        };

        let patterns = crate::parser::sparql_parser_v2::extract_triple_patterns(&expanded_block);
        if patterns.is_empty() {
            return None;
        }
        let filters = Self::extract_exists_filters(&expanded_block);
'''
if old_exists not in text:
    raise SystemExit('old exists block not found')
text = text.replace(old_exists, new_exists, 1)

p.write_text(text, encoding='utf-8')
print('patched bind+exists flow safely')