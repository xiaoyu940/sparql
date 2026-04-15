import os
import psycopg2
from tests.sparql.test_aggregate_subquery import TestSubqueryExists, TestSubqueryNotExists

conn = psycopg2.connect(host="localhost", port=5432, dbname="rs_ontop_core", user="yuxiaoyu", password=os.environ.get("PGPASSWORD", "123456"))
cur = conn.cursor()
for cls in (TestSubqueryExists, TestSubqueryNotExists):
    q = cls().sparql_query()
    cur.execute("SELECT ontop_translate(%s)", (q,))
    print("===", cls.__name__, "===")
    print(cur.fetchone()[0])
cur.close()
conn.close()