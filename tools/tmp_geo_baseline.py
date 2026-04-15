import os,sys
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from test_cases.test_sprint9_p1_geosparql_metric_001 import TestGeofDistance
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')}
t=TestGeofDistance(cfg)
r=t.sql_query()
print('baseline passed', r.passed if hasattr(r,'passed') else getattr(r,'is_success',None), 'rows', r.row_count)
