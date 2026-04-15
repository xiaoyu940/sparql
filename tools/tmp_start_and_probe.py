import os, psycopg2, requests, time, socket
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor(); cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()
for i in range(10):
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('up',i); break
    except Exception:
        time.sleep(1)
q='PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1'
try:
    r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=8)
    print(r.status_code,r.text[:120])
except Exception as e:
    print('err',e)