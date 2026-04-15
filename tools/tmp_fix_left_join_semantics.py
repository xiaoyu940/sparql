from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
s=s.replace('if let Err(_) = generator.add_join_condition(&cond, JoinType::Inner) {','if let Err(_) = generator.add_join_condition(&cond, join_type) {',1)
old='''              let mut alias_exprs: HashMap<String, Vec<String>> = HashMap::new();
              for item in &generator.ctx.all_available_items {
                  let entry = alias_exprs.entry(item.alias.clone()).or_default();
                  if !entry.contains(&item.expression) {
                      entry.push(item.expression.clone());
                  }
              }
              for exprs in alias_exprs.values() {
                  if exprs.len() > 1 {
                      for e in exprs.iter().skip(1) {
                          let cond = format!("{} = {}", exprs[0], e);
                          if seen_conditions.insert(cond.clone()) {
                              generator.ctx.where_conditions.push(Condition {
                                  expression: cond,
                                  condition_type: ConditionType::Join,
                              });
                          }
                      }
                  }
              }
'''
new='''              if join_type != JoinType::Left {
                  let mut alias_exprs: HashMap<String, Vec<String>> = HashMap::new();
                  for item in &generator.ctx.all_available_items {
                      let entry = alias_exprs.entry(item.alias.clone()).or_default();
                      if !entry.contains(&item.expression) {
                          entry.push(item.expression.clone());
                      }
                  }
                  for exprs in alias_exprs.values() {
                      if exprs.len() > 1 {
                          for e in exprs.iter().skip(1) {
                              let cond = format!("{} = {}", exprs[0], e);
                              if seen_conditions.insert(cond.clone()) {
                                  generator.ctx.where_conditions.push(Condition {
                                      expression: cond,
                                      condition_type: ConditionType::Join,
                                  });
                              }
                          }
                      }
                  }
              }
'''
if old not in s:
    raise SystemExit('alias_exprs block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched join inference to preserve LEFT JOIN semantics')
