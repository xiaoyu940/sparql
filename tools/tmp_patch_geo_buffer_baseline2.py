from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_geosparql_001.py')
s=p.read_text(encoding='utf-8')
s=s.replace("ST_Buffer(ST_GeomFromText('POINT(116.4 39.9)', 4326), 5000)","ST_Buffer(ST_GeogFromText('POINT(116.4 39.9)'), 5000)::geometry",1)
p.write_text(s,encoding='utf-8')
print('patched GeoSparqlBuffer baseline buffer expression')
