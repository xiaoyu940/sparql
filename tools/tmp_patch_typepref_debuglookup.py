from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('''              if Self::is_rdf_type_predicate(&pattern.predicate) {
                  subject_preferred_table
                      .entry(canonical_subject.clone())
                      .or_insert(table_name_hint.clone());
              } else {
                  subject_preferred_table.insert(canonical_subject.clone(), table_name_hint.clone());
              }
''','''              if Self::is_rdf_type_predicate(&pattern.predicate) {
                  subject_preferred_table.insert(canonical_subject.clone(), table_name_hint.clone());
              } else {
                  subject_preferred_table
                      .entry(canonical_subject.clone())
                      .or_insert(table_name_hint.clone());
              }
''',1)
text=text.replace('if let Some(rules) = store.mappings.get(&predicate_iri) {','let rules = Self::lookup_mapping_rules_by_predicate(store, &predicate_iri);\n                  if !rules.is_empty() {',1)
p.write_text(text,encoding='utf-8')
print('patched type-priority overwrite and debug lookup fallback')