import requests, time, socket, os, psycopg2
bad = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
 { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
 UNION
 { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
ok = """PREFIX ex: <http://example.org/>
SELECT ?email WHERE { ?emp <http://example.org/email> ?email . } LIMIT 1"""
# ensure started
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
conn.autocommit=True
cur=conn.cursor(); cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()

fail=0
for i in range(1,101):
    q = bad if i%2 else ok
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=5)
        if r.status_code>=500:
            fail += 1
    except Exception:
        fail += 1
        break

try:
    s=socket.create_connection(('127.0.0.1',5820),timeout=2); s.close(); alive=True
except Exception:
    alive=False
print('requests_done',i,'fail_count',fail,'alive',alive)