import requests, socket
cases=[
('single_bind','''PREFIX ex: <http://example.org/>\nSELECT ?name ?type WHERE { ?dept ex:department_name ?name . BIND("Department" AS ?type) } LIMIT 5'''),
('union_no_bind','''PREFIX ex: <http://example.org/>\nSELECT ?name WHERE { { ?dept ex:department_name ?name . } UNION { ?pos ex:position_title ?name . } } LIMIT 5'''),
('union_bind_left_only','''PREFIX ex: <http://example.org/>\nSELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND("Department" AS ?type) } UNION { ?pos ex:position_title ?name . } } LIMIT 5'''),
('union_bind_right_only','''PREFIX ex: <http://example.org/>\nSELECT ?name ?type WHERE { { ?dept ex:department_name ?name . } UNION { ?pos ex:position_title ?name . BIND("Position" AS ?type) } } LIMIT 5'''),
('union_bind_both','''PREFIX ex: <http://example.org/>\nSELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND("Department" AS ?type) } UNION { ?pos ex:position_title ?name . BIND("Position" AS ?type) } } LIMIT 5'''),
]
for n,q in cases:
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=6)
        print(n,r.status_code,r.text[:120])
    except Exception as e:
        print(n,'ERR',e)