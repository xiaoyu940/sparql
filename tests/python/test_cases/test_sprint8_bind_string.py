#!/usr/bin/env python3
"""
Sprint 8 BIND 字符串函数测试

测试目标：验证 BIND 表达式中字符串函数的正确翻译
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestBindConcat(TestCaseBase):
    """BIND CONCAT 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?full_name
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          ?emp <http://example.org/last_name> ?last .
          BIND(CONCAT(?first, " ", ?last) AS ?full_name)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - CONCAT 映射到 ||"""
        baseline_sql = """
        SELECT employee_id AS "emp", (first_name || ' ' || last_name) AS "full_name"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindSubstring(TestCaseBase):
    """BIND SUBSTR 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?initials
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          ?emp <http://example.org/last_name> ?last .
          BIND(CONCAT(SUBSTR(?first, 1, 1), SUBSTR(?last, 1, 1)) AS ?initials)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - SUBSTR 映射到 SUBSTRING"""
        baseline_sql = """
        SELECT employee_id AS "emp", 
               (SUBSTRING(first_name FROM 1 FOR 1) || SUBSTRING(last_name FROM 1 FOR 1)) AS "initials"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindUpperLower(TestCaseBase):
    """BIND UCASE/LCASE 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?upper_name ?lower_name
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          BIND(UCASE(?first) AS ?upper_name)
          BIND(LCASE(?first) AS ?lower_name)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - UCASE/LCASE 映射到 UPPER/LOWER"""
        baseline_sql = """
        SELECT employee_id AS "emp", 
               UPPER(first_name) AS "upper_name",
               LOWER(first_name) AS "lower_name"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindStrlen(TestCaseBase):
    """BIND STRLEN 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name_length
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          BIND(STRLEN(?first) AS ?name_length)
        }
        HAVING(?name_length > 3)
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - STRLEN 映射到 LENGTH"""
        baseline_sql = """
        SELECT employee_id AS "emp", LENGTH(first_name) AS "name_length"
        FROM employees
        WHERE LENGTH(first_name) > 3
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestBindReplace(TestCaseBase):
    """BIND REPLACE 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?masked_name
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          BIND(REPLACE(?first, "a", "*") AS ?masked_name)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - REPLACE"""
        baseline_sql = """
        SELECT employee_id AS "emp", REPLACE(first_name, 'a', '*') AS "masked_name"
        FROM employees
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
        ("BIND - CONCAT 字符串连接", TestBindConcat),
        ("BIND - SUBSTR 子串", TestBindSubstring),
        ("BIND - UCASE/LCASE 大小写", TestBindUpperLower),
        ("BIND - STRLEN 长度", TestBindStrlen),
        ("BIND - REPLACE 替换", TestBindReplace),
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
