import psycopg2
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor()
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
for (pid,) in cur.fetchall():
    cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
cur.execute('SELECT ontop_start_sparql_server()')
cur.close(); conn.close()
print('restarted')