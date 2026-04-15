from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
old='''        // 4. 处理聚合查询
        if !parsed.aggregates.is_empty() || !parsed.group_by.is_empty() {
            core = Self::build_aggregation_node(parsed, core, &projected_vars);

            // 5. 处理 HAVING (聚合后)
            for having in &parsed.having_expressions {
                if let Some(expr) = Self::parse_filter_expr(having) {
                    core = LogicNode::Filter {
                        expression: expr,
                        child: Box::new(core),
                    };
                }
            }
        }
'''
new='''        // 4. 处理聚合 / DISTINCT 查询
        if parsed.distinct || !parsed.aggregates.is_empty() || !parsed.group_by.is_empty() {
            core = Self::build_aggregation_node(parsed, core, &projected_vars);

            // 5. 处理 HAVING (聚合后)
            for having in &parsed.having_expressions {
                if let Some(expr) = Self::parse_filter_expr(having) {
                    core = LogicNode::Filter {
                        expression: expr,
                        child: Box::new(core),
                    };
                }
            }
        }
'''
if old not in text:
    raise SystemExit('aggregation block not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('patched ir distinct into aggregation pipeline')