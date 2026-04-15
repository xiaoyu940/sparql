from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
old='''            let pattern = format!(r"{}:(\\w+)(?=\\W|$)", prefix);
            let re = Regex::new(&pattern).expect("valid regex");
            text = re
                .replace_all(&text, |caps: &regex::Captures| {
                    format!("<{}{}>", namespace, &caps[1])
                })
                .to_string();'''
new='''            let pattern = format!(r"{}:(\\w+)\\b", regex::escape(prefix));
            if let Ok(re) = Regex::new(&pattern) {
                text = re
                    .replace_all(&text, |caps: &regex::Captures| {
                        format!("<{}{}>", namespace, &caps[1])
                    })
                    .to_string();
            }'''
if old not in s:
    raise SystemExit('target prefix regex block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched prefix expansion regex to remove unsupported lookahead')
