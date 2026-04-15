import os,sys,inspect,re
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from test_cases.test_sprint8_subquery_002 import TestCorrelatedSubQueryLateral, TestNestedSubQuery
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')}
for cls in [TestCorrelatedSubQueryLateral, TestNestedSubQuery]:
 t=cls(cfg)
 q=re.search(r'sparql\s*=\s*"""([\s\S]*?)"""',inspect.getsource(cls.sparql_query)).group(1)
 print('\n===',cls.__name__)
 print(t.translate_sparql(q))
