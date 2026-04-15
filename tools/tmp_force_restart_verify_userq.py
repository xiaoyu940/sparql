import time, socket, psycopg2, requests
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
print('old',old,'new',new)
for i in range(10):
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('ready',i); break
    except Exception:
        time.sleep(1)
q='''PREFIX ex: < `http://example.org/>`
SELECT ?firstName ?lastName ?deptName
WHERE {
    ?emp ex:first_name ?firstName ; ex:last_name ?lastName ; ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
    VALUES ?deptName { "Engineering" "Sales" }
}
LIMIT 10'''
r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=8)
print('status',r.status_code)
print('body',r.text[:200])