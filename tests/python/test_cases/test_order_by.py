#!/usr/bin/env python3
"""
测试案例: ORDER BY 查询

验证排序和分页功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestOrderByAsc(TestCaseBase):
    """ASC 排序测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?deptName
        WHERE { ?dept <http://example.org/department_name> ?deptName . }
        ORDER BY ASC(?deptName)"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT department_name AS deptname
        FROM departments
        ORDER BY department_name ASC
        """
        return self.execute_sql_query(baseline_sql)


class TestOrderByDesc(TestCaseBase):
    """DESC 排序测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?deptName (COUNT(?emp) AS ?empCount)
        WHERE { 
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
        }
        GROUP BY ?deptName
        ORDER BY DESC(?empCount)"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT d.department_name AS deptname, COUNT(e.employee_id) AS empcount
        FROM departments d
        JOIN employees e ON e.department_id = d.department_id
        GROUP BY d.department_name
        ORDER BY empcount DESC
        """
        return self.execute_sql_query(baseline_sql)


class TestOrderByWithLimit(TestCaseBase):
    """排序带分页测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?deptName
        WHERE { ?dept <http://example.org/department_name> ?deptName . }
        ORDER BY ?deptName
        LIMIT 10"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT department_name AS deptname
        FROM departments
        ORDER BY department_name
        LIMIT 10
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
        ("ORDER BY ASC", TestOrderByAsc),
        ("ORDER BY DESC", TestOrderByDesc),
        ("ORDER BY 带 LIMIT", TestOrderByWithLimit),
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
