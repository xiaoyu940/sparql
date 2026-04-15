from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
s=p.read_text(encoding='utf-8')
pat=re.compile(r'\n\s*if !parsed\.order_by\.is_empty\(\) \{[\s\S]*?\n\s*\}\n\n\s*// 8\.', re.M)
m=pat.search(s)
if not m:
    raise SystemExit('order/limit region not found')
replacement='''
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
        }

        // 8.'''
s=s[:m.start()]+replacement+s[m.end():]
p.write_text(s,encoding='utf-8')

p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')
s=s.replace('self.ctx.limit = Some(limit);\n        self.ctx.offset = offset;','if limit == usize::MAX {\n            self.ctx.limit = None;\n            self.ctx.offset = None;\n        } else {\n            self.ctx.limit = Some(limit);\n            self.ctx.offset = offset;\n        }',1)
p.write_text(s,encoding='utf-8')

p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_exists_001.py')
s=p.read_text(encoding='utf-8')
s=s.replace('?proj <http://example.org/is_active> true .','?proj <http://example.org/project_status> "Active" .',1)
p.write_text(s,encoding='utf-8')
print('patched')
