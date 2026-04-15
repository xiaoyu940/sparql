import requests, socket, time
q='''PREFIX ex: < `http://example.org/>`
SELECT ?firstName ?lastName ?deptName
WHERE {
  ?emp ex:first_name ?firstName ; ex:last_name ?lastName ; ex:department_id ?dept .
  ?dept ex:department_name ?deptName .
  VALUES ?deptName { "Engineering" "Sales" }
}
LIMIT 10'''
for i in range(1,4):
    r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=8)
    print(i,r.status_code,r.text[:120])
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1); s.close(); print('alive',True)
    except Exception as e:
        print('alive',False,e)
    time.sleep(0.3)