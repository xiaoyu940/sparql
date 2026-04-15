import os, time, socket, psycopg2, requests

BAD = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
OK = """PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1"""

conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor()
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
old=cur.fetchall()
for (pid,) in old:
    cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
cur.execute('SELECT ontop_start_sparql_server()')
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
new=cur.fetchall()
cur.close(); conn.close()
print('old_pids',old,'new_pids',new)

for i in range(15):
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close();
        print('port_ready_at',i,'sec')
        break
    except Exception:
        time.sleep(1)

r1=requests.post('http://127.0.0.1:5820/sparql',data=BAD.encode('utf-8'),timeout=10)
print('bad_status',r1.status_code)
print('bad_body',r1.text[:200])
r2=requests.post('http://127.0.0.1:5820/sparql',data=OK.encode('utf-8'),timeout=10)
print('ok_status',r2.status_code)
print('ok_body',r2.text[:200])