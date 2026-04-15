import requests, socket, psycopg2

def start():
    conn=psycopg2.connect(host='localhost',port=5432,dbname='rs_ontop_core',user='yuxiaoyu',password='123456')
    conn.autocommit=True
    cur=conn.cursor(); cur.execute('SELECT ontop_start_sparql_server()'); cur.close(); conn.close()

def alive():
    try:
        s=socket.create_connection(('127.0.0.1',5820),timeout=1)
        s.close(); return True
    except Exception:
        return False

queries = [
("bad_prefix_only", "PREFIX ex: < `http://example.org/>`\nSELECT ?x WHERE { BIND(\"a\" AS ?x) } LIMIT 1"),
("bad_prefix_pattern", "PREFIX ex: < `http://example.org/>`\nSELECT ?name WHERE { ?dept ex:department_name ?name . } LIMIT 1"),
("bad_prefix_bind", "PREFIX ex: < `http://example.org/>`\nSELECT ?name ?type WHERE { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) } LIMIT 1"),
("bad_prefix_union_no_bind", "PREFIX ex: < `http://example.org/>`\nSELECT ?name WHERE { { ?dept ex:department_name ?name . } UNION { ?pos ex:position_title ?name . } } LIMIT 5"),
("bad_prefix_union_bind", "PREFIX ex: < `http://example.org/>`\nSELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) } UNION { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) } } LIMIT 20"),
("good_prefix_union_bind", "PREFIX ex: <http://example.org/>\nSELECT ?name ?type WHERE { { ?dept ex:department_name ?name . BIND(\"Department\" AS ?type) } UNION { ?pos ex:position_title ?name . BIND(\"Position\" AS ?type) } } LIMIT 20"),
]

for name,q in queries:
    if not alive():
        start()
    try:
        r=requests.post('http://127.0.0.1:5820/sparql',data=q.encode('utf-8'),timeout=6)
        status=r.status_code
        body=r.text[:100].replace('\n',' ')
    except Exception as e:
        status='ERR'; body=str(e)
    print(f"{name} => {status} {body} | alive_after={alive()}")