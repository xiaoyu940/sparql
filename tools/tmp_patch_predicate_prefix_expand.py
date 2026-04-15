from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')
old = '''    fn normalize_predicate_iri_for_lookup(iri: &str) -> String {
        match iri {
            "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
            "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
            _ => iri.to_string(),
        }
    }
'''
new = '''    fn normalize_predicate_iri_for_lookup(iri: &str) -> String {
        let expanded = if let Some((prefix, local)) = iri.split_once(':') {
            if !local.is_empty() {
                match prefix {
                    "ex" => format!("http://example.org/{}", local),
                    "rdf" => format!("http://www.w3.org/1999/02/22-rdf-syntax-ns#{}", local),
                    "rdfs" => format!("http://www.w3.org/2000/01/rdf-schema#{}", local),
                    _ => iri.to_string(),
                }
            } else {
                iri.to_string()
            }
        } else {
            iri.to_string()
        };

        match expanded.as_str() {
            "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
            "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
            _ => expanded,
        }
    }
'''
if old not in text:
    raise SystemExit('normalize function block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched predicate prefix expansion')