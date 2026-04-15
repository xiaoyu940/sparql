import requests
q = """PREFIX ex: <http://example.org/>
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
r = requests.post('http://127.0.0.1:5820/sparql', data=q.encode('utf-8'))
print(r.status_code)
print(r.text[:500])