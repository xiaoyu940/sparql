from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

# replace first metadata resolution block in build_core_plan_with_vars loop
pat='''let metadata_opt = Self::resolve_metadata_for_predicate_with_context(
                &pattern.predicate,
                Some(&canonical_subject_for_lookup),
                preferred_table,
                metadata_map,
                mappings
            );

            let metadata = metadata_opt.unwrap_or_else(|| {
                metadata_map.values().next().cloned().unwrap_or_else(|| Arc::new(TableMetadata::default()))
            });'''
rep='''let metadata_opt = if Self::is_rdf_type_predicate(&pattern.predicate) {
                if let Some(store) = mappings {
                    Self::unique_class_table_for_type_pattern(pattern, store)
                        .and_then(|tbl| metadata_map.get(&tbl).cloned())
                } else {
                    None
                }
            } else {
                Self::resolve_metadata_for_predicate_with_context(
                    &pattern.predicate,
                    Some(&canonical_subject_for_lookup),
                    preferred_table,
                    metadata_map,
                    mappings
                )
            };

            let metadata = if let Some(m) = metadata_opt {
                m
            } else {
                impossible_pattern = true;
                break;
            };'''
if pat not in s:
    raise SystemExit('metadata block exact not found')
s=s.replace(pat,rep,1)

pat2='''let mut node = LogicNode::ExtensionalData {
                table_name: table_name.clone(),
                column_mapping,
                metadata: Arc::clone(metadata),
            };

            table_nodes.push((group_key.clone(), node));'''
rep2='''let mut node = LogicNode::ExtensionalData {
                table_name: table_name.clone(),
                column_mapping,
                metadata: Arc::clone(metadata),
            };

            if let Some(filters) = table_filters.get(&group_key) {
                for f in filters {
                    node = LogicNode::Filter {
                        expression: f.clone(),
                        child: Box::new(node),
                    };
                }
            }

            table_nodes.push((group_key.clone(), node));'''
if pat2 not in s:
    raise SystemExit('node block exact not found')
s=s.replace(pat2,rep2,1)

p.write_text(s,encoding='utf-8')
print('directly replaced metadata and node blocks')
