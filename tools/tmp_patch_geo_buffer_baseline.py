from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_geosparql_001.py')
s=p.read_text(encoding='utf-8')
old='''          SELECT poi_id AS "poi", poi_name AS "name"
          FROM pois
          WHERE ST_Within(
              ST_SetSRID(geometry, 4326),
              ST_Buffer(
                  ST_GeomFromText('POINT(116.4 39.9)', 4326),
                  5000
              )
          )
          ORDER BY poi_id
          LIMIT 10'''
new='''          SELECT poi_id AS "poi", poi_name AS "name"
          FROM pois
          WHERE ST_Within(
              ST_SetSRID(geometry, 4326),
              ST_Buffer(
                  ST_GeogFromText('POINT(116.4 39.9)'),
                  5000
              )::geometry
          )
          ORDER BY poi_id
          LIMIT 10'''
if old not in s:
    raise SystemExit('GeoSparqlBuffer baseline block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched GeoSparqlBuffer baseline to metre-aware geography buffer semantics')
