import os, psycopg2
q='''PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
SELECT ?store ?dist
WHERE {
  ?store a <http://example.org/Store> .
  ?store geo:hasGeometry ?geom .
  ?geom geo:asWKT ?wkt .
  BIND(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) AS ?dist)
  FILTER(?dist < 10000)
}
LIMIT 5'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_translate(%s)',(q,)); print(cur.fetchone()[0][:1000]); cur.close(); conn.close()
