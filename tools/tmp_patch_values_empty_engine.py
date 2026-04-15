from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
s=p.read_text(encoding='utf-8')

# handle_values: if rows empty, add empty guard and still add from table with LIMIT 0
marker='fn handle_values'
if marker not in s:
    raise SystemExit('handle_values not found')

# Insert guard after row_sqls built, before building sql string
insert_point='let sql = format!("(VALUES {})",'
idx=s.find(insert_point)
if idx==-1:
    raise SystemExit('values sql build not found')

# ensure we only insert once
if 'if row_sqls.is_empty()' not in s[s.find('fn handle_values'):s.find('fn handle_union')]:
    s=s.replace(insert_point, 'if row_sqls.is_empty() {\n            self.ctx.from_tables.push(FromTable {\n                table_name: "(SELECT 1)".to_string(),\n                alias: self.alias_manager.allocate_table_alias("vals_empty"),\n                join_type: None,\n                join_condition: Some("FALSE".to_string()),\n                is_subquery: true,\n                subquery_sql: None,\n            });\n            return Ok(());\n        }\n\n        '+insert_point, 1)

p.write_text(s,encoding='utf-8')
print('patched handle_values for empty rows')
