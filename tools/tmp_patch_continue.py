from pathlib import Path

# 1) Enable ORDER BY without LIMIT via sentinel limit node
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''        // 6. 添加 ORDER BY
        if !parsed.order_by.is_empty() {
            // TODO: 实现 ORDER BY 支持
        }

        // 7. 添加 LIMIT
        // [S4-P0-1] 同时处理 ORDER BY
        if let Some(limit) = parsed.limit {
            // 转换 order_by 到 IR 格式: Vec<(String, bool)> 表示 (变量名, 是否降序)
            let order_by: Vec<(String, bool)> = parsed.order_by.iter()
                .map(|item| {
                    let var_name = item.variable.trim_start_matches('?').to_string();
                    let is_desc = item.direction == SortDirection::Desc;
                    (var_name, is_desc)
                })
                .collect();

            core = LogicNode::Limit {
                limit,
                offset: None,
                order_by,
                child: Box::new(core),
            };
        }'''
new='''        // 6. 添加 ORDER BY / LIMIT
        let order_by: Vec<(String, bool)> = parsed.order_by.iter()
            .map(|item| {
                let var_name = item.variable.trim_start_matches('?').to_string();
                let is_desc = item.direction == SortDirection::Desc;
                (var_name, is_desc)
            })
            .collect();

        if parsed.limit.is_some() || !order_by.is_empty() {
            core = LogicNode::Limit {
                limit: parsed.limit.unwrap_or(usize::MAX),
                offset: None,
                order_by,
                child: Box::new(core),
            };
        }'''
if old not in s:
    raise SystemExit('ir order/limit block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# 2) Handle sentinel limit in SQL generator
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
old='''        // 设置 LIMIT 和 OFFSET
        self.ctx.limit = Some(limit);
        self.ctx.offset = offset;
'''
new='''        // 设置 LIMIT 和 OFFSET
        if limit == usize::MAX {
            self.ctx.limit = None;
            self.ctx.offset = None;
        } else {
            self.ctx.limit = Some(limit);
            self.ctx.offset = offset;
        }
'''
if old not in s:
    raise SystemExit('handle_limit block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# 3) Fix nested EXISTS test predicate to mapped vocab
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_exists_001.py')
s=p.read_text(encoding='utf-8')
s=s.replace('?proj <http://example.org/is_active> true .','?proj <http://example.org/project_status> "Active" .',1)
p.write_text(s,encoding='utf-8')

print('patched_order_and_nested_exists_test')
