import os,time,psycopg2,requests
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
conn.autocommit=True
cur=conn.cursor()
cur.execute('SELECT ontop_start_sparql_server()')
cur.execute("SELECT pid FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway' ORDER BY pid DESC LIMIT 1")
pid=cur.fetchone()[0]
print('pid_before',pid)
cur.execute('SELECT pg_terminate_backend(%s)',(pid,))
print('terminated',cur.fetchone()[0])
cur.close(); conn.close()
for i in range(1,8):
    time.sleep(1)
    try:
        r=requests.get('http://127.0.0.1:5820/sparql',timeout=2)
        print('t',i,'http',r.status_code)
        if r.status_code in (400,200,405):
            break
    except Exception as e:
        print('t',i,'down',e)
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor(); cur.execute("SELECT count(*) FROM pg_stat_activity WHERE backend_type='rs_ontop_core SPARQL Web Gateway'")
print('bgworker_count',cur.fetchone()[0]); cur.close(); conn.close()