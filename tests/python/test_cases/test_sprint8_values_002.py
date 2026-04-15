#!/usr/bin/env python3
"""
Sprint 8 VALUES 多变量测试

测试目标：验证多变量 VALUES 数据块的正确翻译
支持元组形式的值列表
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestValuesMultiVar(TestCaseBase):
    """多变量 VALUES 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          VALUES (?dept ?name) {
            (1 "Engineering")
            (2 "Sales")
            (3 "Marketing")
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - VALUES 子句作为派生表"""
        baseline_sql = """
        SELECT v.dept, v.name
        FROM (VALUES (1, 'Engineering'), (2, 'Sales'), (3, 'Marketing')) AS v(dept, name)
        JOIN departments AS d ON d.department_id = v.dept AND d.department_name = v.name
        ORDER BY v.dept
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesJoinPattern(TestCaseBase):
    """VALUES 与图模式 JOIN"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?target_dept ?target_salary
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/department_id> ?dept .
          ?emp <http://example.org/salary> ?salary .
          VALUES (?target_dept ?target_salary) {
            (1 50000)
            (2 60000)
            (3 55000)
          }
          FILTER(?dept = ?target_dept && ?salary >= ?target_salary)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - VALUES JOIN + FILTER"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name",
               t.dept AS "target_dept", t.min_salary AS "target_salary"
        FROM employees AS e
        JOIN (VALUES (1, 50000), (2, 60000), (3, 55000)) AS t(dept, min_salary)
          ON e.department_id = t.dept AND e.salary >= t.min_salary
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesMixedTypes(TestCaseBase):
    """VALUES 混合类型测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?hire_date
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/hire_date> ?hire_date .
          VALUES (?emp ?name) {
            (<http://example.org/emp1> "Alice")
            (<http://example.org/emp2> "Bob")
            (<http://example.org/emp3> "Charlie")
          }
        }
        ORDER BY ?emp
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name", e.hire_date
        FROM employees AS e
        JOIN (VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie')) AS v(emp, name)
          ON e.employee_id = v.emp AND e.first_name = v.name
        ORDER BY e.employee_id
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesEmpty(TestCaseBase):
    """VALUES 空集测试 - 边界情况"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          VALUES ?emp { }
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 空集应返回空结果"""
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE 1=0  -- 永远为假
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
        ("VALUES - 多变量基础", TestValuesMultiVar),
        ("VALUES - 与图模式 JOIN", TestValuesJoinPattern),
        ("VALUES - 混合类型", TestValuesMixedTypes),
        ("VALUES - 空集边界", TestValuesEmpty),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class())
        if not result['passed']:
            all_passed = False
            print(f"✗ 失败: {result.get('errors', [])}")
        else:
            print(f"✓ 测试通过")
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
