import requests, socket, time, random
variants = [
"PREFIX ex: < `http://example.org/>` SELECT ?x WHERE { ?s ex:first_name ?x . } LIMIT 1",
"PREFIX ex: <http://example.org/> SELECT ?x WHERE { ?s ex:first_name ?x .",
"PREFIX ex: <http://example.org/> SELECT ?x WHERE { FILTER(CONTAINS(LCASE(?x), \"a\")) }",
"PREFIX ex: < `http://example.org/>` SELECT ?name ?type WHERE { { ?d ex:department_name ?name . BIND(\"D\" AS ?type)} UNION { ?p ex:position_title ?name . BIND(\"P\" AS ?type)} } LIMIT 10",
"PREFIX ex: <http://example.org/> SELECT ?x WHERE { VALUES ?x { \"a\" \"b\" }",
]
for i,q in enumerate(variants,1):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=8)
        print(i,r.status_code,r.text[:120])
    except Exception as e:
        print(i,'ERR',e)
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('alive',True)
    except Exception as e:
        print('alive',False,e)