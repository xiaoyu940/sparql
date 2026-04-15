import os,sys
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from framework import run_test_case
from test_cases.test_sprint8_subquery_002 import TestCorrelatedSubQueryLateral
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')}
r=run_test_case(TestCorrelatedSubQueryLateral,cfg)
print('TestCorrelatedSubQueryLateral', 'PASS' if r.get('passed') else 'FAIL', r.get('errors'))
