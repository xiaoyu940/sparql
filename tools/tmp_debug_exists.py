import os, psycopg2, json
q1 = '''SELECT ?dept ?name
WHERE {
  ?dept <http://example.org/dept_name> ?name .
  FILTER EXISTS {
    ?emp <http://example.org/department_id> ?dept .
    ?emp <http://example.org/project_id> ?proj .
    FILTER EXISTS {
      ?proj <http://example.org/is_active> true .
    }
  }
}
ORDER BY ?dept'''
q2 = '''SELECT ?dept ?name
WHERE {
  ?dept <http://example.org/dept_name> ?name .
  VALUES ?dept { 1 2 3 }
  FILTER EXISTS {
    ?emp <http://example.org/department_id> ?dept .
    ?emp <http://example.org/salary> ?salary .
    FILTER(?salary > 70000)
  }
}
ORDER BY ?dept'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor()
for i,q in enumerate([q1,q2],1):
    cur.execute('SELECT ontop_debug_parse(%s)', (q,))
    res=cur.fetchone()[0]
    print('----',i)
    print(res)
    cur.execute('SELECT ontop_translate(%s)', (q,))
    print(cur.fetchone()[0][:1200])
cur.close(); conn.close()
