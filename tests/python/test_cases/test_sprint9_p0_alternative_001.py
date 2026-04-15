#!/usr/bin/env python3
"""
Sprint 9 P0 Property Path 测试 - 选择路径 (p1|p2)

测试目标：验证选择路径在OBDA架构下的UNION生成
选择路径 p1|p2 展开为 SQL UNION
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestAlternativePathEmailPhone(TestCaseBase):
    """测试选择路径: ?emp :email|:phone ?contact"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?contact
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:email|ex:phone ?contact .
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P0-3] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - UNION 合并 email 和 phone"""
        baseline_sql = """
        SELECT employee_id AS emp, email AS contact
        FROM employees
        WHERE email IS NOT NULL
        UNION
        SELECT employee_id AS emp, phone AS contact
        FROM employees
        WHERE phone IS NOT NULL
        ORDER BY emp
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestAlternativePathMultiPredicate(TestCaseBase):
    """测试多谓词选择: ?emp :firstName|:lastName|:middleName ?namePart"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?namePart
        WHERE {
          ?emp ex:firstName|ex:lastName|ex:middleName ?namePart .
        }
        LIMIT 15
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 三分支 UNION"""
        baseline_sql = """
        SELECT employee_id AS emp, first_name AS namePart FROM employees
        UNION
        SELECT employee_id AS emp, last_name AS namePart FROM employees
        UNION
        SELECT employee_id AS emp, middle_name AS namePart FROM employees
        LIMIT 15
        """
        return self.execute_sql_query(baseline_sql)


class TestAlternativePathWithCommonSubject(TestCaseBase):
    """测试带共同subject约束的选择路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?contact
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:name ?name .
          ?emp ex:email|ex:phone ?contact .
          FILTER(?name = "Alice")
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - UNION + WHERE条件"""
        baseline_sql = """
        SELECT employee_id AS emp, email AS contact, first_name AS name
        FROM employees
        WHERE first_name = 'Alice' AND email IS NOT NULL
        UNION
        SELECT employee_id AS emp, phone AS contact, first_name AS name
        FROM employees
        WHERE first_name = 'Alice' AND phone IS NOT NULL
        """
        return self.execute_sql_query(baseline_sql)


class TestAlternativePathCrossTable(TestCaseBase):
    """测试跨表选择路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?person ?identifier
        WHERE {
          ?person a ex:Person .
          ?person ex:ssn|ex:employeeId|ex:passport ?identifier .
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 不同表列的UNION"""
        baseline_sql = """
        SELECT person_id AS person, id AS identifier FROM persons WHERE id IS NOT NULL
        UNION
        SELECT employee_id AS person, employee_id AS identifier FROM employees WHERE employee_id IS NOT NULL
        UNION  
        SELECT person_id AS person, email AS identifier FROM persons WHERE email IS NOT NULL
        """
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': os.environ.get('PGUSER', 'yuxiaoyu'),
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    tests = [
        ("S9-P0 Alternative Path - Email|Phone", TestAlternativePathEmailPhone),
        ("S9-P0 Alternative Path - Multi Names", TestAlternativePathMultiPredicate),
        ("S9-P0 Alternative Path - With Common Subject", TestAlternativePathWithCommonSubject),
        ("S9-P0 Alternative Path - Cross Table", TestAlternativePathCrossTable),
    ]
    
    framework = SparqlTestFramework(db_config)
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        result = framework.run_test_case(test_class(db_config))
        if not result['passed']:
            all_passed = False
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
