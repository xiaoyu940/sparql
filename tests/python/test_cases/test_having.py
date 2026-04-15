#!/usr/bin/env python3
"""
测试案例: HAVING 查询

验证 HAVING 子句是否正确翻译
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestHavingBasic(TestCaseBase):
    """基础 HAVING 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?deptName (AVG(?salary) AS ?avgSalary)
        WHERE { 
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
            ?emp <http://example.org/salary> ?salary .
        }
        GROUP BY ?deptName
        HAVING (AVG(?salary) > 50000)"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT d.department_name AS deptname, AVG(e.salary) AS avgsalary
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        HAVING AVG(e.salary) > 50000
        """
        return self.execute_sql_query(baseline_sql)


class TestHavingMultiCondition(TestCaseBase):
    """HAVING 多条件测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """SELECT ?deptName (AVG(?salary) AS ?avgSalary) (COUNT(?emp) AS ?empCount)
        WHERE { 
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
            ?emp <http://example.org/salary> ?salary .
        }
        GROUP BY ?deptName
        HAVING (AVG(?salary) > 50000 && COUNT(?emp) > 5)"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT d.department_name AS deptname, 
               AVG(e.salary) AS avgsalary,
               COUNT(e.employee_id) AS empcount
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        GROUP BY d.department_name
        HAVING AVG(e.salary) > 50000 AND COUNT(e.employee_id) > 5
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
        ("HAVING 基础", TestHavingBasic),
        ("HAVING 多条件", TestHavingMultiCondition),
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
