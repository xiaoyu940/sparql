import requests, json, os, psycopg2
q = """PREFIX ex: <http://example.org/>
SELECT DISTINCT ?deptName
WHERE {
    ?emp ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
}
ORDER BY ?deptName"""
r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'))
print('http',r.status_code)
obj=r.json()
vals=[b.get('deptName',{}).get('value') for b in obj.get('results',{}).get('bindings',[])]
print('rows',len(vals),'unique',len(set(vals)))
print('first',vals[:10])
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor();
cur.execute('SELECT COUNT(DISTINCT department_name), COUNT(*) FROM departments')
print('sql departments distinct,total=',cur.fetchone())
cur.close(); conn.close()