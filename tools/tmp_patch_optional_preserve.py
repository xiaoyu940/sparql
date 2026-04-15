from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text = p.read_text(encoding='utf-8')

text = text.replace(
    '.map(|branch| Self::build_join_from_patterns_with_vars(branch, metadata_map, mappings, &needed_vars))',
    '.map(|branch| Self::build_join_from_patterns_with_vars(branch, metadata_map, mappings, &needed_vars, false))',
    1
)
text = text.replace(
    'Self::build_join_from_patterns_with_vars(&parsed.main_patterns, metadata_map, mappings, &needed_vars);',
    'Self::build_join_from_patterns_with_vars(&parsed.main_patterns, metadata_map, mappings, &needed_vars, false);',
    1
)
text = text.replace(
    'let right = Self::build_join_from_patterns_with_vars(optional, metadata_map, mappings, &needed_vars);',
    'let right = Self::build_join_from_patterns_with_vars(optional, metadata_map, mappings, &needed_vars, true);',
    1
)

text = text.replace(
'''    fn build_join_from_patterns_with_vars(
        patterns: &[super::TriplePattern],
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
        needed_vars: &std::collections::HashSet<String>,
    ) -> LogicNode {
''',
'''    fn build_join_from_patterns_with_vars(
        patterns: &[super::TriplePattern],
        metadata_map: &std::collections::HashMap<String, Arc<TableMetadata>>,
        mappings: Option<&MappingStore>,
        needed_vars: &std::collections::HashSet<String>,
        preserve_on_impossible: bool,
    ) -> LogicNode {
''',
1)

text = text.replace(
'''          if impossible_pattern {
              return LogicNode::Values {
                  variables: Vec::new(),
                  rows: Vec::new(),
              };
          }
''',
'''          if impossible_pattern {
              if preserve_on_impossible {
                  return LogicNode::Values {
                      variables: vec!["__unit".to_string()],
                      rows: vec![vec![Term::Constant("1".to_string())]],
                  };
              }
              return LogicNode::Values {
                  variables: Vec::new(),
                  rows: Vec::new(),
              };
          }
''',
1)

p.write_text(text, encoding='utf-8')
print('patched optional preserve_on_impossible')