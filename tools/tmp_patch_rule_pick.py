from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

old='''                        store.mappings.get(&pred_iri)
                            .and_then(|rules| rules.first())
                            .and_then(|rule| rule.position_to_column.get(&1))
                            .cloned()'''
new='''                        store.mappings.get(&pred_iri)
                            .and_then(|rules| {
                                rules.iter().find(|rule| {
                                    rule.table_name == table_name
                                        && Self::mapping_rule_is_usable(rule, metadata_map)
                                })
                            })
                            .and_then(|rule| rule.position_to_column.get(&1))
                            .cloned()'''
if old not in s:
    raise SystemExit('object mapped_col block not found')
s=s.replace(old,new,1)

old2='''                              if let Some(col) = store.mappings.get(&pred_iri)
                                  .and_then(|rules| rules.first())
                                  .and_then(|rule| rule.position_to_column.get(&1))
                                  .cloned() {'''
new2='''                              if let Some(col) = store.mappings.get(&pred_iri)
                                  .and_then(|rules| {
                                      rules.iter().find(|rule| {
                                          rule.table_name == table_name
                                              && Self::mapping_rule_is_usable(rule, metadata_map)
                                      })
                                  })
                                  .and_then(|rule| rule.position_to_column.get(&1))
                                  .cloned() {'''
if old2 not in s:
    raise SystemExit('constant mapped col block not found')
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')
print('patched rule selection to current table + usable rule')
