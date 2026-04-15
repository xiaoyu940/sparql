#!/usr/bin/env python3
"""
Sprint 8 NOT EXISTS 测试

测试目标：验证 NOT EXISTS 操作的正确翻译
NOT EXISTS 测试子查询是否不返回结果
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestNotExistsBasic(TestCaseBase):
    """NOT EXISTS 基础测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          FILTER NOT EXISTS {
            ?emp <http://example.org/has_manager> ?mgr .
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - NOT EXISTS"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name"
        FROM employees AS e
        WHERE NOT EXISTS (
            SELECT 1 FROM manager_relations AS mr
            WHERE mr.employee_id = e.employee_id
        )
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestNotExistsWithFilter(TestCaseBase):
    """NOT EXISTS + FILTER 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          FILTER NOT EXISTS {
            ?emp <http://example.org/department_id> ?dept .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary < 40000)
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - NOT EXISTS 带内部 FILTER"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.salary < 40000
        )
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestNotExistsMultiple(TestCaseBase):
    """多个 NOT EXISTS 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          FILTER NOT EXISTS {
            ?emp <http://example.org/has_manager> ?mgr .
          }
          FILTER NOT EXISTS {
            ?emp <http://example.org/is_contractor> true .
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 多个 NOT EXISTS"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name"
        FROM employees AS e
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS mgr
            WHERE mgr.employee_id = e.manager_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = e.employee_id
              AND e2.is_contractor = true
        )
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestNotExistsWithAggregate(TestCaseBase):
    """NOT EXISTS + 聚合组合"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name (COUNT(?emp) AS ?count)
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          ?emp <http://example.org/department_id> ?dept .
          FILTER NOT EXISTS {
            ?emp <http://example.org/is_on_leave> true .
          }
        }
        GROUP BY ?dept ?name
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - NOT EXISTS 在聚合前过滤"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name",
               COUNT(e.employee_id) AS "count"
        FROM departments AS d
        JOIN employees AS e ON e.department_id = d.department_id
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = e.employee_id
              AND e2.is_on_leave = true
        )
        GROUP BY d.department_id, d.department_name
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestExistsAndNotExists(TestCaseBase):
    """EXISTS 和 NOT EXISTS 组合"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
          }
          FILTER NOT EXISTS {
            ?emp <http://example.org/is_fired> true .
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - EXISTS + NOT EXISTS"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name"
        FROM employees AS e
        WHERE EXISTS (
            SELECT 1 FROM departments AS d
            WHERE d.department_id = e.department_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = e.employee_id
              AND e2.is_fired = true
        )
        ORDER BY e.employee_id
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
        ("NOT EXISTS - 基础", TestNotExistsBasic),
        ("NOT EXISTS - 带 FILTER", TestNotExistsWithFilter),
        ("NOT EXISTS - 多个组合", TestNotExistsMultiple),
        ("NOT EXISTS - 与聚合组合", TestNotExistsWithAggregate),
        ("EXISTS + NOT EXISTS 组合", TestExistsAndNotExists),
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
