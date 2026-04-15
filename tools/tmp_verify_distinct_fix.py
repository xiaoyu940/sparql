import requests
q = """PREFIX ex: <http://example.org/>
SELECT DISTINCT ?deptName
WHERE {
    ?emp ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
}
ORDER BY ?deptName"""
r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'))
obj=r.json()
vals=[b.get('deptName',{}).get('value') for b in obj.get('results',{}).get('bindings',[])]
print('status',r.status_code,'rows',len(vals),'unique',len(set(vals)))
print(vals[:20])