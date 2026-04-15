from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/sparql_parser_v2.rs')
s=p.read_text(encoding='utf-8')
start=s.find('pub fn extract_triple_patterns(input: &str) -> Vec<TriplePattern> {')
end=s.find('/// 灞曞紑 SPARQL PREFIX 澹版槑', start)
if start==-1 or end==-1:
    raise SystemExit('extract_triple_patterns markers not found')
new_fn='''pub fn extract_triple_patterns(input: &str) -> Vec<TriplePattern> {
    let expanded = expand_sparql_shorthand(input);
    let expanded_with_prefixes = expand_prefixes(&expanded);
    eprintln!("[DEBUG SPARQL] Expanded input: {:?}", expanded_with_prefixes);

    let mut patterns: Vec<TriplePattern> = Vec::new();

    let re_type_assertion = regex::Regex::new(
        r"(?m)(\?\w+)\s+a\s+<([^>]+)>\s*[.;]"
    ).expect("valid type assertion regex");

    for cap in re_type_assertion.captures_iter(&expanded_with_prefixes) {
        patterns.push(TriplePattern {
            subject: cap[1].to_string(),
            predicate: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string(),
            object: cap[2].to_string(),
        });
    }

    let re_predicate = regex::Regex::new(
        r#"(?m)(\?\w+)\s+([^?\s][^\s]*)\s+(\?\w+|<[^>]+>|\"[^\"]*\"(?:\^\^<[^>]+>)?)\s*[.;]"#
    ).expect("valid predicate regex");

    for cap in re_predicate.captures_iter(&expanded_with_prefixes) {
        let subject = cap[1].to_string();
        let predicate = cap[2].trim().to_string();
        let object = cap[3].to_string();

        if predicate == "a" {
            continue;
        }

        patterns.push(TriplePattern {
            subject,
            predicate,
            object,
        });
    }

    eprintln!(
        "[DEBUG SPARQL] Extracted patterns count: {}, patterns: {:?}",
        patterns.len(),
        patterns
            .iter()
            .map(|p| (&p.subject, &p.predicate, &p.object))
            .collect::<Vec<_>>()
    );
    patterns
}

'''
s=s[:start]+new_fn+s[end:]
p.write_text(s,encoding='utf-8')
print('rewrote extract_triple_patterns to collect type+predicate patterns and support literal objects')
