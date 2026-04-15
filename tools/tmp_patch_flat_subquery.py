from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')

s=s.replace('''            LogicNode::SubQuery { .. } => {
                // [S8-P0-4] SubQuery handling placeholder
                return Err(GenerationError::Other("SubQuery not yet implemented".to_string()));
            }
            LogicNode::CorrelatedJoin { .. } => {
                // [S8-P0-4] CorrelatedJoin handling placeholder
                return Err(GenerationError::Other("CorrelatedJoin not yet implemented".to_string()));
            }''','''            LogicNode::SubQuery { inner, correlated_vars } => {
                self.handle_subquery(inner, correlated_vars)?;
            }
            LogicNode::CorrelatedJoin { outer, inner, correlated_vars } => {
                self.traverse_node(outer)?;
                self.handle_subquery(inner, correlated_vars)?;
            }''',1)

insert_anchor='''    fn format_values_constant(value: &str) -> String {'''
if 'fn handle_subquery(' not in s:
    helper='''    fn collect_output_vars(node: &LogicNode) -> Vec<String> {
        match node {
            LogicNode::Construction { projected_vars, .. } => projected_vars.clone(),
            LogicNode::Limit { child, .. } => Self::collect_output_vars(child),
            LogicNode::Filter { child, .. } => Self::collect_output_vars(child),
            LogicNode::Aggregation { group_by, aggregates, .. } => {
                let mut vars = group_by.clone();
                vars.extend(aggregates.keys().cloned());
                vars
            }
            LogicNode::ExtensionalData { column_mapping, .. } => column_mapping.keys().cloned().collect(),
            LogicNode::Values { variables, .. } => variables.clone(),
            LogicNode::Join { children, .. } => {
                let mut vars = Vec::new();
                for c in children {
                    vars.extend(Self::collect_output_vars(c));
                }
                vars.sort();
                vars.dedup();
                vars
            }
            _ => Vec::new(),
        }
    }

    fn handle_subquery(&mut self, inner: &LogicNode, correlated_vars: &[String]) -> Result<(), GenerationError> {
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
                    expression: expr.clone(),
                    alias: v.clone(),
                    is_aggregate: false,
                });
            }
        }

        Ok(())
    }

'''
    idx=s.find(insert_anchor)
    if idx==-1:
        raise SystemExit('insert anchor not found')
    s=s[:idx]+helper+s[idx:]

p.write_text(s,encoding='utf-8')
print('patched flat generator with SubQuery/CorrelatedJoin support')
