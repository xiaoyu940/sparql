import time, socket, psycopg2, requests
bad_prefix='''PREFIX ex: < `http://example.org/>`\nSELECT ?x WHERE { BIND("a" AS ?x) } LIMIT 1'''
bad_format='''PREFIX ex: <http://example.org/>\nSELECT ?x WHERE { ?s ex:first_name ?x . '''
ok='''PREFIX ex: <http://example.org/>\nSELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor(); cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
for (pid,) in cur.fetchall(): cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()
for _ in range(12):
    try: s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); break
    except Exception: time.sleep(1)
for name,q in [('bad_prefix',bad_prefix),('bad_format',bad_format),('ok',ok),('bad_format_again',bad_format),('ok_again',ok)]:
    try:
      r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=8)
      print(name,r.status_code,r.text[:140])
    except Exception as e:
      print(name,'ERR',e)