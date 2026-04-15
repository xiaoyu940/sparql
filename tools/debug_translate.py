import os
import psycopg2

conn = psycopg2.connect(host="localhost", port=5432, dbname="rs_ontop_core", user="yuxiaoyu", password=os.environ.get("PGPASSWORD", "123456"))
cur = conn.cursor()
cur.execute("SELECT ontop_refresh();")
print(cur.fetchone())
queries = [
    "ASK { ?emp <http://example.org/nonexistent_property> ?value . }",
    "ASK { ?emp <http://example.org/department_id> ?dept . ?dept <http://example.org/department_name> \"Engineering\" . }"
]
for q in queries:
    cur.execute("SELECT ontop_translate(%s)", (q,))
    sql = cur.fetchone()[0]
    print("---")
    print(q)
    print(sql)
cur.close()
conn.close()
