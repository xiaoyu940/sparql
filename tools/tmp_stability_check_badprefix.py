import time, socket, psycopg2, requests
q='''PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND("Department" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND("Position" AS ?type) }
}
LIMIT 20'''

conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor(); cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
for (pid,) in cur.fetchall(): cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()
for _ in range(15):
    try: s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); break
    except: time.sleep(1)

counts={}
for i in range(120):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=5)
        k=(r.status_code, r.text[:60])
    except Exception as e:
        k=('ERR',str(type(e).__name__))
    counts[k]=counts.get(k,0)+1
    time.sleep(0.05)
print('distinct',len(counts))
for k,v in counts.items():
    print(v,k)