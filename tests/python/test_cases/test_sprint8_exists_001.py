#!/usr/bin/env python3
"""
Sprint 8 EXISTS 测试

测试目标：验证 EXISTS 操作的正确翻译
EXISTS 测试子查询是否返回结果
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestExistsBasic(TestCaseBase):
    """EXISTS 基础测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - EXISTS 子查询"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1 FROM employees AS e
            WHERE e.department_id = d.department_id
        )
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestExistsWithFilter(TestCaseBase):
    """EXISTS + FILTER 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
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
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 关联 EXISTS"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name"
        FROM employees AS e
        WHERE EXISTS (
            SELECT 1 FROM projects AS p
            WHERE p.project_id = e.project_id
              AND p.budget > e.salary
        )
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestExistsNested(TestCaseBase):
    """嵌套 EXISTS 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
            ?emp <http://example.org/project_id> ?proj .
            ?proj <http://example.org/project_status> "In Progress" .
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 嵌套 EXISTS"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1 FROM employees AS e
            JOIN projects AS p ON e.project_id = p.project_id
            WHERE e.department_id = d.department_id
              AND EXISTS (
                  SELECT 1 FROM projects AS p2
                  WHERE p2.project_id = p.project_id
                    AND p2.status = 'In Progress'
              )
        )
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestExistsWithValues(TestCaseBase):
    """EXISTS + VALUES 组合测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          VALUES ?dept { 1 2 3 }
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 70000)
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - VALUES + EXISTS"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE d.department_id IN (1, 2, 3)
          AND EXISTS (
              SELECT 1 FROM employees AS e
              WHERE e.department_id = d.department_id
                AND e.salary > 70000
          )
        ORDER BY d.department_id
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
        ("EXISTS - 基础", TestExistsBasic),
        ("EXISTS - 带 FILTER", TestExistsWithFilter),
        ("EXISTS - 嵌套", TestExistsNested),
        ("EXISTS - 与 VALUES 组合", TestExistsWithValues),
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
