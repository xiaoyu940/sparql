import os,sys
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from test_cases.test_sprint7_construct import TestConstructWithFilter
from test_cases.test_sprint7_describe import TestDescribeWithLimit
from test_cases.test_sprint8_bind_numeric import TestBindArithmetic
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')}
for cls in [TestConstructWithFilter,TestDescribeWithLimit,TestBindArithmetic]:
    t=cls(cfg); r=t.run();
    print('\n===',cls.__name__,'===')
    print('passed',r.get('passed'))
    print('errors',r.get('errors'))
    print('sparql_sql',r.get('sparql_sql','')[:700])
    t.close()