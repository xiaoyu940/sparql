from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
anchor='''          if condition.is_none() {
              let mut seen_conditions = HashSet::new();
              for i in 0..all_child_items.len() {'''
if anchor not in s:
    raise SystemExit('handle_join auto condition anchor not found')

insert='''          if condition.is_none() {
              let mut seen_conditions = HashSet::new();
              for i in 0..all_child_items.len() {
                  for j in (i + 1)..all_child_items.len() {
                      for item_i in &all_child_items[i] {
                          for item_j in &all_child_items[j] {
                              if item_i.alias == item_j.alias && item_i.expression != item_j.expression {
                                  let cond = format!("{} = {}", item_i.expression, item_j.expression);
                                  if seen_conditions.insert(cond.clone()) {
                                      if let Err(_) = self.add_join_condition(&cond, JoinType::Inner) {
                                          self.ctx.where_conditions.push(Condition {
                                              expression: cond,
                                              condition_type: ConditionType::Join,
                                          });
                                      }
                                  }
                              }
                          }
                      }
                  }
              }

              let mut alias_exprs: HashMap<String, Vec<String>> = HashMap::new();
              for item in &self.ctx.all_available_items {
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
                              self.ctx.where_conditions.push(Condition {
                                  expression: cond,
                                  condition_type: ConditionType::Join,
                              });
                          }
                      }
                  }
              }
          }'''
# Replace whole existing condition.is_none block by locating start/end
start=s.find('if condition.is_none() {')
end=s.find('// 添加显式 JOIN 条件', start)
if start==-1 or end==-1:
    raise SystemExit('condition.is_none block bounds not found')
# keep indentation as existing (10 spaces?) using insert exactly
s=s[:start]+insert+s[end:]
p.write_text(s,encoding='utf-8')
print('patched handle_join with alias-level fallback join equality conditions')
