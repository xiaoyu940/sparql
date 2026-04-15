import psycopg2, os
q="""PREFIX ex: <http://example.org/>
SELECT ?name WHERE {
 { ?a ex:department_name ?name . }
 UNION
 { ?b ex:department_name ?name . }
}
LIMIT 3"""
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
cur=conn.cursor()
try:
    cur.execute('SELECT ontop_translate(%s)',(q,))
    print('OK',cur.fetchone()[0][:200])
except Exception as e:
    print('ERR',type(e),e)
cur.close(); conn.close()