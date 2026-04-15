from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')

# improve source_var lookup and remove unsafe fallback
s=s.replace('''                          if let Some(existing) = child_items.iter()
                              .find(|item| item.alias == *source_var || item.alias == source_expected_alias || item.alias == format!("col_{}", source_var)) {
                              // 浣跨敤鐩稿悓鐨勮〃杈惧紡锛屼絾鍒 悕涓?var_name
                              new_select_items.push(SelectItem {   
                                  expression: existing.expression.clone(),
                                  alias: var_name.clone(),
                                  is_aggregate: existing.is_aggregate,
                              });
                              continue;
                          }''','''                          if let Some(existing) = child_items.iter()
                              .find(|item| item.alias == *source_var || item.alias == source_expected_alias || item.alias == format!("col_{}", source_var)) {
                              new_select_items.push(SelectItem {
                                  expression: existing.expression.clone(),
                                  alias: var_name.clone(),
                                  is_aggregate: existing.is_aggregate,
                              });
                              continue;
                          }
                          if let Some(existing) = self.ctx.all_available_items.iter()
                              .find(|item| item.alias == *source_var || item.alias == source_expected_alias || item.alias == format!("col_{}", source_var)) {
                              new_select_items.push(SelectItem {
                                  expression: existing.expression.clone(),
                                  alias: var_name.clone(),
                                  is_aggregate: existing.is_aggregate,
                              });
                              continue;
                          }''',1)

s=s.replace('''              // 鏈€鍚庣殑 fallback锛氬皾璇曚粠 child_items 鍙栫涓€涓?   839                  if let Some(first) = child_items.first() {   
                  new_select_items.push(SelectItem {
                      expression: first.expression.clone(),        
                      alias: var_name.clone(),
                      is_aggregate: first.is_aggregate,
                  });
              }''','''              if let Some(existing) = self.ctx.all_available_items.iter()
                  .find(|item| item.alias == *var_name || item.alias == expected_alias || item.alias == format!("col_{}", var_name)) {
                  new_select_items.push(SelectItem {
                      expression: existing.expression.clone(),
                      alias: var_name.clone(),
                      is_aggregate: existing.is_aggregate,
                  });
              }''',1)

old_sub='''    fn handle_subquery(&mut self, inner: &LogicNode, correlated_vars: &[String]) -> Result<(), GenerationError> {
        let mut child_gen = self.child_generator();
        let sub_sql = child_gen.generate(inner)?;
        let sub_alias = self.alias_manager.allocate_table_alias("sq");

        let is_first = self.ctx.from_tables.is_empty();
        let join_condition = if is_first {
            None
        } else if correlated_vars.is_empty() {
            Some("TRUE".to_string())
        } else {
            let mut conds: Vec<String> = Vec::new();
            for v in correlated_vars {
                if let Some(item) = self.ctx.all_available_items.iter().find(|i| i.alias == *v) {
                    conds.push(format!("{} = {}.{}", item.expression, sub_alias, v.trim_start_matches('?')));
                }
            }
            if conds.is_empty() { Some("TRUE".to_string()) } else { Some(conds.join(" AND ")) }
        };

        self.ctx.from_tables.push(FromTable {
            table_name: format!("({})", sub_sql),
            alias: sub_alias.clone(),
            join_type: if is_first { None } else { Some(JoinType::Inner) },
            join_condition,
            is_subquery: true,
            subquery_sql: Some(sub_sql),
        });

        for v in Self::collect_output_vars(inner) {
            let col = v.trim_start_matches('?').to_string();     
            let expr = format!("{}.{}", sub_alias, col);
            if !self.ctx.all_available_items.iter().any(|i| i.alias == v) {
                self.ctx.all_available_items.push(SelectItem {   
                    expression: expr,
                    alias: v,
                    is_aggregate: false,
                });
            }
        }

        Ok(())
    }'''
new_sub='''    fn handle_subquery(&mut self, inner: &LogicNode, correlated_vars: &[String]) -> Result<(), GenerationError> {
        let mut child_gen = self.child_generator();
        let sub_sql = child_gen.generate(inner)?;
        let sub_alias = self.alias_manager.allocate_table_alias("sq");
        let output_vars = Self::collect_output_vars(inner);

        let mut projections: Vec<String> = Vec::new();
        let mut alias_pairs: Vec<(String, String)> = Vec::new();
        for v in &output_vars {
            let source_col = v.trim_start_matches('?').to_string();
            let alias_col = self.alias_manager.allocate_var_alias(v);
            projections.push(format!("sub_inner.{} AS {}", source_col, alias_col));
            alias_pairs.push((v.clone(), alias_col));
        }
        let wrapped_sql = if projections.is_empty() {
            format!("SELECT * FROM ({}) AS sub_inner", sub_sql)
        } else {
            format!("SELECT {} FROM ({}) AS sub_inner", projections.join(", "), sub_sql)
        };

        let is_first = self.ctx.from_tables.is_empty();
        let join_condition = if is_first {
            None
        } else if correlated_vars.is_empty() {
            Some("TRUE".to_string())
        } else {
            let mut conds: Vec<String> = Vec::new();
            for v in correlated_vars {
                let v_alias = self.alias_manager.allocate_var_alias(v);
                if let Some(item) = self.ctx.all_available_items.iter().find(|i| i.alias == v_alias || i.alias == *v) {
                    conds.push(format!("{} = {}.{}", item.expression, sub_alias, v_alias));
                }
            }
            if conds.is_empty() { Some("TRUE".to_string()) } else { Some(conds.join(" AND ")) }
        };

        self.ctx.from_tables.push(FromTable {
            table_name: format!("({})", wrapped_sql),
            alias: sub_alias.clone(),
            join_type: if is_first { None } else { Some(JoinType::Inner) },
            join_condition,
            is_subquery: true,
            subquery_sql: Some(wrapped_sql),
        });

        for (raw_var, alias_col) in alias_pairs {
            let expr = format!("{}.{}", sub_alias, alias_col);
            if !self.ctx.all_available_items.iter().any(|i| i.alias == alias_col) {
                self.ctx.all_available_items.push(SelectItem {
                    expression: expr.clone(),
                    alias: alias_col,
                    is_aggregate: false,
                });
            }
            if !self.ctx.all_available_items.iter().any(|i| i.alias == raw_var) {
                self.ctx.all_available_items.push(SelectItem {
                    expression: expr,
                    alias: raw_var,
                    is_aggregate: false,
                });
            }
        }

        Ok(())
    }'''
if old_sub not in s:
    raise SystemExit('old handle_subquery block not found')
s=s.replace(old_sub,new_sub,1)

p.write_text(s,encoding='utf-8')
print('patched handle_construction fallback + robust handle_subquery alias wrapping')
