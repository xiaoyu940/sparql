#!/usr/bin/env python3
"""
Sprint 8 VALUES 单变量测试

测试目标：验证单变量 VALUES 数据块的正确翻译
VALUES 提供内联数据表，用于多值匹配
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestValuesSingleVar(TestCaseBase):
    """单变量 VALUES 基础测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          VALUES ?emp { <http://example.org/emp1> <http://example.org/emp2> <http://example.org/emp3> }
        }
        ORDER BY ?emp
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - VALUES 子句或 IN 条件"""
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE employee_id IN (1, 2, 3)
        ORDER BY employee_id
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesNumeric(TestCaseBase):
    """VALUES 数值测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/dept_name> ?name .
          VALUES ?dept { 1 2 3 4 5 }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL"""
        baseline_sql = """
        SELECT department_id AS "dept", department_name AS "name"
        FROM departments
        WHERE department_id IN (1, 2, 3, 4, 5)
        ORDER BY department_id
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesWithFilter(TestCaseBase):
    """VALUES + FILTER 组合"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?salary
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/salary> ?salary .
          VALUES ?emp { <http://example.org/emp1> <http://example.org/emp2> <http://example.org/emp3> }
          FILTER(?salary > 50000)
        }
        ORDER BY ?emp
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - VALUES + WHERE 条件"""
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name", salary AS "salary"
        FROM employees
        WHERE employee_id IN (1, 2, 3)
          AND salary > 50000
        ORDER BY employee_id
        """
        return self.execute_sql_query(baseline_sql)


class TestValuesLargeSet(TestCaseBase):
    """VALUES 大数据集测试 - 验证性能"""
    
    def sparql_query(self) -> QueryResult:
        # 测试 VALUES 包含较多元素时的性能
        values_list = " ".join([f"<http://example.org/emp{i}>" for i in range(1, 21)])
        sparql = f"""
        SELECT ?emp ?name
        WHERE {{
          ?emp <http://example.org/first_name> ?name .
          VALUES ?emp {{ {values_list} }}
        }}
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL"""
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE employee_id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20)
        ORDER BY employee_id
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
        ("VALUES - 单变量 URI", TestValuesSingleVar),
        ("VALUES - 数值", TestValuesNumeric),
        ("VALUES - 带 FILTER", TestValuesWithFilter),
        ("VALUES - 大数据集", TestValuesLargeSet),
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
