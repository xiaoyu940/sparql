from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
        if class_iri.is_empty() || class_iri.starts_with('?') {
            return None;
        }
        let rules = mappings.mappings.get(class_iri)?;
        let mut tables = std::collections::HashSet::new();
        for rule in rules {
            tables.insert(rule.table_name.clone());
        }
'''
new='''        let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
        if class_iri.is_empty() || class_iri.starts_with('?') {
            return None;
        }

        let class_iri_norm = Self::normalize_predicate_iri_for_lookup(class_iri);
        let mut tables = std::collections::HashSet::new();

        if let Some(rules) = mappings.mappings.get(class_iri) {
            for rule in rules {
                tables.insert(rule.table_name.clone());
            }
        }
        if let Some(rules) = mappings.mappings.get(&class_iri_norm) {
            for rule in rules {
                tables.insert(rule.table_name.clone());
            }
        }

        if tables.is_empty() {
            for (k, rules) in &mappings.mappings {
                if Self::normalize_predicate_iri_for_lookup(k) == class_iri_norm {
                    for rule in rules {
                        tables.insert(rule.table_name.clone());
                    }
                }
            }
        }
'''
if old in text:
    text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched class lookup normalization for rdf:type resolution')