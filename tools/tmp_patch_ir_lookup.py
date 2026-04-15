from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')

if 'fn lookup_mapping_rules_by_predicate' not in text:
    marker='    fn predicate_local_name(iri: &str) -> String {'
    helper="""    fn predicate_lookup_candidates(iri: &str) -> Vec<String> {
        let normalized = Self::normalize_predicate_iri_for_lookup(iri);
        let mut candidates = vec![normalized.clone()];

        if let Some(pos) = normalized.rfind(['#', '/']) {
            let ns = &normalized[..=pos];
            let local = &normalized[pos + 1..];
            if !local.is_empty() {
                if let Some(stripped) = local.strip_prefix(\"is_\") {
                    if !stripped.is_empty() {
                        candidates.push(format!(\"{}{}\", ns, stripped));
                    }
                } else {
                    candidates.push(format!(\"{}is_{}\", ns, local));
                }
            }
        }

        candidates.sort();
        candidates.dedup();
        candidates
    }

    fn lookup_mapping_rules_by_predicate<'a>(
        store: &'a MappingStore,
        iri: &str,
    ) -> Vec<&'a crate::mapping::MappingRule> {
        let mut out = Vec::new();
        for cand in Self::predicate_lookup_candidates(iri) {
            if let Some(rules) = store.mappings.get(&cand) {
                out.extend(rules.iter());
            }
        }
        out
    }

"""
    text=text.replace(marker, helper+marker, 1)

text=text.replace("""                                store
                                    .mappings
                                    .get(&pred_iri)
                                    .and_then(|rules| {
                                        rules.iter().find(|rule| {
                                            rule.table_name == table_name
                                                && Self::mapping_rule_is_usable(rule, metadata_map)
                                        })
                                    })
""","""                                Self::lookup_mapping_rules_by_predicate(store, &pred_iri)
                                    .into_iter()
                                    .find(|rule| {
                                        rule.table_name == table_name
                                            && Self::mapping_rule_is_usable(rule, metadata_map)
                                    })
""",2)

text=text.replace("""        if let Some(rules) = store.mappings.get(&predicate_iri) {
            for rule in rules {
                if Self::mapping_rule_is_usable(rule, metadata_map) {
                    if let Some(metadata) = metadata_map.get(&rule.table_name) {
                        return Some(Arc::clone(metadata));
                    }
                }
            }
        }
""","""        let rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);
        for rule in rules {
            if Self::mapping_rule_is_usable(rule, metadata_map) {
                if let Some(metadata) = metadata_map.get(&rule.table_name) {
                    return Some(Arc::clone(metadata));
                }
            }
        }
""",1)

text=text.replace("""        let mut matching_rules = Vec::new();
        if let Some(rules) = store.mappings.get(&predicate_iri) {
            matching_rules.extend(rules.iter());
        }
""","""        let mut matching_rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);
""",1)

text=text.replace("""                  if let Some(rules) = store.mappings.get(&predicate_iri) {
                      eprintln!(\"[DEBUG IRConverter] Found {} rules for {}\", rules.len(), predicate_iri);
                      if let Some(rule) = rules.iter().find(|rule| rule.table_name == metadata.table_name && rule.position_to_column.values().all(|col| metadata.columns.iter().any(|c| c == col))) {
""","""                  let rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);
                  if !rules.is_empty() {
                      eprintln!(\"[DEBUG IRConverter] Found {} rules for {}\", rules.len(), predicate_iri);
                      if let Some(rule) = rules.iter().find(|rule| rule.table_name == metadata.table_name && rule.position_to_column.values().all(|col| metadata.columns.iter().any(|c| c == col))) {
""",1)

p.write_text(text,encoding='utf-8')
print('patched ir converter lookup candidates')