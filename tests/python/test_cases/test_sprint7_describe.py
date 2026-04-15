#!/usr/bin/env python3
"""
测试案例: DESCRIBE 查询 [S7-P1-1]

验证 DESCRIBE 查询是否能正确翻译并返回资源描述
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestDescribeResource(TestCaseBase):
    """DESCRIBE 单一资源测试"""
    
    def sparql_query(self) -> QueryResult:
        """SPARQL DESCRIBE 查询"""
        sparql = """DESCRIBE <http://example.org/emp1>"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 查询资源所有属性"""
        baseline_sql = """
        SELECT 
            'http://example.org/emp1' AS subject,
            p.predicate,
            p.object
        FROM (
            SELECT 'first_name' AS predicate, first_name::text AS object FROM employees WHERE employee_id = 1
            UNION ALL
            SELECT 'last_name' AS predicate, last_name::text AS object FROM employees WHERE employee_id = 1
            UNION ALL
            SELECT 'email' AS predicate, email::text AS object FROM employees WHERE employee_id = 1
            UNION ALL
            SELECT 'salary' AS predicate, salary::text AS object FROM employees WHERE employee_id = 1
        ) p
        WHERE p.object IS NOT NULL
        """
        return self.execute_sql_query(baseline_sql)


class TestDescribeVariable(TestCaseBase):
    """DESCRIBE 变量测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """DESCRIBE ?emp
        WHERE { 
            ?emp <http://example.org/first_name> ?firstName .
            FILTER(?firstName = 'First1')
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT e.employee_id AS emp_uri, 'first_name' AS predicate, e.first_name AS object
        FROM employees e
        WHERE e.first_name = 'First1'
        """
        return self.execute_sql_query(baseline_sql)


class TestDescribeWithLimit(TestCaseBase):
    """DESCRIBE 带 LIMIT 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """DESCRIBE ?emp
        WHERE { ?emp a <http://example.org/Employee> . }
        LIMIT 3"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT DISTINCT e.employee_id AS emp
        FROM employees e
        LIMIT 3
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("DESCRIBE 单一资源", TestDescribeResource),
        ("DESCRIBE 变量", TestDescribeVariable),
        ("DESCRIBE 带 LIMIT", TestDescribeWithLimit),
    ]
    
    all_passed = True
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = run_test_case(test_class, db_config)
        if not result['passed']:
            all_passed = False
            print(f"✗ 失败: {result['errors']}")
    
    sys.exit(0 if all_passed else 1)
