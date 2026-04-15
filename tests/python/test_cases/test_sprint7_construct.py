#!/usr/bin/env python3
"""
测试案例: CONSTRUCT 基础三元组 [S7-P0-1]

验证 CONSTRUCT 查询是否能正确翻译并执行
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestConstructBasicTriple(TestCaseBase):
    """CONSTRUCT 基础三元组测试"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL CONSTRUCT 查询
        构造 ?emp a Employee 三元组
        """
        sparql = """CONSTRUCT { ?emp a <http://example.org/Employee> }
        WHERE { ?emp <http://example.org/first_name> ?firstName . }
          LIMIT 10"""
        
        sql = self.translate_sparql(sparql)
        self._last_sql = sql
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        基准 SQL - 构造三元组所需的数据
        """
        # CONSTRUCT 需要查询主体数据
        baseline_sql = """
        SELECT e.employee_id AS emp
        FROM employees e
        WHERE e.first_name IS NOT NULL
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestConstructMultiplePredicates(TestCaseBase):
    """CONSTRUCT 多谓词测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """CONSTRUCT { 
            ?emp a <http://example.org/Employee> ;
                <http://example.org/hasName> ?firstName .
        } WHERE { 
            ?emp <http://example.org/first_name> ?firstName . 
        } LIMIT 5"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT e.employee_id AS emp, e.first_name AS firstname
        FROM employees e
        WHERE e.first_name IS NOT NULL
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


class TestConstructWithFilter(TestCaseBase):
    """CONSTRUCT 带 FILTER 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """CONSTRUCT { ?emp a <http://example.org/SeniorEmployee> }
        WHERE { 
            ?emp a <http://example.org/Employee> .
            ?emp <http://example.org/salary> ?salary .
            FILTER(?salary > 100000)
        }"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT e.employee_id AS emp
        FROM employees e
        WHERE e.salary > 100000
        """
        return self.execute_sql_query(baseline_sql)


class TestConstructWithLimit(TestCaseBase):
    """CONSTRUCT 带 LIMIT 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """CONSTRUCT { ?emp a <http://example.org/Employee> }
        WHERE { ?emp <http://example.org/first_name> ?firstName . }
        LIMIT 10"""
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT e.employee_id AS emp
        FROM employees e
        WHERE e.first_name IS NOT NULL
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
        ("CONSTRUCT 基础三元组", TestConstructBasicTriple),
        ("CONSTRUCT 多谓词", TestConstructMultiplePredicates),
        ("CONSTRUCT 带 FILTER", TestConstructWithFilter),
        ("CONSTRUCT 带 LIMIT", TestConstructWithLimit),
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
