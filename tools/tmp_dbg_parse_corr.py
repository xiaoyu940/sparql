import os, psycopg2
q='''SELECT ?emp ?name ?dept_name ?avg_dept_salary
WHERE {
  ?emp <http://example.org/first_name> ?name .
  ?emp <http://example.org/department_id> ?dept .
  ?dept <http://example.org/dept_name> ?dept_name .
  {
    SELECT (AVG(?s) AS ?avg_dept_salary)
    WHERE {
      ?e <http://example.org/salary> ?s .
      ?e <http://example.org/department_id> ?dept .
    }
  }
  FILTER(?avg_dept_salary > 60000)
}
ORDER BY ?emp
LIMIT 10'''
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor();
cur.execute('SELECT ontop_debug_parse(%s)',(q,));
print(cur.fetchone()[0])
cur.close(); conn.close()
