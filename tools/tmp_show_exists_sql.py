import os, psycopg2
from tests.python.test_cases.test_sprint8_exists_001 import TestExistsNested, TestExistsWithFilter, TestExistsWithValues
from tests.python.test_cases.test_sprint8_exists_002 import TestNotExistsWithAggregate, TestNotExistsWithFilter
from tests.python.framework import DatabaseConfig

cfg = DatabaseConfig()
conn = psycopg2.connect(host=cfg.host, port=cfg.port, dbname=cfg.database, user=cfg.user, password=cfg.password)
cur = conn.cursor()
cases = [TestExistsNested, TestExistsWithFilter, TestExistsWithValues, TestNotExistsWithAggregate, TestNotExistsWithFilter]
for cls in cases:
    t = cls(cfg)
    q = t.get_sparql_query()
    cur.execute("SELECT ontop_translate(%s)", (q,))
    sql = cur.fetchone()[0]
    print("\n===", cls.__name__, "===")
    print(sql[:3000])
cur.close(); conn.close()
