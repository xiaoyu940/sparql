import requests
q = """PREFIX ex: <http://example.org/>
SELECT ?deptName
WHERE {
    ?emp ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
}
GROUP BY ?deptName
ORDER BY ?deptName"""
r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode())
print(r.status_code)
print(r.text[:800])