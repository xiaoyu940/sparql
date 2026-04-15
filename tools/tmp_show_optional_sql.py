import os, sys, psycopg2
sys.path.append('/home/yuxiaoyu/rs_ontop_core/tests/sparql')
from test_join_optional import TestOptionalEmployeeSalary, TestOptionalEmployeeProject, TestNestedOptional

conn = psycopg2.connect(host='localhost', port=5432, dbname='rs_ontop_core', user='yuxiaoyu', password=os.environ.get('PGPASSWORD','123456'))
cur = conn.cursor()
for cls in (TestOptionalEmployeeSalary, TestOptionalEmployeeProject, TestNestedOptional):
    q = cls().sparql_query()
    cur.execute('SELECT ontop_translate(%s)', (q,))
    print('\n===', cls.__name__, '===')
    print(cur.fetchone()[0])
cur.close(); conn.close()