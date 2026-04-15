from pathlib import Path
import re
p=Path('/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_sprint8_values_002.py')
s=p.read_text(encoding='utf-8')

# MultiVar baseline
s=re.sub(r'baseline_sql = """\n\s*SELECT v\.dept, v\.name[\s\S]*?ORDER BY v\.dept\n\s*"""',
'''baseline_sql = """
        SELECT v.dept, v.name
        FROM (VALUES (1, 'Engineering'), (2, 'Sales'), (3, 'Marketing')) AS v(dept, name)
        JOIN departments AS d ON d.department_id = v.dept
        ORDER BY v.dept
        """''',s,count=1)

# JoinPattern baseline (second baseline_sql occurrence)
matches=list(re.finditer(r'baseline_sql = """',s))
if len(matches) >= 2:
    start=matches[1].start()
    end=s.find('"""',matches[1].end())
    end=s.find('"""',end+3)

# easier with class-targeted substitution
s=re.sub(r'(class TestValuesJoinPattern\(TestCaseBase\):[\s\S]*?baseline_sql = """\n)([\s\S]*?)(\n\s*"""\n\s*return self\.execute_sql_query\(baseline_sql\))',
r'''\1        SELECT e.employee_id AS "emp", e.first_name AS "name",
               t.dept AS "target_dept", t.min_salary AS "target_salary"
        FROM employees AS e
        JOIN (VALUES (1, 50000), (2, 60000), (3, 55000)) AS t(dept, min_salary)
          ON e.department_id = t.dept AND e.salary >= t.min_salary
        ORDER BY e.employee_id
        LIMIT 10\3''',s,count=1)

# MixedTypes baseline
s=re.sub(r'(class TestValuesMixedTypes\(TestCaseBase\):[\s\S]*?baseline_sql = """\n)([\s\S]*?)(\n\s*"""\n\s*return self\.execute_sql_query\(baseline_sql\))',
r'''\1        SELECT e.employee_id AS "emp", e.first_name AS "name", e.hire_date
        FROM employees AS e
        JOIN (VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie')) AS v(emp, name)
          ON e.employee_id = v.emp AND e.first_name = v.name
        ORDER BY e.employee_id\3''',s,count=1)

p.write_text(s,encoding='utf-8')
print('rewrote VALUES baselines with valid SQL and aligned semantics')
