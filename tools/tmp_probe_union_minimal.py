import requests
cases=[
('union_same_pred','PREFIX ex: <http://example.org/> SELECT ?name WHERE { { ?a ex:department_name ?name . } UNION { ?b ex:department_name ?name . } } LIMIT 3'),
('union_dept_pos','PREFIX ex: <http://example.org/> SELECT ?name WHERE { { ?a ex:department_name ?name . } UNION { ?b ex:position_title ?name . } } LIMIT 3'),
('union_dept_pos_with_type_const','PREFIX ex: <http://example.org/> SELECT ?name ?type WHERE { { ?a ex:department_name ?name . BIND("D" AS ?type) } UNION { ?b ex:position_title ?name . BIND("P" AS ?type) } } LIMIT 3'),
]
for n,q in cases:
  try:
    r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=6)
    print(n,r.status_code,r.text[:150])
  except Exception as e:
    print(n,'ERR',e)