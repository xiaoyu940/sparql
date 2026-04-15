import requests, socket
q = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
r = requests.post('http://127.0.0.1:5820/sparql', data=q.encode('utf-8'), timeout=8)
print('bad', r.status_code, r.text[:220])
q2 = """PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1"""
r2 = requests.post('http://127.0.0.1:5820/sparql', data=q2.encode('utf-8'), timeout=8)
print('good', r2.status_code, r2.text[:120])
try:
    s=socket.create_connection(('127.0.0.1',5820),timeout=2); s.close(); print('alive',True)
except Exception as e:
    print('alive',False,e)