#!/usr/bin/env python3
"""
测试案例: FILTER 查询

验证条件过滤功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestFilterGreaterThan(TestCaseBase):
    """大于条件测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?firstName ?salary
        WHERE { 
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 80000)
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS firstname, salary AS salary
        FROM employees
        WHERE salary > 80000
        """
        return self.execute_sql_query(baseline_sql)


class TestFilterEquals(TestCaseBase):
    """等于条件测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?firstName ?lastName
        WHERE { 
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/last_name> ?lastName .
            FILTER(?firstName = 'First1')
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS firstname, last_name AS lastname
        FROM employees
        WHERE first_name = 'First1'
        """
        return self.execute_sql_query(baseline_sql)


class TestFilterLessThan(TestCaseBase):
    """小于条件测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?firstName ?salary
        WHERE { 
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary < 60000)
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT first_name AS firstname, salary AS salary
        FROM employees
        WHERE salary < 60000
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
        ("FILTER > (大于)", TestFilterGreaterThan),
        ("FILTER = (等于)", TestFilterEquals),
        ("FILTER < (小于)", TestFilterLessThan),
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
