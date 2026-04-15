import os, psycopg2
q = '''SELECT ?dept ?name
WHERE {
  ?dept <http://example.org/dept_name> ?name .
  FILTER EXISTS {
    ?emp <http://example.org/department_id> ?dept .
    ?emp <http://example.org/project_id> ?proj .
    FILTER EXISTS {
      ?proj <http://example.org/project_status> "Active" .
    }
  }
}
ORDER BY ?dept'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_debug_parse(%s)',(q,)); print(cur.fetchone()[0]); cur.close(); conn.close()
