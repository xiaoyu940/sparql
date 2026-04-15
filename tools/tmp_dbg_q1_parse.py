import os, psycopg2
q='''PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
SELECT ?poi ?name
WHERE {
  ?poi a <http://example.org/POI> .
  ?poi <http://example.org/poi_name> ?name .
  ?poi geo:hasGeometry ?geom .
  ?geom geo:asWKT ?wkt .
  FILTER(geof:sfWithin(?wkt, geof:buffer("POINT(116.4 39.9)"^^geo:wktLiteral, 5000, <http://www.opengis.net/def/uom/OGC/1.0/metre>)))
}
ORDER BY ?poi
LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_debug_parse(%s)',(q,)); print(cur.fetchone()[0]); cur.close(); conn.close()
