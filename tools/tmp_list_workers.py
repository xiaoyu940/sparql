import os, psycopg2
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor()
cur.execute('SELECT pid, backend_type, application_name, state FROM pg_stat_activity')
for r in cur.fetchall():
    bt=(r[1] or '').lower(); app=(r[2] or '').lower()
    if 'worker' in bt or 'ontop' in bt or 'ontop' in app:
        print(r)
cur.close(); conn.close()