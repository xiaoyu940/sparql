import os, psycopg2
qs={
'ask_join':'''ASK {
  ?emp <http://example.org/department_id> ?dept .
  ?dept <http://example.org/department_name> "Engineering" .
}''',
'construct_filter':'''CONSTRUCT { ?emp <http://example.org/hasHighSalary> ?salary . }
WHERE {
  ?emp <http://example.org/salary> ?salary .
  FILTER(?salary > 100000)
}'''
}
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor()
for k,q in qs.items():
 print('\n===',k)
 cur.execute('SELECT ontop_debug_parse(%s)',(q,));
 print(cur.fetchone()[0])
 cur.execute('SELECT ontop_translate(%s)',(q,));
 print(cur.fetchone()[0])
cur.close(); conn.close()
