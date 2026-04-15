import os, sys
sys.path.insert(0,'/home/yuxiaoyu/rs_ontop_core/tests/python')
from framework import run_test_case
from test_cases.test_sprint8_geosparql_001 import TestGeoSparqlBuffer, TestGeoSparqlContains, TestGeoSparqlDistance, TestGeoSparqlIntersects, TestGeoSparqlOverlaps, TestGeoSparqlWithin
cfg={'host':'localhost','port':5432,'database':'rs_ontop_core','user':'yuxiaoyu','password':os.environ.get('PGPASSWORD','123456')}
for cls in [TestGeoSparqlWithin, TestGeoSparqlContains, TestGeoSparqlIntersects, TestGeoSparqlOverlaps, TestGeoSparqlBuffer, TestGeoSparqlDistance]:
    r=run_test_case(cls,cfg)
    print(cls.__name__, 'PASS' if r.get('passed') else 'FAIL')
    if not r.get('passed'):
        print(r.get('errors'))
