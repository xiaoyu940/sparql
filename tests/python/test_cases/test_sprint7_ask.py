#!/usr/bin/env python3
"""
测试案例: ASK 查询 [S7-P0-2]

验证 ASK 查询是否能正确翻译为布尔结果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestAskBasic(TestCaseBase):
    """ASK 基础查询测试"""
    
    def sparql_query(self) -> QueryResult:
        """SPARQL ASK 查询"""
        sparql = """ASK { 
            ?emp <http://example.org/first_name> ?firstName . 
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 检查是否存在符合条件的记录"""
        baseline_sql = """
        SELECT EXISTS(
            SELECT 1 FROM employees WHERE first_name IS NOT NULL
        ) AS result
        """
        return self.execute_sql_query(baseline_sql)


class TestAskWithFilter(TestCaseBase):
    """ASK 带 FILTER 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """ASK { 
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 100000)
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT EXISTS(
            SELECT 1 FROM employees WHERE salary > 100000
        ) AS result
        """
        return self.execute_sql_query(baseline_sql)


class TestAskPatternNotExist(TestCaseBase):
    """ASK 不存在的模式测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """ASK { 
            ?emp <http://example.org/nonexistent_property> ?value .
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT false AS result
        """
        return self.execute_sql_query(baseline_sql)


class TestAskWithJoin(TestCaseBase):
    """ASK 带 JOIN 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """ASK { 
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> "Engineering" .
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT EXISTS(
            SELECT 1 FROM employees e
            JOIN departments d ON e.department_id = d.department_id
            WHERE d.department_name = 'Engineering'
        ) AS result
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
        ("ASK 基础查询", TestAskBasic),
        ("ASK 带 FILTER", TestAskWithFilter),
        ("ASK 不存在模式", TestAskPatternNotExist),
        ("ASK 带 JOIN", TestAskWithJoin),
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
