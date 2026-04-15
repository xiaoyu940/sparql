from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/sparql/test_basic_select.py')
text=p.read_text(encoding='utf-8')
if 'TestSelectDistinctDepartmentsViaJoin(),' not in text:
    text=text.replace('            TestSelectDistinctDepartments(),\n            TestSelectCountEmployees(),','            TestSelectDistinctDepartments(),\n            TestSelectDistinctDepartmentsViaJoin(),\n            TestSelectCountEmployees(),',1)
p.write_text(text,encoding='utf-8')
print('added new test case into suite list')