from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py')
s=p.read_text(encoding='utf-8')

old1='''            ?store a <http://example.org/Store> .
            ?store geo:hasGeometry ?geom .
            ?geom geo:asWKT ?wkt .
            BIND(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) AS ?dist)
            FILTER(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) < 10000)
          }
            LIMIT 10'''
new1='''            ?store a <http://example.org/Store> .
            ?store <http://example.org/geometry> ?wkt .
            BIND(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) AS ?dist)
            FILTER(?dist < 10000)
          }
            ORDER BY ?store
            LIMIT 10'''
if old1 not in s:
    raise SystemExit('old1 not found')
s=s.replace(old1,new1,1)

old2='''            ?store1 geo:hasGeometry ?geom1 .
            ?geom1 geo:asWKT ?wkt1 .
            ?store2 geo:hasGeometry ?geom2 .
            ?geom2 geo:asWKT ?wkt2 .
            BIND(geof:distance(?wkt1, ?wkt2, uom:metre) AS ?dist)
            FILTER(geof:distance(?wkt1, ?wkt2, uom:metre) < 5000)
          }
            LIMIT 20'''
new2='''            ?store1 a <http://example.org/Store> .
            ?store1 <http://example.org/geometry> ?wkt1 .
            ?store2 a <http://example.org/Store> .
            ?store2 <http://example.org/geometry> ?wkt2 .
            BIND(geof:distance(?wkt1, ?wkt2, uom:metre) AS ?dist)
            FILTER(?store1 != ?store2)
            FILTER(?dist < 5000)
          }
            ORDER BY ?store1 ?store2
            LIMIT 20'''
if old2 not in s:
    raise SystemExit('old2 not found')
s=s.replace(old2,new2,1)

# baseline1 keep setsrid and add order by store
s=s.replace('''            WHERE ST_Distance(ST_SetSRID(geometry, 4326), ST_GeomFromText('POINT(116.4074 39.9042)', 4326)) < 10000
            LIMIT 10''','''            WHERE ST_Distance(ST_SetSRID(geometry, 4326), ST_GeomFromText('POINT(116.4074 39.9042)', 4326)) < 10000
            ORDER BY store
            LIMIT 10''',1)
# baseline2 align filters/order
s=s.replace('''            WHERE s1.store_id < s2.store_id
              AND ST_Distance(ST_SetSRID(s1.geometry, 4326), ST_SetSRID(s2.geometry, 4326)) < 5000
            LIMIT 20''','''            WHERE s1.store_id <> s2.store_id
              AND ST_Distance(ST_SetSRID(s1.geometry, 4326), ST_SetSRID(s2.geometry, 4326)) < 5000
            ORDER BY store1, store2
            LIMIT 20''',1)

p.write_text(s,encoding='utf-8')
print('patched geof distance tests to mapped geometry predicate')
