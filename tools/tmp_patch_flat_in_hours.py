from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')

old_not = '                    "NOT" if args_sql.len() == 1 => Ok(format!("NOT ({})", args_sql[0])),\n'
new_not = old_not + '                    "IN" if args_sql.len() >= 2 => Ok(format!("{} IN ({})", args_sql[0], args_sql[1..].join(", "))),\n'
if old_not not in text:
    raise SystemExit('NOT branch anchor not found')
text = text.replace(old_not, new_not, 1)

old_hours = '                    "HOURS" if args_sql.len() == 1 => Ok(format!("EXTRACT(HOUR FROM ({}::timestamp))", args_sql[0])),\n'
new_hours = '                    "HOURS" if args_sql.len() == 1 => Ok(format!("EXTRACT(HOUR FROM {})", args_sql[0])),\n'
if old_hours not in text:
    raise SystemExit('HOURS line not found')
text = text.replace(old_hours, new_hours, 1)

p.write_text(text, encoding='utf-8')
print('patched flat_generator IN + HOURS')