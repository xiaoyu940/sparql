#!/usr/bin/env python3
"""
测试案例: 基础HAVING

验证 SPARQL 基础HAVING查询是否正确翻译为 SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestHaving001(TestCaseBase):
    """测试基础HAVING: employees, departments, salaries"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 获取平均薪资超过50000的部门
        
        对应 SQL:
        SELECT dep.department_name AS deptName, AVG(emp.salary) AS avgSalary
        FROM departments AS dep 
        INNER JOIN employees AS emp ON dep.department_id = emp.department_id
        INNER JOIN salaries AS sal ON emp.employee_id = sal.employee_id
        GROUP BY dep.department_name
          ORDER BY dep.department_name
        HAVING AVG(emp.salary) > 50000
          ORDER BY dep.department_name
        """
        sparql = """
        SELECT ?deptName (AVG(?salary) AS ?avgSalary)
        WHERE {
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
            ?emp <http://example.org/salary> ?salary .
        } GROUP BY ?deptName HAVING (AVG(?salary) > 50000) ORDER BY ?deptName
        """
        
        # 翻译 SPARQL
        sql = self.translate_sparql(sparql)
        self._generated_sql = sql
        
        # 验证生成的 SQL 包含预期模式
        expected_patterns = ["HAVING", "AVG"]
        excluded_patterns = []
        
        for pattern in expected_patterns:
            if pattern not in sql:
                return QueryResult(
                    passed=False,
                    error=f"Missing expected pattern: {pattern}",
                    sql=sql
                )
        
        for pattern in excluded_patterns:
            if pattern in sql:
                return QueryResult(
                    passed=False,
                    error=f"Found excluded pattern: {pattern}",
                    sql=sql
                )
        
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        基准 SQL - 这是我们认为正确的查询
        """
        baseline_sql = """
        SELECT dep.department_name AS deptName, AVG(emp.salary) AS avgSalary
        FROM departments AS dep
        INNER JOIN employees AS emp ON dep.department_id = emp.department_id
        INNER JOIN salaries AS sal ON emp.employee_id = sal.employee_id
        GROUP BY dep.department_name
        HAVING AVG(emp.salary) > 50000
        ORDER BY dep.department_name
        """

        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    import json
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    print(f"\n{'='*80}")
    print(f"测试: 基础HAVING")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestHaving001, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
