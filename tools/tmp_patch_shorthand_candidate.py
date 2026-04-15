from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
old='''        if trimmed.starts_with('?') {
            if let Some(first_space) = trimmed.find(' ') {
                *current_subject = Some(trimmed[..first_space].to_string());
            }
            result.push_str(trimmed);
            result.push_str(" .\n");
            return;
        }
'''
new='''        let mut candidate = trimmed.to_string();
        if !candidate.starts_with('?') {
            if let Ok(tail_re) = regex::Regex::new(r"(\?\w+\s+[^\s]+\s+[^.;]+)$") {
                if let Some(cap) = tail_re.captures(&candidate) {
                    candidate = cap.get(1).map(|m| m.as_str()).unwrap_or("").trim().to_string();
                }
            }
        }

        if candidate.starts_with('?') {
            if let Some(first_space) = candidate.find(' ') {
                *current_subject = Some(candidate[..first_space].to_string());
            }
            result.push_str(&candidate);
            result.push_str(" .\n");
            return;
        }
'''
if old not in text:
    raise SystemExit('target starts_with block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched shorthand candidate triple extraction')