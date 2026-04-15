from pathlib import Path

# patch parser expand shorthand and remove temp debug
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

# patch ir predicate lookup candidates + type-priority already
p2=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text2=p2.read_text(encoding='utf-8')

if 'fn predicate_lookup_candidates(' not in text2:
    anchor='''    fn normalize_predicate_iri_for_lookup(iri: &str) -> String {
'''
    insert='''    fn predicate_lookup_candidates(iri: &str) -> Vec<String> {
        let normalized = Self::normalize_predicate_iri_for_lookup(iri);
        let mut candidates = vec![normalized.clone()];

        let split_pos = normalized.rfind(['#', '/']);
        if let Some(pos) = split_pos {
            let ns = &normalized[..=pos];
            let local = &normalized[pos + 1..];
            if !local.is_empty() {
                if let Some(stripped) = local.strip_prefix("is_") {
                    if !stripped.is_empty() {
                        candidates.push(format!("{}{}", ns, stripped));
                    }
                } else {
                    candidates.push(format!("{}is_{}", ns, local));
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
        let mut out: Vec<&crate::mapping::MappingRule> = Vec::new();
        for cand in Self::predicate_lookup_candidates(iri) {
            if let Some(rules) = store.mappings.get(&cand) {
                for rule in rules {
                    out.push(rule);
                }
            }
        }
        out
    }

'''
    text2=text2.replace(anchor,insert+anchor,1)

# replace mapping get calls
text2=text2.replace('''                              store
                                  .mappings
                                  .get(&pred_iri)
                                  .and_then(|rules| {
                                      rules.iter().find(|rule| {
                                          rule.table_name == table_name
                                              && Self::mapping_rule_is_usable(rule, metadata_map)
                                      })
                                  })
''','''                              Self::lookup_mapping_rules_by_predicate(store, &pred_iri)
                                  .into_iter()
                                  .find(|rule| {
                                      rule.table_name == table_name
                                          && Self::mapping_rule_is_usable(rule, metadata_map)
                                  })
''',1)

text2=text2.replace('''                              store
                                  .mappings
                                  .get(&pred_iri)
                                  .and_then(|rules| {
                                      rules.iter().find(|rule| {
                                          rule.table_name == table_name
                                              && Self::mapping_rule_is_usable(rule, metadata_map)
                                      })
                                  })
''','''                              Self::lookup_mapping_rules_by_predicate(store, &pred_iri)
                                  .into_iter()
                                  .find(|rule| {
                                      rule.table_name == table_name
                                          && Self::mapping_rule_is_usable(rule, metadata_map)
                                  })
''',1)

text2=text2.replace('if let Some(rules) = store.mappings.get(&predicate_iri) {','for rule in Self::lookup_mapping_rules_by_predicate(store, &predicate_iri) {',1)
text2=text2.replace('for rule in rules {','',1)
# close brace count adjust for the replaced block around line ~1190
text2=text2.replace('''                    }
                }
            }
        }
''','''                    }
            }
        }
''',1)

# second/third occurrences for resolve_metadata functions
text2=text2.replace('if let Some(rules) = store.mappings.get(&predicate_iri) {','let rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);
        if !rules.is_empty() {',1)
text2=text2.replace('if let Some(rules) = store.mappings.get(&predicate_iri) {','let rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);
        if !rules.is_empty() {',1)

p2.write_text(text2,encoding='utf-8')
print('patched shorthand string-safe split + generic predicate fallback lookup')