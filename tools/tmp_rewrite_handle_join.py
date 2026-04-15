from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
start=s.find('fn handle_join(')
end=s.find('/// 澶勭悊 FILTER 鑺傜偣', start)
if start==-1 or end==-1:
    raise SystemExit('handle_join function bounds not found')
new_fn='''fn handle_join(
        &mut self,
        children: &[LogicNode],
        condition: &Option<Expr>,
        join_type: JoinType,
    ) -> Result<(), GenerationError> {
        if children.len() < 2 {
            return Err(GenerationError::InvalidJoin(
                "Join must have at least 2 children".to_string()
            ));
        }

        let mut all_child_items = Vec::new();

        for child in children {
            let start = self.ctx.select_items.len();
            self.traverse_node(child)?;
            let end = self.ctx.select_items.len();
            let items = self.ctx.select_items[start..end].to_vec();
            all_child_items.push(items);
        }

        let mut infer_conditions = |generator: &mut Self| {
            let mut seen_conditions = HashSet::new();
            for i in 0..all_child_items.len() {
                for j in (i + 1)..all_child_items.len() {
                    for item_i in &all_child_items[i] {
                        for item_j in &all_child_items[j] {
                            if item_i.alias == item_j.alias && item_i.expression != item_j.expression {
                                let cond = format!("{} = {}", item_i.expression, item_j.expression);
                                if seen_conditions.insert(cond.clone()) {
                                    if let Err(_) = generator.add_join_condition(&cond, JoinType::Inner) {
                                        generator.ctx.where_conditions.push(Condition {
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
        };

        if condition.is_none() {
            infer_conditions(self);
        }

        if let Some(join_condition) = condition {
            let sql_condition = self.translate_expression(join_condition)?;
            if Self::condition_references_known_columns(&sql_condition, &self.ctx.all_available_items) {
                self.add_join_condition(&sql_condition, join_type)?;
            } else {
                eprintln!("[JOINDBG] skip unresolved explicit condition: {}", sql_condition);
                infer_conditions(self);
            }
        }

        Ok(())
    }

    '''
s=s[:start]+new_fn+s[end:]
p.write_text(s,encoding='utf-8')
print('rewrote handle_join with fallback inferred joins when explicit condition unresolved')
