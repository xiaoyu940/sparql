from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')

# 1) GeneratorContext add pending_join_type field
old='''    /// 记录所有扫描过的表产生的变量（用于 HAVING 引用那些不在最终 SELECT 中的列）
    all_available_items: Vec<SelectItem>,
}
'''
new='''    /// 记录所有扫描过的表产生的变量（用于 HAVING 引用那些不在最终 SELECT 中的列）
    all_available_items: Vec<SelectItem>,
    /// 当前遍历子节点时的连接语义（用于 VALUES 空集等上下文敏感生成）
    pending_join_type: Option<JoinType>,
}
'''
if old not in s:
    raise SystemExit('GeneratorContext field block not found')
s=s.replace(old,new,1)

# 2) handle_join loop with index and pending_join_type
old='''          for child in children {
              let start = self.ctx.select_items.len();
              self.traverse_node(child)?;
              let end = self.ctx.select_items.len();
              let items = self.ctx.select_items[start..end].to_vec();
              all_child_items.push(items);
          }
'''
new='''          for (idx, child) in children.iter().enumerate() {
              let prev_pending = self.ctx.pending_join_type;
              self.ctx.pending_join_type = if idx == 0 { None } else { Some(join_type) };

              let start = self.ctx.select_items.len();
              self.traverse_node(child)?;
              let end = self.ctx.select_items.len();
              let items = self.ctx.select_items[start..end].to_vec();
              all_child_items.push(items);

              self.ctx.pending_join_type = prev_pending;
          }
'''
if old not in s:
    raise SystemExit('handle_join children loop block not found')
s=s.replace(old,new,1)

# 3) infer join condition uses current join_type (not always inner)
s=s.replace('if let Err(_) = generator.add_join_condition(&cond, JoinType::Inner) {','if let Err(_) = generator.add_join_condition(&cond, join_type) {',1)

# 4) alias_exprs fallback should not force LEFT JOIN into WHERE equalities
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
    raise SystemExit('alias_exprs fallback block not found')
s=s.replace(old,new,1)

# 5) handle_values empty rows: context-sensitive false handling
old='''          if row_sqls.is_empty() {
              let alias = self.alias_manager.allocate_table_alias("vals_empty");
              let is_first = self.ctx.from_tables.is_empty();
              self.ctx.from_tables.push(FromTable {
                  table_name: "(SELECT 1)".to_string(),
                  alias,
                  join_type: if is_first { None } else { Some(JoinType::Inner) },
                  join_condition: if is_first { None } else { Some("FALSE".to_string()) },
                  is_subquery: true,
                  subquery_sql: None,
              });
              self.ctx.where_conditions.push(Condition {
                  expression: "FALSE".to_string(),
                  condition_type: ConditionType::Filter,
              });
              return Ok(());
          }
'''
new='''          if row_sqls.is_empty() {
              let alias = self.alias_manager.allocate_table_alias("vals_empty");
              let is_first = self.ctx.from_tables.is_empty();
              let effective_join = if is_first {
                  None
              } else {
                  Some(self.ctx.pending_join_type.unwrap_or(JoinType::Inner))
              };

              self.ctx.from_tables.push(FromTable {
                  table_name: "(SELECT 1)".to_string(),
                  alias,
                  join_type: effective_join,
                  join_condition: if is_first { None } else { Some("FALSE".to_string()) },
                  is_subquery: true,
                  subquery_sql: None,
              });

              if is_first || effective_join == Some(JoinType::Inner) {
                  self.ctx.where_conditions.push(Condition {
                      expression: "FALSE".to_string(),
                      condition_type: ConditionType::Filter,
                  });
              }
              return Ok(());
          }
'''
if old not in s:
    raise SystemExit('handle_values empty block not found')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('patched flat_generator for context-aware empty VALUES and LEFT JOIN-safe inference')
