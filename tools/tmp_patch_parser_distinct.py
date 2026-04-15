from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')

# 1) ParsedQuery add distinct field after projected_vars
text=text.replace(
'''pub struct ParsedQuery {
    pub raw: String,
    pub query_type: QueryType,
    pub projected_vars: Vec<String>,
    pub has_filter: bool,
''',
'''pub struct ParsedQuery {
    pub raw: String,
    pub query_type: QueryType,
    pub projected_vars: Vec<String>,
    pub distinct: bool,
    pub has_filter: bool,
''',1)

# 2) compute distinct in parse
text=text.replace(
'''        let mut projected_vars = extract_projected_vars(trimmed);
''',
'''        let mut projected_vars = extract_projected_vars(trimmed);
        let distinct = extract_select_distinct(trimmed);
''',1)

# 3) assign field in ParsedQuery construction
text=text.replace(
'''            query_type,
            projected_vars,
            has_filter,
''',
'''            query_type,
            projected_vars,
            distinct,
            has_filter,
''',1)

# 4) add helper near extract_limit/extract_order_by section (append before strip_filter_exists_blocks)
insert_anchor='''fn strip_filter_exists_blocks(where_block: &str) -> String {
'''
helper='''fn extract_select_distinct(sparql: &str) -> bool {
    let re = regex::Regex::new(
        r"(?is)^(?:\s*(?:PREFIX\s+[^\s:]+:\s*<[^>]+>|BASE\s+<[^>]+>)\s*)*SELECT\s+DISTINCT\b"
    ).expect("valid DISTINCT regex");
    re.is_match(sparql.trim())
}

'''
if helper not in text:
    if insert_anchor not in text:
        raise SystemExit('insert anchor not found for distinct helper')
    text=text.replace(insert_anchor, helper + insert_anchor,1)

p.write_text(text,encoding='utf-8')
print('patched parser distinct support')