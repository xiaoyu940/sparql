from pathlib import Path

p = Path('/home/yuxiaoyu/rs_ontop_core/src/sql/flat_generator.rs')
text = p.read_text(encoding='utf-8')
anchor = '                    "CONTAINS" if args_sql.len() == 2 => Ok(format!(\n                        "POSITION({} IN {}) > 0",\n                        args_sql[1], args_sql[0]\n                    )),\n'
insert = '                    "STRSTARTS" if args_sql.len() == 2 => Ok(format!("{} LIKE ({} || \'%\')", args_sql[0], args_sql[1])),\n                    "STRENDS" if args_sql.len() == 2 => Ok(format!("{} LIKE (\'%\' || {})", args_sql[0], args_sql[1])),\n                    "STRBEFORE" if args_sql.len() == 2 => Ok(format!("SPLIT_PART({}, {}, 1)", args_sql[0], args_sql[1])),\n'
if anchor not in text:
    raise SystemExit('anchor not found for string funcs')
text = text.replace(anchor, anchor + insert, 1)
p.write_text(text, encoding='utf-8')
print('patched STRSTARTS/STRENDS/STRBEFORE')