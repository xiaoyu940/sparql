import requests, time, socket
q='''PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND("Department" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND("Position" AS ?type) }
}
LIMIT 20'''
for i in range(30):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=5)
        print(i,r.status_code,r.text[:80])
    except Exception as e:
        print(i,'ERR',e)
    time.sleep(0.1)