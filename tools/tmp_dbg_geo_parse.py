import os, psycopg2
q='''PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
SELECT ?region ?name
WHERE {
  ?region a <http://example.org/Region> .
  ?region <http://example.org/region_name> ?name .
  ?region geo:hasGeometry ?geom .
  ?geom geo:asWKT ?wkt .
  FILTER(geof:sfContains(?wkt, "POINT(116.4 39.9)"^^geo:wktLiteral))
}
ORDER BY ?region
LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor();cur.execute('SELECT ontop_debug_parse(%s)',(q,));print(cur.fetchone()[0]);cur.close();conn.close()
