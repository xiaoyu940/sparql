import time, socket, os, psycopg2, requests, urllib.parse
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor(); cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()
for i in range(10):
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close();
        print('up at',i); break
    except Exception:
        time.sleep(1)

bad_raw = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
bad_form = 'query=' + urllib.parse.quote(bad_raw, safe='')
headers={'Content-Type':'application/x-www-form-urlencoded'}
for tag,data,h in [('raw',bad_raw.encode('utf-8'),None),('form',bad_form,headers),('ok',"PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1".encode('utf-8'),None)]:
    r=requests.post('http://127.0.0.1:5820/sparql',data=data,headers=h,timeout=8)
    print(tag,r.status_code,r.text[:120])