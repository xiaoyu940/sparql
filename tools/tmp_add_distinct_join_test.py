from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/sparql/test_basic_select.py')
text=p.read_text(encoding='utf-8')
insert='''

class TestSelectDistinctDepartmentsViaJoin(TestCaseBase):
    """去重查询：通过员工-部门连接后仍应保持部门名唯一"""

    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT DISTINCT ?deptName
        WHERE {
            ?emp ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
        }
        ORDER BY ?deptName
        """

    def baseline_sql(self) -> str:
        return """
        SELECT DISTINCT d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        ORDER BY d.department_name
        """
'''
if 'class TestSelectDistinctDepartmentsViaJoin' not in text:
    text=text.replace('\n\nclass TestSelectCountEmployees(TestCaseBase):', insert+'\n\nclass TestSelectCountEmployees(TestCaseBase):',1)
    text=text.replace('            TestSelectDistinctDepartments(),\n            TestSelectCountEmployees(),','            TestSelectDistinctDepartments(),\n            TestSelectDistinctDepartmentsViaJoin(),\n            TestSelectCountEmployees(),',1)
p.write_text(text,encoding='utf-8')
print('added DISTINCT-via-join regression test')