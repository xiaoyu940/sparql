import os, psycopg2
q='''SELECT ?emp ?name ?target_dept ?target_salary WHERE { ?emp <http://example.org/first_name> ?name . ?emp <http://example.org/department_id> ?dept . ?emp <http://example.org/salary> ?salary . VALUES (?target_dept ?target_salary) { (1 50000) (2 60000) (3 55000) } FILTER(?dept = ?target_dept && ?salary >= ?target_salary) } ORDER BY ?emp LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute('SELECT ontop_debug_parse(%s)',(q,)); print(cur.fetchone()[0]); cur.close(); conn.close()
