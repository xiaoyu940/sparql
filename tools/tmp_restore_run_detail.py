from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
start=s.find('    def run(self) -> Dict:')
end=s.find('\n\n    def close(self):', start)
if start==-1 or end==-1:
    raise SystemExit('run method bounds not found')
new='''    def run(self) -> Dict:
        """执行单个测试用例并打印详细过程"""
        try:
            print("  执行 SPARQL 查询...")
            sparql_result = self.sparql_query()
            print(f"  ✓ SPARQL 返回 {sparql_result.row_count} 行")

            print("  执行 SQL 查询...")
            sql_result = self.sql_query()
            print(f"  ✓ SQL 返回 {sql_result.row_count} 行")

            print("  比对结果...")
            passed, errors = self.compare_results(sparql_result, sql_result)
            if passed:
                print("  ✓ 测试通过")
            else:
                print("  ✗ 测试失败:")
                for err in errors:
                    print(f"    - {err}")

            return {
                'test_name': self.__class__.__name__,
                'passed': passed,
                'errors': errors,
                'sparql_sql': getattr(sparql_result, 'sql', None),
                'sparql_result': sparql_result.to_dict() if hasattr(sparql_result, 'to_dict') else None,
                'sql_result': sql_result.to_dict() if hasattr(sql_result, 'to_dict') else None,
            }
        except Exception as e:
            msg = f'测试执行异常: {str(e)}'
            print(f"  ✗ {msg}")
            return {
                'test_name': self.__class__.__name__,
                'passed': False,
                'errors': [msg],
            }
'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('restored detailed per-case SPARQL/SQL/compare logging in TestCaseBase.run')
