import requests, socket, time
bad = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
ok = """PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1"""
for i,q in enumerate([bad,ok,bad,ok],1):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=8)
        print(i,r.status_code,r.text[:160])
    except Exception as e:
        print(i,'ERR',e)
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('alive',i,True)
    except Exception as e:
        print('alive',i,False,e)
    time.sleep(0.3)