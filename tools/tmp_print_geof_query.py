import sys
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from test_cases.test_sprint9_p1_geosparql_metric_001 import TestGeofDistance
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':'123456'}
t=TestGeofDistance(cfg)
q=t.sparql_query()
print(q)
print('---repr---')
print(repr(q))