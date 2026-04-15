import requests, time, socket
q="""PREFIX ex: < `http://example.org/>`
SELECT ?firstName ?lastName ?deptName
WHERE {
  ?emp ex:first_name ?firstName ; ex:last_name ?lastName ; ex:department_id ?dept .
  ?dept ex:department_name ?deptName .
  VALUES ?deptName { "Engineering" "Sales" }
}
LIMIT 10"""
for i in range(1,4):
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode(),timeout=8)
        print(i,r.status_code,r.text[:100])
    except Exception as e:
        print(i,'ERR',e)
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=2); s.close(); print('alive',i,True)
    except Exception as e:
        print('alive',i,False,e)
    time.sleep(2)