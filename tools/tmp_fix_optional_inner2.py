from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/optimizer/rules/left_to_inner.rs')
s=p.read_text(encoding='utf-8')
old='''                      if let LogicNode::ExtensionalData { column_mapping, metadata, .. } = &children[1] {
                          for (_var, col) in column_mapping {
                              if !metadata.not_null_columns.contains(col) {
                                  all_not_null = false;
                                  break;
                              }
                          }
                      } else {
'''
new='''                      if let LogicNode::ExtensionalData { table_name, column_mapping, metadata, .. } = &children[1] {
                          if table_name == "(SELECT 1)" {
                              all_not_null = false;
                          } else {
                              for (_var, col) in column_mapping {
                                  if !metadata.not_null_columns.contains(col) {
                                      all_not_null = false;
                                      break;
                                  }
                              }
                          }
                      } else {
'''
if old not in s:
    raise SystemExit('target left_to_inner extensional block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched left_to_inner: do not convert LEFT JOIN when right is synthetic (SELECT 1)')
