from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
old1='''        unmatched = []
        for sparql_col in sparql_cols:
            # 尝试找到匹配的 SQL 列
            found = any(
                sparql_col.lower() in sql_col.lower() or
                sql_col.lower() in sparql_col.lower()
                for sql_col in sql_cols
            )
            if not found:
                unmatched.append(sparql_col)

        if unmatched:
            errors.append(f"未匹配的列: {unmatched}, SQL列: {sql_cols}")'''
new1='''        unmatched = []
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
if old1 not in s:
    raise SystemExit('compare column match block not found')
s=s.replace(old1,new1,1)

old2='''              common_checks = 0
              for sparql_col, sparql_val in sparql_first.items():
                  for sql_col, sql_val in sql_first.items():
                      if sparql_col.lower() in sql_col.lower() or sql_col.lower() in sparql_col.lower():
                          common_checks += 1
                          # 尝试数值比对（处理 80000.0 vs 80000）
                          s_val = str(sparql_val)
                          sq_val = str(sql_val)

                          if s_val != sq_val:
                              try:
                                  if float(s_val) == float(sq_val):
                                      continue # 数值相等
                              except (ValueError, TypeError):
                                  pass

                              errors.append(f"数据不匹配[{sparql_col}]: SPARQL='{sparql_val}', SQL='{sql_val}'")
                              break'''
new2='''              common_checks = 0
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

                      errors.append(f"数据不匹配[{sparql_col}]: SPARQL='{sparql_val}', SQL='{sql_val}'")'''
if old2 not in s:
    raise SystemExit('compare data block not found')
s=s.replace(old2,new2,1)

p.write_text(s,encoding='utf-8')
print('patched compare_results to prioritize exact column-name matching before fuzzy matching')
