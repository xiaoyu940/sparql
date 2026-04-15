from pathlib import Path

# ---- patch parser ----
p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text = p.read_text(encoding='utf-8')

# add MinusBlock struct
if 'pub struct MinusBlock' not in text:
    text = text.replace(
'''pub struct BindExpr {
    pub expression: String,
    pub alias: String,
}
''',
'''pub struct BindExpr {
    pub expression: String,
    pub alias: String,
}

#[derive(Debug, Clone)]
pub struct MinusBlock {
    pub patterns: Vec<TriplePattern>,
    pub filters: Vec<String>,
}
''',1)

# add field in ParsedQuery
if 'pub minus_blocks: Vec<MinusBlock>,' not in text:
    text = text.replace('    pub union_patterns: Vec<Vec<TriplePattern>>,\n', '    pub union_patterns: Vec<Vec<TriplePattern>>,\n    pub minus_blocks: Vec<MinusBlock>,\n',1)

# parse flow adjustments
text = text.replace(
'''        let optional_patterns = extract_optional_patterns(&expanded_where);
        let where_without_optional = strip_optional_blocks(&expanded_where);
        let main_patterns = extract_triple_patterns(&where_without_optional);
        let union_patterns = extract_union_patterns(&where_without_optional);
        let mut filter_expressions = extract_filter_expressions(&where_without_subqueries);
''',
'''        let minus_blocks = extract_minus_blocks(&expanded_where);
        let where_without_minus = strip_minus_blocks(&expanded_where);
        let optional_patterns = extract_optional_patterns(&where_without_minus);
        let where_without_optional = strip_optional_blocks(&where_without_minus);
        let main_patterns = extract_triple_patterns(&where_without_optional);
        let union_patterns = extract_union_patterns(&where_without_optional);
        let mut filter_expressions = extract_filter_expressions(&where_without_optional);

        let mut left_vars: std::collections::HashSet<String> = std::collections::HashSet::new();
        for p in &main_patterns {
            if let Some(v) = p.subject.strip_prefix('?') {
                left_vars.insert(v.to_string());
            }
            if let Some(v) = p.object.strip_prefix('?') {
                left_vars.insert(v.to_string());
            }
        }

        for minus in &minus_blocks {
            let mut minus_vars: std::collections::HashSet<String> = std::collections::HashSet::new();
            for p in &minus.patterns {
                if let Some(v) = p.subject.strip_prefix('?') {
                    minus_vars.insert(v.to_string());
                }
                if let Some(v) = p.object.strip_prefix('?') {
                    minus_vars.insert(v.to_string());
                }
            }
            let has_shared = minus_vars.iter().any(|v| left_vars.contains(v));
            if !has_shared {
                continue;
            }

            let mut block_parts: Vec<String> = minus.patterns.iter().map(|p| {
                format!("{} {} {} .", p.subject, p.predicate, p.object)
            }).collect();
            for f in &minus.filters {
                block_parts.push(format!("FILTER({})", f.trim()));
            }
            if !block_parts.is_empty() {
                filter_expressions.push(format!("NOT EXISTS {{ {} }}", block_parts.join(" ")));
            }
        }
''',1)

# ParsedQuery construction include minus_blocks
if '            union_patterns,\n            minus_blocks,\n            filter_expressions,' not in text:
    text = text.replace('            union_patterns,\n            filter_expressions,\n', '            union_patterns,\n            minus_blocks,\n            filter_expressions,\n',1)

# helper funcs add before strip_optional_blocks
if 'fn extract_minus_blocks(where_block: &str) -> Vec<MinusBlock>' not in text:
    anchor = 'fn strip_optional_blocks(where_block: &str) -> String {'
    helper = '''fn extract_minus_blocks(where_block: &str) -> Vec<MinusBlock> {
    let mut out = Vec::new();
    let chars: Vec<char> = where_block.chars().collect();
    let mut i = 0usize;

    while i < chars.len() {
        let rem: String = chars[i..].iter().collect();
        let upper = rem.to_ascii_uppercase();
        if upper.starts_with("MINUS") {
            i += "MINUS".len();
            while i < chars.len() && chars[i].is_whitespace() {
                i += 1;
            }
            if i < chars.len() && chars[i] == '{' {
                let start = i + 1;
                let mut depth = 1i32;
                i += 1;
                while i < chars.len() {
                    if chars[i] == '{' {
                        depth += 1;
                    } else if chars[i] == '}' {
                        depth -= 1;
                        if depth == 0 {
                            let block: String = chars[start..i].iter().collect();
                            let patterns = extract_triple_patterns(&block);
                            let filters = extract_filter_expressions(&block);
                            out.push(MinusBlock { patterns, filters });
                            i += 1;
                            break;
                        }
                    }
                    i += 1;
                }
                continue;
            }
        }
        i += 1;
    }

    out
}

fn strip_minus_blocks(where_block: &str) -> String {
    let mut result = String::new();
    let chars: Vec<char> = where_block.chars().collect();
    let mut i = 0usize;

    while i < chars.len() {
        let rem: String = chars[i..].iter().collect();
        let upper = rem.to_ascii_uppercase();
        if upper.starts_with("MINUS") {
            i += "MINUS".len();
            while i < chars.len() && chars[i].is_whitespace() {
                i += 1;
            }
            if i < chars.len() && chars[i] == '{' {
                let mut depth = 1i32;
                i += 1;
                while i < chars.len() {
                    if chars[i] == '{' {
                        depth += 1;
                    } else if chars[i] == '}' {
                        depth -= 1;
                        if depth == 0 {
                            i += 1;
                            break;
                        }
                    }
                    i += 1;
                }
                continue;
            }
        }

        result.push(chars[i]);
        i += 1;
    }

    result
}

'''
    text = text.replace(anchor, helper + anchor, 1)

p.write_text(text, encoding='utf-8')

# ---- patch ir converter ----
p2 = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text2 = p2.read_text(encoding='utf-8')
text2 = text2.replace('ordered_patterns.sort_by_key(|p| if Self::is_rdf_type_predicate(&p.predicate) { 1 } else { 0 });',
                      'ordered_patterns.sort_by_key(|p| if Self::is_rdf_type_predicate(&p.predicate) { 0 } else { 1 });',1)
text2 = text2.replace('if Self::is_rdf_type_predicate(&pattern.predicate) {\n                  subject_preferred_table\n                      .entry(canonical_subject.clone())\n                      .or_insert(table_name_hint.clone());\n              } else {\n                  subject_preferred_table.insert(canonical_subject.clone(), table_name_hint.clone());\n              }',
                      'if Self::is_rdf_type_predicate(&pattern.predicate) {\n                  subject_preferred_table.insert(canonical_subject.clone(), table_name_hint.clone());\n              } else {\n                  subject_preferred_table\n                      .entry(canonical_subject.clone())\n                      .or_insert(table_name_hint.clone());\n              }',1)
p2.write_text(text2, encoding='utf-8')

print('patched parser minus semantics + class-priority table selection')