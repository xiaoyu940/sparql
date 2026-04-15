import requests, urllib.parse, time, socket, os, psycopg2

q1 = """PREFIX ex: < `http://example.org/>`\r\nSELECT ?firstName ?lastName ?deptName\r\nWHERE {\r\n    ?emp ex:first_name ?firstName ;\r\n         ex:last_name ?lastName ;\r\n         ex:department_id ?dept .\r\n    ?dept ex:department_name ?deptName .\r\n    VALUES ?deptName { \"Engineering\" \"Sales\" }\r\n}\r\nLIMIT 10"""
q2 = """PREFIX ex: < `http://example.org/>`\r\nSELECT ?firstName ?lastName\r\nWHERE {\r\n    ?emp ex:first_name ?firstName ;\r\n         ex:last_name ?lastName ;\r\n         ex:department_name ?deptName .\r\n    FILTER(CONTAINS(LCASE(?deptName), \"engineering\"))\r\n}\r\nLIMIT 10"""
q3 = q2

conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
conn.autocommit=True
cur=conn.cursor()
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
for (pid,) in cur.fetchall():
    cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
cur.execute('SELECT ontop_start_sparql_server()')
cur.close(); conn.close()
for _ in range(10):
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); break
    except Exception:
        time.sleep(1)

for i,q in enumerate([q1,q2,q3],1):
    r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=10)
    print('raw',i,r.status_code,r.text[:160])

headers={'Content-Type':'application/x-www-form-urlencoded'}
for i,q in enumerate([q1,q2,q3],1):
    payload='query='+urllib.parse.quote(q,safe='')
    r=requests.post('http://127.0.0.1:5820/sparql',data=payload,headers=headers,timeout=10)
    print('form',i,r.status_code,r.text[:160])