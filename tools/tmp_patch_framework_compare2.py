from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')

start=s.find('unmatched = []')
end=s.find('if unmatched:', start)
if start==-1 or end==-1:
    raise SystemExit('unmatched block bounds not found')
# include the if unmatched block lines
end2=s.find('\n\n', end)
if end2==-1:
    raise SystemExit('unmatched block end not found')
new1='''unmatched = []
        col_matches = {}
        sql_col_by_lower = {c.lower(): c for c in sql_cols}
        for sparql_col in sparql_cols:
            s_lower = sparql_col.lower()
            if s_lower in sql_col_by_lower:
                col_matches[sparql_col] = sql_col_by_lower[s_lower]
                continue

            fallback = next(
                (sql_col for sql_col in sql_cols
                 if s_lower in sql_col.lower() or sql_col.lower() in s_lower),
                None
            )
            if fallback is not None:
                col_matches[sparql_col] = fallback
            else:
                unmatched.append(sparql_col)

        if unmatched:
            errors.append(f"未匹配的列: {unmatched}, SQL列: {sql_cols}")'''
s=s[:start]+new1+s[end2:]

start=s.find('common_checks = 0')
end=s.find('if common_checks == 0:', start)
if start==-1 or end==-1:
    raise SystemExit('common_checks block bounds not found')
new2='''common_checks = 0
            for sparql_col, sparql_val in sparql_first.items():
                sql_col = col_matches.get(sparql_col)
                if sql_col is None:
                    s_lower = sparql_col.lower()
                    sql_col = next(
                        (c for c in sql_first.keys() if c.lower() == s_lower),
                        next((c for c in sql_first.keys() if s_lower in c.lower() or c.lower() in s_lower), None)
                    )
                if sql_col is None or sql_col not in sql_first:
                    continue

                common_checks += 1
                sql_val = sql_first[sql_col]
                s_val = str(sparql_val)
                sq_val = str(sql_val)

                if s_val != sq_val:
                    try:
                        if float(s_val) == float(sq_val):
                            continue
                    except (ValueError, TypeError):
                        pass

                    errors.append(f"数据不匹配[{sparql_col}]: SPARQL='{sparql_val}', SQL='{sql_val}'")
'''
s=s[:start]+new2+s[end:]

p.write_text(s,encoding='utf-8')
print('patched framework compare blocks by bounds replacement')
