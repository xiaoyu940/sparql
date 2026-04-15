import os, psycopg2
q='''PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
SELECT ?store ?dist
WHERE {
  ?store a <http://example.org/Store> .
  ?store <http://example.org/geometry> ?wkt .
  BIND(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) AS ?dist)
  FILTER(geof:distance(?wkt, "POINT(116.4074 39.9042)"^^geo:wktLiteral, uom:metre) < 10000)
}
ORDER BY ?store
LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor()
try:
    cur.execute('SELECT ontop_translate(%s)', (q,))
    print(cur.fetchone()[0])
except Exception as e:
    print('ERR',e)
cur.close(); conn.close()