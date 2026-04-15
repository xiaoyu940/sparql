import requests, time, socket
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
for i,q in enumerate([bad, ok, bad, ok, ok],1):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=6)
        print(i,'status',r.status_code,'len',len(r.text))
    except Exception as e:
        print(i,'ERR',e)
    time.sleep(0.2)
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('alive',i,True)
    except Exception as e:
        print('alive',i,False,e)