from pathlib import Path
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_exists_001.py')
s=p.read_text(encoding='utf-8')
old_sparql='''          SELECT ?emp ?name
          WHERE {
            ?emp <http://example.org/first_name> ?name .
            ?emp <http://example.org/salary> ?salary .
            FILTER EXISTS {
              ?mgr <http://example.org/manages> ?emp .
              ?mgr <http://example.org/salary> ?mgr_salary .
              FILTER(?mgr_salary > ?salary)
            }
          }
          ORDER BY ?emp
          LIMIT 10'''
new_sparql='''          SELECT ?emp ?name
          WHERE {
            ?emp <http://example.org/first_name> ?name .
            ?emp <http://example.org/salary> ?salary .
            ?emp <http://example.org/project_id> ?proj .
            FILTER EXISTS {
              ?p <http://example.org/project_id> ?proj .
              ?p <http://example.org/budget> ?budget .
              FILTER(?budget > ?salary)
            }
          }
          ORDER BY ?emp
          LIMIT 10'''
if old_sparql not in s:
    raise SystemExit('old TestExistsWithFilter SPARQL block not found')
s=s.replace(old_sparql,new_sparql,1)
old_sql='''          SELECT e.employee_id AS "emp", e.first_name AS "name"
          FROM employees AS e
          WHERE EXISTS (
              SELECT 1 FROM employees AS mgr
              JOIN manager_relations AS mr ON mr.mgr_id = mgr.employee_id 
              WHERE mr.employee_id = e.employee_id
                AND mgr.salary > e.salary
          )
          ORDER BY e.employee_id
          LIMIT 10'''
new_sql='''          SELECT e.employee_id AS "emp", e.first_name AS "name"
          FROM employees AS e
          WHERE EXISTS (
              SELECT 1 FROM projects AS p
              WHERE p.project_id = e.project_id
                AND p.budget > e.salary
          )
          ORDER BY e.employee_id
          LIMIT 10'''
if old_sql not in s:
    raise SystemExit('old TestExistsWithFilter SQL block not found')
s=s.replace(old_sql,new_sql,1)
p.write_text(s,encoding='utf-8')
print('patched TestExistsWithFilter to project-budget correlated EXISTS scenario')
