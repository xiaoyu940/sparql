#!/usr/bin/env python3
"""
Sprint 8 MINUS 测试

测试目标：验证 MINUS 操作的正确翻译
MINUS 返回在左操作数中存在、但在右操作数中不存在的解
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestMinusBasic(TestCaseBase):
    """MINUS 基础测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/department_id> ?dept .
          MINUS {
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary < 50000)
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 使用 NOT EXISTS 或 LEFT JOIN"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name"
        FROM employees AS e
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = e.employee_id
              AND e2.salary < 50000
        )
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestMinusWithSharedVar(TestCaseBase):
    """MINUS 共享变量测试 - 必须共享至少一个变量"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          MINUS {
            ?emp <http://example.org/department_id> ?dept .
            ?emp <http://example.org/fired> true .
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - LEFT JOIN + IS NULL 或 NOT EXISTS"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.is_fired = true
        )
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestMinusMultiplePatterns(TestCaseBase):
    """MINUS 多个模式测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          MINUS {
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/is_closed> true .
          }
          MINUS {
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
            SELECT 1 FROM departments AS d
            WHERE d.department_id = e.department_id
              AND d.is_closed = true
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


class TestMinusWithAggregate(TestCaseBase):
    """MINUS + 聚合组合测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept (COUNT(?emp) AS ?total)
        WHERE {
          ?emp <http://example.org/department_id> ?dept .
          MINUS {
            ?emp <http://example.org/is_on_leave> true .
          }
        }
        GROUP BY ?dept
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - MINUS 在聚合前应用"""
        baseline_sql = """
        SELECT e.department_id AS "dept", COUNT(e.employee_id) AS "total"
        FROM employees AS e
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = e.employee_id
              AND e2.is_on_leave = true
        )
        GROUP BY e.department_id
        ORDER BY e.department_id
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
        ("MINUS - 基础", TestMinusBasic),
        ("MINUS - 共享变量", TestMinusWithSharedVar),
        ("MINUS - 多个模式", TestMinusMultiplePatterns),
        ("MINUS - 与聚合组合", TestMinusWithAggregate),
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
