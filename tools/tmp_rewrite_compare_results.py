from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
start=s.find('def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult) -> Tuple[bool, List[str]]:')
end=s.find('\n    def run_test_case(', start)
if start==-1 or end==-1:
    raise SystemExit('compare_results function bounds not found')
new_fn='''def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult) -> Tuple[bool, List[str]]:
        """比对 SPARQL 和 SQL 查询结果"""
        errors = []

        if sparql_result.row_count != sql_result.row_count:
            errors.append(f"行数不匹配: SPARQL={sparql_result.row_count}, SQL={sql_result.row_count}")

        sparql_cols = set(sparql_result.columns)
        sql_cols = set(sql_result.columns)

        unmatched = []
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
                None,
            )
            if fallback is not None:
                col_matches[sparql_col] = fallback
            else:
                unmatched.append(sparql_col)

        if unmatched:
            errors.append(f"未匹配的列: {unmatched}, SQL列: {sql_cols}")

        if sparql_result.rows and sql_result.rows:
            sparql_first = sparql_result.rows[0]
            sql_first = sql_result.rows[0]

            common_checks = 0
            for sparql_col, sparql_val in sparql_first.items():
                sql_col = col_matches.get(sparql_col)
                if sql_col is None:
                    s_lower = sparql_col.lower()
                    if s_lower in sql_first:
                        sql_col = s_lower
                    else:
                        sql_col = next(
                            (c for c in sql_first.keys() if s_lower in c.lower() or c.lower() in s_lower),
                            None,
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

            if common_checks == 0:
                errors.append(f"没有可比对的共同列: SPARQL列={list(sparql_first.keys())}, SQL列={list(sql_first.keys())}")

        return len(errors) == 0, errors

'''
s=s[:start]+new_fn+s[end:]
p.write_text(s,encoding='utf-8')
print('rewrote compare_results function')
