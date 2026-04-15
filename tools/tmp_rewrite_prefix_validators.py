from pathlib import Path

def rewrite_fn(path, fn_name):
    p=Path(path)
    text=p.read_text(encoding='utf-8')
    start=text.find(f'fn {fn_name}(sparql: &str) -> Option<String> {{')
    if start<0:
        raise SystemExit(f'{fn_name} not found in {path}')
    end=text.find('fn ', start+10)
    # find next function start at line boundary
    end_candidates=[i for i in [text.find('\nfn ', start+1), text.find('\nfn ', start+10)] if i!=-1]
    end=min(end_candidates) if end_candidates else -1
    if end==-1:
        raise SystemExit('next fn not found')
    new_fn=f'''fn {fn_name}(sparql: &str) -> Option<String> {{
    let decl_re = regex::Regex::new(r"(?i)PREFIX\\s+([^\\s:]+):\\s*<([^>]*)>").ok()?;
    for cap in decl_re.captures_iter(sparql) {{
        let prefix = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let iri = cap.get(2).map(|m| m.as_str()).unwrap_or("");
        if iri.is_empty() || iri.contains('`') || iri.chars().any(|c| c.is_whitespace()) {{
            return Some(format!("Invalid PREFIX declaration for '{{}}': IRI must be a clean <...> value", prefix));
        }}
    }}

    let malformed_re = regex::Regex::new(r"(?i)PREFIX\\s+[^\\s:]+:\\s*(?!<[^>]*>)").ok()?;
    if malformed_re.is_match(sparql) {{
        return Some("Invalid PREFIX declaration syntax".to_string());
    }}

    None
}}

'''
    text=text[:start]+new_fn+text[end+1:]
    p.write_text(text,encoding='utf-8')
    print('rewrote',fn_name,'in',path)

rewrite_fn('/home/yuxiaoyu/rs_ontop_core/src/listener.rs','validate_prefix_declarations_for_http')
rewrite_fn('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs','validate_prefix_declarations')