from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/framework.py')
s=p.read_text(encoding='utf-8')
if 'def run(self) -> Dict:' in s:
    print('run method already exists')
else:
    insert='''
    def run(self) -> Dict:
        """执行单个测试用例并返回标准化结果"""
        try:
            sparql_result = self.sparql_query()
            sql_result = self.sql_query()
            passed, errors = self.compare_results(sparql_result, sql_result)
            return {
                'test_name': self.__class__.__name__,
                'passed': passed,
                'errors': errors,
                'sparql_sql': getattr(sparql_result, 'sql', None),
                'sparql_result': sparql_result.to_dict() if hasattr(sparql_result, 'to_dict') else None,
                'sql_result': sql_result.to_dict() if hasattr(sql_result, 'to_dict') else None,
            }
        except Exception as e:
            return {
                'test_name': self.__class__.__name__,
                'passed': False,
                'errors': [f'测试执行异常: {str(e)}'],
            }

'''
    marker='\n    def close(self):'
    pos=s.find(marker)
    if pos==-1:
        raise SystemExit('close method marker not found')
    s=s[:pos]+"\n"+insert+s[pos:]
    p.write_text(s,encoding='utf-8')
    print('added TestCaseBase.run method')
