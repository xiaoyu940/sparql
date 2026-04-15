#!/usr/bin/env python3
"""
Sprint 8 关联子查询测试

测试目标：验证关联子查询（引用外部变量）的正确翻译
关联子查询通常转换为 LATERAL JOIN 或 EXISTS 子查询
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestCorrelatedSubQueryExists(TestCaseBase):
    """关联子查询 - EXISTS 形式"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 80000)
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 使用 EXISTS 子查询"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1 FROM employees AS e
            WHERE e.department_id = d.department_id
              AND e.salary > 80000
        )
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestCorrelatedSubQueryLateral(TestCaseBase):
    """关联子查询 - LATERAL JOIN 形式 (PostgreSQL)"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?dept_name ?avg_dept_salary
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/department_id> ?dept .
          ?dept <http://example.org/dept_name> ?dept_name .
          {
            SELECT (AVG(?s) AS ?avg_dept_salary)
            WHERE {
              ?e <http://example.org/salary> ?s .
              ?e <http://example.org/department_id> ?dept .
            }
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 使用 LATERAL JOIN"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name",
               d.department_name AS "dept_name", dept_avg.avg_salary AS "avg_dept_salary"
        FROM employees AS e
        JOIN departments AS d ON e.department_id = d.department_id
        LEFT JOIN LATERAL (
            SELECT AVG(salary) AS avg_salary
            FROM employees AS inner_e
            WHERE inner_e.department_id = e.department_id
        ) AS dept_avg ON true
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestNestedSubQuery(TestCaseBase):
    """嵌套子查询"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name ?top_salary
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          {
            SELECT ?dept (MAX(?salary) AS ?top_salary)
            WHERE {
              ?emp <http://example.org/department_id> ?dept .
              ?emp <http://example.org/salary> ?salary .
              FILTER EXISTS {
                ?emp <http://example.org/first_name> ?fn .
                FILTER(STRLEN(?fn) > 3)
              }
            }
            GROUP BY ?dept
          }
        }
        HAVING(?top_salary > 70000)
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 嵌套 EXISTS"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name", sub.top_salary
        FROM departments AS d
        JOIN (
            SELECT e.department_id, MAX(e.salary) AS top_salary
            FROM employees AS e
            WHERE EXISTS (
                SELECT 1 FROM employees AS e2
                WHERE e2.employee_id = e.employee_id
                  AND LENGTH(e2.first_name) > 3
            )
            GROUP BY e.department_id
        ) AS sub ON d.department_id = sub.department_id
        WHERE sub.top_salary > 70000
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
        ("关联子查询 - EXISTS", TestCorrelatedSubQueryExists),
        ("关联子查询 - LATERAL JOIN", TestCorrelatedSubQueryLateral),
        ("嵌套子查询", TestNestedSubQuery),
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
