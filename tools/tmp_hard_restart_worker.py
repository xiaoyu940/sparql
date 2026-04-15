import os, psycopg2
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor()
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
rows=cur.fetchall(); print('existing',rows)
for (pid,) in rows:
    cur.execute('SELECT pg_terminate_backend(%s)',(pid,)); print('term',pid,cur.fetchone()[0])
cur.execute('SELECT ontop_start_sparql_server()'); print('start',cur.fetchone()[0])
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
print('after',cur.fetchall())
cur.close(); conn.close()