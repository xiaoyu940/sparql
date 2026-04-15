from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')

s=s.replace('let sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);','let mut sub_plan = Self::convert_with_mappings(sub_parsed, metadata_map, mappings);',1)

old='''            let correlated_vars: Vec<String> = sub_vars
                .into_iter()
                .filter(|v| core_bindings.contains_key(v))
                .collect();

            let sub_node = LogicNode::SubQuery {'''
new='''            let correlated_vars: Vec<String> = sub_vars
                .into_iter()
                .filter(|v| core_bindings.contains_key(v))
                .collect();

            if !correlated_vars.is_empty() {
                sub_plan = Self::promote_correlated_vars(sub_plan, &correlated_vars);
            }

            let sub_node = LogicNode::SubQuery {'''
if old not in s:
    raise SystemExit('correlated vars block not found for promote insertion')
s=s.replace(old,new,1)

if 'fn promote_correlated_vars(node: LogicNode, correlated_vars: &[String]) -> LogicNode {' not in s:
    ins=s.find('fn collect_query_vars(parsed: &ParsedQuery) -> HashSet<String> {')
    if ins==-1:
        raise SystemExit('collect_query_vars marker not found')
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

p.write_text(s,encoding='utf-8')
print('patched correlated subquery promotion for aggregation/group-by join keys')
