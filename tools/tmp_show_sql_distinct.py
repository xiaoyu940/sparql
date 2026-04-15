import os, psycopg2
q = """PREFIX ex: <http://example.org/>
SELECT DISTINCT ?deptName
WHERE {
    ?emp ex:department_id ?dept .
    ?dept ex:department_name ?deptName .
}
ORDER BY ?deptName"""
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_translate(%s)',(q,)); print(cur.fetchone()[0]); cur.close(); conn.close()