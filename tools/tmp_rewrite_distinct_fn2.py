from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
start=text.find('fn extract_select_distinct(sparql: &str) -> bool {')
if start<0:
    raise SystemExit('start not found')
end=text.find('fn strip_filter_exists_blocks', start)
if end<0:
    raise SystemExit('end not found')
new_fn='''fn extract_select_distinct(sparql: &str) -> bool {
    let re = regex::Regex::new(
        r"(?is)^(?:\\s*(?:PREFIX\\s+[^\\s:]+:\\s*<[^>]+>|BASE\\s+<[^>]+>)\\s*)*SELECT\\s+DISTINCT"
    ).expect("valid DISTINCT regex");
    re.is_match(sparql.trim())
}

'''
text = text[:start] + new_fn + text[end:]
p.write_text(text,encoding='utf-8')
print('rewrote distinct fn by slicing')