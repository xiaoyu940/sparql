#!/usr/bin/env python3
"""
Sprint 8 子查询基础测试

测试目标：验证非关联子查询（标量子查询和派生表）的正确翻译和执行
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestSubQueryBasic(TestCaseBase):
    """基础子查询测试 - 标量子查询"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?total
        WHERE {
          {
            SELECT ?dept (COUNT(?emp) AS ?total)
            WHERE {
              ?emp <http://example.org/department_id> ?dept .
            }
            GROUP BY ?dept
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 使用派生表"""
        baseline_sql = """
        SELECT department_id AS "dept", COUNT(employee_id) AS "total"
        FROM employees
        GROUP BY department_id
        ORDER BY department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestSubQueryDerivedTable(TestCaseBase):
    """派生表子查询测试 - 作为数据源"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?avg_salary
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/salary> ?salary .
          {
            SELECT (AVG(?s) AS ?avg_salary)
            WHERE {
              ?e <http://example.org/salary> ?s .
            }
          }
          FILTER(?salary > ?avg_salary)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 标量子查询 + JOIN"""
        baseline_sql = """
        SELECT e.employee_id AS "emp", e.first_name AS "name", avg_sub.avg_salary
        FROM employees AS e
        CROSS JOIN (
            SELECT AVG(salary) AS avg_salary FROM employees
        ) AS avg_sub
        WHERE e.salary > avg_sub.avg_salary
        ORDER BY e.employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestSubQueryWithFilter(TestCaseBase):
    """带 FILTER 的子查询"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name ?high_earners
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          {
            SELECT ?dept (COUNT(?emp) AS ?high_earners)
            WHERE {
              ?emp <http://example.org/department_id> ?dept .
              ?emp <http://example.org/salary> ?salary .
              FILTER(?salary > 80000)
            }
            GROUP BY ?dept
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 子查询带 WHERE 条件"""
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name", 
               COALESCE(high_earners.cnt, 0) AS "high_earners"
        FROM departments AS d
        LEFT JOIN (
            SELECT department_id, COUNT(employee_id) AS cnt
            FROM employees
            WHERE salary > 80000
            GROUP BY department_id
        ) AS high_earners ON d.department_id = high_earners.department_id
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
        ("子查询基础 - 标量子查询", TestSubQueryBasic),
        ("子查询 - 派生表", TestSubQueryDerivedTable),
        ("子查询 - 带 FILTER", TestSubQueryWithFilter),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class)
        if not result['passed']:
            all_passed = False
            print(f"✗ 失败: {result.get('errors', [])}")
        else:
            print(f"✓ 测试通过")
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
