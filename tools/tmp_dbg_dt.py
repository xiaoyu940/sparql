import os, psycopg2
queries=[
'''SELECT ?currenttime WHERE { BIND(NOW() AS ?currenttime) }''',
'''PREFIX ex: <http://example.org/> SELECT ?name ?hireyear WHERE { ?emp ex:name ?name ; ex:hireDate ?date . BIND(YEAR(?date) AS ?hireyear) FILTER(?hireyear > 2020) } LIMIT 10''',
'''PREFIX ex:<http://example.org/> SELECT ?name ?yearsofservice WHERE { ?emp ex:name ?name ; ex:hireDate ?hireDate . BIND(YEAR(NOW()) - YEAR(?hireDate) AS ?yearsofservice) FILTER(?yearsofservice > 5)}'''
]
conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password=os.environ.get('PGPASSWORD','123456'))
cur=conn.cursor()
for i,q in enumerate(queries,1):
    print('\n---Q',i)
    cur.execute('SELECT ontop_debug_parse(%s)',(q,))
    print(cur.fetchone()[0])
    try:
        cur.execute('SELECT ontop_translate(%s)',(q,))
        print('sql',cur.fetchone()[0][:500])
    except Exception as e:
        print('translate err',e)
        conn.rollback()
cur.close(); conn.close()
