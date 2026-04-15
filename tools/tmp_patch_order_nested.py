from pathlib import Path

p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
old='''        // 6. 娣诲姞 ORDER BY
        if !parsed.order_by.is_empty() {
            // TODO: 瀹炵幇 ORDER BY 鏀寔
        }

        // 7. 娣诲姞 LIMIT
        // [S4-P0-1] 鍚屾椂澶勭悊 ORDER BY
        if let Some(limit) = parsed.limit {
            // 杞崲 order_by 鍒?IR 鏍煎紡: Vec<(String, bool)> 琛ㄧず (鍙橀噺鍚? 鏄惁闄嶅簭)
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
new='''        // 6. 娣诲姞 ORDER BY / LIMIT
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
    raise SystemExit('ir block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
old='''        // 璁剧疆 LIMIT 鍜?OFFSET
        self.ctx.limit = Some(limit);
        self.ctx.offset = offset;
'''
new='''        // 璁剧疆 LIMIT 鍜?OFFSET
        if limit == usize::MAX {
            self.ctx.limit = None;
            self.ctx.offset = None;
        } else {
            self.ctx.limit = Some(limit);
            self.ctx.offset = offset;
        }
'''
if old not in s:
    raise SystemExit('flat block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_exists_001.py')
s=p.read_text(encoding='utf-8')
s=s.replace('?proj <http://example.org/is_active> true .','?proj <http://example.org/project_status> "Active" .',1)
p.write_text(s,encoding='utf-8')

print('patched')
