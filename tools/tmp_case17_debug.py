import os, psycopg2
from tests.python.framework import DatabaseConfig
from tests.python.test_cases.test_sprint7_construct import TestConstructWithFilter
cfg=DatabaseConfig()
t=TestConstructWithFilter(cfg)
q=t.get_sparql_query()
print('QUERY:\n',q)
conn=psycopg2.connect(host=cfg.host,port=cfg.port,dbname=cfg.database,user=cfg.user,password=cfg.password)
cur=conn.cursor(); cur.execute('SELECT ontop_translate(%s)',(q,)); sql=cur.fetchone()[0]; print('SQL:\n',sql)
cur.execute(sql)
rows=cur.fetchall(); print('rows',len(rows))
cur.close(); conn.close()
