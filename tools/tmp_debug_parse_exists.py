import os, psycopg2
q = '''SELECT ?emp ?name
WHERE {
  ?emp <http://example.org/first_name> ?name .
  FILTER EXISTS {
    ?emp <http://example.org/salary> ?salary .
    FILTER(?salary > 80000)
  }
}
ORDER BY ?emp
LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_debug_parse(%s)',(q,)); print(cur.fetchone()[0]); cur.close(); conn.close()
