from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')

# Replace extract_union_patterns
pat_union=r"fn extract_union_patterns\(where_block: &str\) -> Vec<Vec<TriplePattern>> \{[\s\S]*?\n\}\n\nfn extract_vars_from_expr"
new_union='''fn extract_union_patterns(where_block: &str) -> Vec<Vec<TriplePattern>> {
    let mut parts: Vec<&str> = Vec::new();
    let mut depth = 0i32;
    let mut start = 0usize;
    let upper = where_block.to_ascii_uppercase();
    let bytes = where_block.as_bytes();

    let mut i = 0usize;
    while i < bytes.len() {
        let ch = bytes[i] as char;
        if ch == '{' {
            depth += 1;
            i += 1;
            continue;
        }
        if ch == '}' {
            depth -= 1;
            i += 1;
            continue;
        }

        if depth == 0 && upper[i..].starts_with("UNION") {
            let seg = where_block[start..i].trim();
            if !seg.is_empty() {
                parts.push(seg);
            }
            i += 5;
            start = i;
            continue;
        }

        i += 1;
    }

    let tail = where_block[start..].trim();
    if !tail.is_empty() {
        parts.push(tail);
    }

    if parts.len() < 2 {
        return Vec::new();
    }

    let mut out = Vec::new();
    for seg in parts {
        let s = seg.trim();
        let inner = if s.starts_with('{') && s.ends_with('}') {
            &s[1..s.len() - 1]
        } else {
            s
        };
        let patterns = extract_triple_patterns(inner);
        if !patterns.is_empty() {
            out.push(patterns);
        }
    }
    out
}

fn extract_vars_from_expr'''
text2,n=re.subn(pat_union,new_union,text,count=1)
if n!=1:
    raise SystemExit(f'union replace failed {n}')
text=text2

# Replace expand_sparql_shorthand
pat_short=r"fn expand_sparql_shorthand\(input: &str\) -> String \{[\s\S]*?\n\}\n\n\n\nfn strip_optional_blocks"
new_short='''fn expand_sparql_shorthand(input: &str) -> String {
    fn is_control_segment(seg: &str) -> bool {
        let up = seg.trim_start().to_ascii_uppercase();
        [
            "FILTER", "BIND", "VALUES", "OPTIONAL", "UNION", "GRAPH", "SERVICE", "MINUS",
            "ORDER", "GROUP", "HAVING", "LIMIT", "SELECT", "WHERE", "PREFIX", "FROM", "CONSTRUCT",
            "ASK", "DESCRIBE"
        ].iter().any(|k| up.starts_with(k))
    }

    let mut result = String::new();
    let mut current_subject: Option<String> = None;
    let mut in_iri = false;
    let mut current_segment = String::new();

    let mut flush_segment = |seg: &str, result: &mut String, current_subject: &mut Option<String>| {
        let trimmed = seg.trim();
        if trimmed.is_empty() {
            return;
        }

        if trimmed.starts_with('?') {
            if let Some(first_space) = trimmed.find(' ') {
                *current_subject = Some(trimmed[..first_space].to_string());
            }
            result.push_str(trimmed);
            result.push_str(" .\n");
            return;
        }

        if is_control_segment(trimmed) {
            return;
        }

        if let Some(subject) = current_subject.as_ref() {
            let mut toks = trimmed.split_whitespace();
            let first = toks.next().unwrap_or("");
            let second = toks.next().unwrap_or("");
            if !first.is_empty() && !second.is_empty() {
                result.push_str(subject);
                result.push(' ');
                result.push_str(trimmed);
                result.push_str(" .\n");
            }
        }
    };

    for ch in input.chars() {
        if ch == '<' && !in_iri {
            in_iri = true;
            current_segment.push(ch);
        } else if ch == '>' && in_iri {
            in_iri = false;
            current_segment.push(ch);
        } else if (ch == '.' || ch == ';') && !in_iri {
            flush_segment(&current_segment, &mut result, &mut current_subject);
            current_segment.clear();
        } else {
            current_segment.push(ch);
        }
    }

    flush_segment(&current_segment, &mut result, &mut current_subject);

    if result.is_empty() { input.to_string() } else { result }
}



fn strip_optional_blocks'''
text2,n=re.subn(pat_short,new_short,text,count=1)
if n!=1:
    raise SystemExit(f'shorthand replace failed {n}')
text=text2

p.write_text(text,encoding='utf-8')
print('patched union extraction + shorthand expansion generically')