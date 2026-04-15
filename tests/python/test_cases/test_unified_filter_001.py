#!/usr/bin/env python3
"""
测试案例: 大于条件

验证 SPARQL 大于条件FILTER查询是否正确翻译为 SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestFil001(TestCaseBase):
    """测试大于条件: employees, salaries"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 获取薪资超过80000的员工
        
        对应 SQL:
        SELECT emp.first_name AS firstName, emp.salary AS salary
        FROM employees AS emp
        INNER JOIN salaries AS sal ON emp.employee_id = sal.employee_id
        WHERE emp.salary > 80000
        """
        sparql = """
        SELECT ?firstName ?salary WHERE {
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 80000)
        }
        """
        
        # 翻译 SPARQL
        sql = self.translate_sparql(sparql)
        self._generated_sql = sql
        
        # 验证生成的 SQL 包含预期模式
        expected_patterns = [">"]
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
        SELECT emp.first_name AS firstName, emp.salary AS salary
        FROM employees AS emp
        INNER JOIN salaries AS sal ON emp.employee_id = sal.employee_id
        WHERE emp.salary > 80000
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
    print(f"测试: 大于条件")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestFil001, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
