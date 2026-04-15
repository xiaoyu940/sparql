import requests
cases=[
('simple_no_prefix','SELECT ?email WHERE { ?emp <http://example.org/email> ?email . } LIMIT 1'),
('simple_prefix','PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?emp ex:email ?email . } LIMIT 1'),
('simple_prefix_dept','PREFIX ex: <http://example.org/> SELECT ?name WHERE { ?d ex:department_name ?name . } LIMIT 1'),
('simple_prefix_bind_only','PREFIX ex: <http://example.org/> SELECT ?x WHERE { BIND("a" AS ?x) } LIMIT 1'),
]
for n,q in cases:
  try:
    r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=6)
    print(n,r.status_code,r.text[:120])
  except Exception as e:
    print(n,'ERR',e)