import requests, os, psycopg2, time
bad = """PREFIX ex: < `http://example.org/>`
SELECT ?name ?type
WHERE {
 { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) }
 UNION
 { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) }
}
LIMIT 20"""
try:
    r=requests.post('http://127.0.0.1:5820/sparql',data=bad.encode(),timeout=8)
    print('first',r.status_code,r.text[:120])
except Exception as e:
    print('first err',e)
time.sleep(0.5)
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute("SELECT count(*) FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
print('bgworker_count',cur.fetchone()[0])
cur.close(); conn.close()