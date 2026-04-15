from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/parser/ir_converter.rs')
text=p.read_text(encoding='utf-8')
text=text.replace('if !parsed.aggregates.is_empty() || !parsed.group_by.is_empty() {','if parsed.distinct || !parsed.aggregates.is_empty() || !parsed.group_by.is_empty() {',1)
text=text.replace('// 4. 处理聚合查询','// 4. 处理聚合 / DISTINCT 查询',1)
p.write_text(text,encoding='utf-8')
print('patched distinct aggregation condition')