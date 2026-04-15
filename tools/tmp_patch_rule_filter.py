from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

# Insert helper near metadata resolvers
anchor='''    fn resolve_metadata_for_predicate(
        predicate: &str,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
    ) -> Option<Arc<TableMetadata>> {'''
helper='''    fn mapping_rule_is_usable(
        rule: &crate::mapping::MappingRule,
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
    ) -> bool {
        let Some(metadata) = metadata_map.get(&rule.table_name) else {
            return false;
        };
        if metadata.columns.is_empty() {
            return false;
        }

        if let Some(subject_col) = Self::extract_column_from_template(&rule.subject_template) {
            if !metadata.columns.iter().any(|c| c == &subject_col) {
                return false;
            }
        }

        for col in rule.position_to_column.values() {
            if !metadata.columns.iter().any(|c| c == col) {
                return false;
            }
        }

        true
    }

'''
if 'fn mapping_rule_is_usable(' not in s:
    idx=s.find(anchor)
    if idx==-1:
        raise SystemExit('resolver anchor not found')
    s=s[:idx]+helper+s[idx:]

old1='''          if let Some(rules) = store.mappings.get(predicate_iri) {
              if let Some(rule) = rules.first() {
                  if let Some(metadata) = metadata_map.get(&rule.table_name) {
                      return Some(Arc::clone(metadata));
                  }
              }
          }

          for (mapped_pred, rules) in &store.mappings {
              if mapped_pred.ends_with(predicate_iri) || predicate_iri.ends_with(mapped_pred) {
                  if let Some(rule) = rules.first() {
                      if let Some(metadata) = metadata_map.get(&rule.table_name) {
                          return Some(Arc::clone(metadata));
                      }
                  }
              }
          }'''
new1='''          if let Some(rules) = store.mappings.get(predicate_iri) {
              for rule in rules {
                  if Self::mapping_rule_is_usable(rule, metadata_map) {
                      if let Some(metadata) = metadata_map.get(&rule.table_name) {
                          return Some(Arc::clone(metadata));
                      }
                  }
              }
          }

          for (mapped_pred, rules) in &store.mappings {
              if mapped_pred.ends_with(predicate_iri) || predicate_iri.ends_with(mapped_pred) {
                  for rule in rules {
                      if Self::mapping_rule_is_usable(rule, metadata_map) {
                          if let Some(metadata) = metadata_map.get(&rule.table_name) {
                              return Some(Arc::clone(metadata));
                          }
                      }
                  }
              }
          }'''
if old1 not in s:
    raise SystemExit('resolve_metadata_for_predicate block not found')
s=s.replace(old1,new1,1)

old2='''        if matching_rules.is_empty() {
            return None;
        }

        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }'''
new2='''        matching_rules.retain(|r| Self::mapping_rule_is_usable(r, metadata_map));
        if matching_rules.is_empty() {
            return None;
        }

        if matching_rules.len() == 1 {
            let rule = matching_rules[0];
            return metadata_map.get(&rule.table_name).map(Arc::clone);
        }'''
if old2 not in s:
    raise SystemExit('matching_rules filter anchor not found')
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')
print('patched metadata resolver with usable-rule filtering')
