import requests
bad = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
 { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
 UNION
 { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
ok = """PREFIX ex: <http://example.org/>
SELECT ?email WHERE { ?emp ex:email ?email . } LIMIT 1"""
for i,q in enumerate([bad, ok, ok], 1):
    try:
        r = requests.post('http://127.0.0.1:5820/sparql', data=q.encode('utf-8'), timeout=8)
        print(i, r.status_code, r.text[:240])
    except Exception as e:
        print(i, 'ERR', e)