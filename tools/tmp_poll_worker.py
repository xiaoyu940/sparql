import os,time,psycopg2
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
conn.autocommit=True
cur=conn.cursor()
cur.execute('SELECT ontop_start_sparql_server();')
print('called start')
for i in range(1,11):
    time.sleep(1)
    cur.execute("select count(*) from pg_stat_activity where backend_type ilike '%worker%' or application_name ilike '%ontop%'")
    c=cur.fetchone()[0]
    print('sec',i,'workers',c)
    if c:
        cur.execute("select pid,backend_type,application_name,state from pg_stat_activity where backend_type ilike '%worker%' or application_name ilike '%ontop%' order by pid")
        print(cur.fetchall())
cur.close(); conn.close()
