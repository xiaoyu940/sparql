import requests, urllib.parse, socket
bad_raw = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
    { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
    UNION
    { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
bad_form = 'query=' + urllib.parse.quote(bad_raw, safe='')
headers={'Content-Type':'application/x-www-form-urlencoded'}
r1=requests.post('http://127.0.0.1:5820/sparql',data=bad_raw.encode('utf-8'),timeout=8)
print('raw',r1.status_code,r1.text[:180])
r2=requests.post('http://127.0.0.1:5820/sparql',data=bad_form,headers=headers,timeout=8)
print('form',r2.status_code,r2.text[:180])
ok='PREFIX ex: <http://example.org/> SELECT ?email WHERE { ?e ex:email ?email . } LIMIT 1'
r3=requests.post('http://127.0.0.1:5820/sparql',data=ok.encode('utf-8'),timeout=8)
print('ok',r3.status_code,r3.text[:120])
try:
 s=socket.create_connection(('127.0.0.1',5820),timeout=2); s.close(); print('alive',True)
except Exception as e:
 print('alive',False,e)