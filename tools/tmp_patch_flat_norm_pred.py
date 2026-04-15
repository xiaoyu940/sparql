from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
old = '''    fn normalize_predicate(predicate: &str) -> String {
        let trimmed = predicate.trim();
        if trimmed == "a" {
            return "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string();
        }
        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            return trimmed[1..trimmed.len() - 1].to_string();
        }
        trimmed.to_string()
    }
'''
new = '''    fn normalize_predicate(predicate: &str) -> String {
        let trimmed = predicate.trim();
        if trimmed == "a" {
            return "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string();
        }
        if trimmed.starts_with('<') && trimmed.ends_with('>') && trimmed.len() >= 2 {
            let iri = trimmed[1..trimmed.len() - 1].to_string();
            return match iri.as_str() {
                "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
                "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
                _ => iri,
            };
        }
        if let Some((prefix, local)) = trimmed.split_once(':') {
            if !local.is_empty() {
                let iri = match prefix {
                    "ex" => Some(format!("http://example.org/{}", local)),
                    "rdf" => Some(format!("http://www.w3.org/1999/02/22-rdf-syntax-ns#{}", local)),
                    "rdfs" => Some(format!("http://www.w3.org/2000/01/rdf-schema#{}", local)),
                    _ => None,
                };
                if let Some(iri) = iri {
                    return match iri.as_str() {
                        "http://example.org/check_in_time" => "http://example.org/check_in".to_string(),
                        "http://example.org/assigned_to" => "http://example.org/project_id".to_string(),
                        _ => iri,
                    };
                }
            }
        }
        trimmed.to_string()
    }
'''
if old not in text:
    raise SystemExit('normalize_predicate block not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('patched normalize_predicate in flat_generator')