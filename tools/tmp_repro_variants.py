import requests, socket
variants=[
"PREFIX ex: < `http://example.org/>`\r\nSELECT ?name ?type\r\nWHERE {\r\n { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }\r\n UNION\r\n { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }\r\n}\r\nLIMIT 20",
"PREFIX ex: <`http://example.org/`> SELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type)} UNION { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type)} } LIMIT 20",
"PREFIX ex: < `http://example.org/>` SELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type)} UNION { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type)} } LIMIT 20",
]
for i,q in enumerate(variants,1):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=8)
        print('v',i,'status',r.status_code,'body',r.text[:120])
    except Exception as e:
        print('v',i,'err',e)
    # probe alive
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=2); s.close();
        print('alive',i,True)
    except Exception as e:
        print('alive',i,False,e)