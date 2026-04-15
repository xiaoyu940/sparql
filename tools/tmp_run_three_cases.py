import os, sys
sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')
from test_cases.test_sprint8_minus_001 import TestMinusBasic, TestMinusWithSharedVar
from test_cases.test_sprint9_p1_geosparql_metric_001 import TestGeofDistance

cfg={
 'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')
}
for cls in [TestMinusBasic, TestMinusWithSharedVar, TestGeofDistance]:
    t=cls(cfg)
    r=t.run()
    print('\n===',cls.__name__,'===')
    print('passed=',r.get('passed'))
    if not r.get('passed'):
        print('errors=',r.get('errors'))
        print('sql=',r.get('sparql_sql','')[:500])
    t.close()