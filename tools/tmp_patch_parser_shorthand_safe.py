from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''        if trimmed.contains("geof:distance") {
            eprintln!("[DBG WHERE_RAW] {}", where_without_subqueries.replace('\n', " "));
            eprintln!("[DBG WHERE_EXPANDED] {}", expanded_where.replace('\n', " "));
        }
''','',1)
text=text.replace('''    let mut in_iri = false;
    let mut current_segment = String::new();
''','''    let mut in_iri = false;
    let mut in_string = false;
    let mut prev_char = '\\0';
    let mut current_segment = String::new();
''',1)
text=text.replace('''        if ch == '<' && !in_iri {
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
''','''        if ch == '<' && !in_iri && !in_string {
            in_iri = true;
            current_segment.push(ch);
        } else if ch == '>' && in_iri && !in_string {
            in_iri = false;
            current_segment.push(ch);
        } else if ch == '"' && !in_iri && prev_char != '\\\\' {
            in_string = !in_string;
            current_segment.push(ch);
        } else if (ch == '.' || ch == ';') && !in_iri && !in_string {
            flush_segment(&current_segment, &mut result, &mut current_subject);
            current_segment.clear();
        } else {
            current_segment.push(ch);
        }
        prev_char = ch;
''',1)
p.write_text(text,encoding='utf-8')
print('patched parser string-safe shorthand + removed debug')