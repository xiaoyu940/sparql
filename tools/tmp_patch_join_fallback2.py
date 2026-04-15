from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
pattern=r"if condition\.is_none\(\) \{[\s\S]*?\n\s*\}\n\n\s*//[\s\S]*?if let Some\(join_condition\) = condition \{" 
m=re.search(pattern,s)
if not m:
    # fallback: locate between if condition.is_none and if let Some(join_condition)
    start=s.find('if condition.is_none() {')
    end=s.find('if let Some(join_condition) = condition {',start)
    if start==-1 or end==-1:
        raise SystemExit('unable to locate handle_join condition block')
    head=s[:start]
    tail=s[end:]
else:
    start,end=m.start(),m.end()
    head=s[:start]
    tail='if let Some(join_condition) = condition {'+s[s.find('if let Some(join_condition) = condition {',start)+len('if let Some(join_condition) = condition {'):]

new_block='''if condition.is_none() {
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
        }

        '''
s2=head+new_block+tail
p.write_text(s2,encoding='utf-8')
print('patched handle_join condition.is_none block with alias-level fallback')
