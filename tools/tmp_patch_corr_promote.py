from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

# 1) sub_plan mutable + promote correlated vars
s=s.replace('let sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);','let mut sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);',1)
old='''            let correlated_vars: Vec<String> = sub_bindings
                .keys()
                .filter(|v| core_bindings.contains_key(*v))
                .cloned()
                .collect();

            let sub_node = LogicNode::SubQuery {'''
new='''            let correlated_vars: Vec<String> = sub_bindings
                .keys()
                .filter(|v| core_bindings.contains_key(*v))
                .cloned()
                .collect();

            if !correlated_vars.is_empty() {
                sub_plan = Self::promote_correlated_vars(sub_plan, &correlated_vars);
            }

            let sub_node = LogicNode::SubQuery {'''
if old not in s:
    raise SystemExit('correlated vars block not found')
s=s.replace(old,new,1)

# 2) add helper function
if 'fn promote_correlated_vars(' not in s:
    ins=s.find('fn resolve_var_alias(var: &str, aliases: &HashMap<String, String>) -> String {')
    if ins==-1:
        raise SystemExit('resolve_var_alias marker not found')
    helper='''    fn promote_correlated_vars(node: LogicNode, correlated_vars: &[String]) -> LogicNode {
        match node {
            LogicNode::Construction { mut projected_vars, mut bindings, child } => {
                for v in correlated_vars {
                    if !projected_vars.contains(v) {
                        projected_vars.push(v.clone());
                    }
                    bindings
                        .entry(v.clone())
                        .or_insert_with(|| Expr::Term(Term::Variable(v.clone())));
                }

                let promoted_child = match *child {
                    LogicNode::Aggregation { mut group_by, aggregates, having, child } => {
                        for v in correlated_vars {
                            if !group_by.contains(v) {
                                group_by.push(v.clone());
                            }
                        }
                        LogicNode::Aggregation {
                            group_by,
                            aggregates,
                            having,
                            child,
                        }
                    }
                    other => other,
                };

                LogicNode::Construction {
                    projected_vars,
                    bindings,
                    child: Box::new(promoted_child),
                }
            }
            other => other,
        }
    }

'''
    s=s[:ins]+helper+s[ins:]

# 3) restore aggregation extract bindings including child vars
old_agg='''            LogicNode::Aggregation { group_by, aggregates, .. } => {
                for v in group_by {
                    bindings.insert(v.clone(), v.clone());
                }
                for v in aggregates.keys() {
                    bindings.insert(v.clone(), v.clone());
                }
            }'''
new_agg='''            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                bindings.extend(Self::extract_var_bindings(child));
                for v in group_by {
                    bindings.insert(v.clone(), v.clone());
                }
                for v in aggregates.keys() {
                    bindings.insert(v.clone(), v.clone());
                }
            }'''
if old_agg not in s:
    raise SystemExit('aggregation arm for extract_var_bindings not found')
s=s.replace(old_agg,new_agg,1)

p.write_text(s,encoding='utf-8')
print('patched correlated subquery promotion + restored aggregation binding propagation')
