from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
pattern=r'fn extract_select_distinct\(sparql: &str\) -> bool \{[\s\S]*?\n\}\n\nfn strip_filter_exists_blocks'
new='''fn extract_select_distinct(sparql: &str) -> bool {
    let re = regex::Regex::new(
        r"(?is)^(?:\s*(?:PREFIX\s+[^\s:]+:\s*<[^>]+>|BASE\s+<[^>]+>)\s*)*SELECT\s+DISTINCT"
    ).expect("valid DISTINCT regex");
    re.is_match(sparql.trim())
}

fn strip_filter_exists_blocks'''
text2,n=re.subn(pattern,new,text,count=1)
if n!=1:
    raise SystemExit(f'could not replace distinct fn: {n}')
p.write_text(text2,encoding='utf-8')
print('rewrote extract_select_distinct safely')