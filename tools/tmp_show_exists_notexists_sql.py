import os, sys, psycopg2
sys.path.append('/home/yuxiaoyu/rs_ontop_core/tests/sparql')
from test_aggregate_subquery import TestSubqueryExists, TestSubqueryNotExists

conn = psycopg2.connect(host='localhost', port=5432, dbname='rs_ontop_core', user='yuxiaoyu', password=os.environ.get('PGPASSWORD','123456'))
cur = conn.cursor()
for cls in (TestSubqueryExists, TestSubqueryNotExists):
    q = cls().sparql_query()
    cur.execute('SELECT ontop_translate(%s)', (q,))
    sql = cur.fetchone()[0]
    print('\n===', cls.__name__, 'SQL===')
    print(sql)
    cur.execute(sql)
    rows = cur.fetchall()
    print('rows:', len(rows))
cur.close(); conn.close()