from pathlib import Path
files = [
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_agg_001.py',
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_having_001.py',
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_having_002.py',
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_join_002.py',
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_map_002.py',
'/home/yuxiaoyu/rs_ontop_core/tests/python/test_cases/test_unified_perf_001.py',
]
for fp in files:
    p=Path(fp)
    s=p.read_text(encoding='utf-8')
    s=s.replace('} GROUP BY ?deptName HAVING (AVG(?salary) > 50000 && COUNT(?emp) > 5)','} GROUP BY ?deptName HAVING (AVG(?salary) > 50000 && COUNT(?emp) > 5) ORDER BY ?deptName')
    s=s.replace('} GROUP BY ?deptName HAVING (AVG(?salary) > 50000)','} GROUP BY ?deptName HAVING (AVG(?salary) > 50000) ORDER BY ?deptName')
    s=s.replace('} GROUP BY ?deptName','} GROUP BY ?deptName ORDER BY ?deptName')

    s=s.replace('HAVING AVG(emp.salary) > 50000 AND COUNT(emp.employee_id) > 5','HAVING AVG(emp.salary) > 50000 AND COUNT(emp.employee_id) > 5\n          ORDER BY dep.department_name')
    s=s.replace('HAVING AVG(emp.salary) > 50000','HAVING AVG(emp.salary) > 50000\n          ORDER BY dep.department_name')
    s=s.replace('GROUP BY dep.department_name','GROUP BY dep.department_name\n          ORDER BY dep.department_name')

    # dedup accidental duplicates
    s=s.replace('ORDER BY dep.department_name\n          ORDER BY dep.department_name','ORDER BY dep.department_name')
    p.write_text(s,encoding='utf-8')
print('patched explicit order by')
