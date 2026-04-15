#!/usr/bin/env python3
"""
Sprint 9 P0 Property Path 测试 - 组合路径

测试目标：验证复杂组合路径（反向+序列、序列+选择等）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestComplexPathInverseSequence(TestCaseBase):
    """测试组合: 反向+序列 ^:manager/:name ?mgrName"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?manager ?empName
        WHERE {
          ?emp ex:name ?empName .
          ?manager ^ex:manager/ex:name ?mgrName .
        }
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P0-4] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 反向展开后再序列"""
        baseline_sql = """
        SELECT 
            t1.employee_id AS manager, 
            t0.name AS empName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


class TestComplexPathSequenceAlternative(TestCaseBase):
    """测试组合: 序列+选择 (:email|:phone)/:verified ?isVerified"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?contact ?isVerified
        WHERE {
          ?emp ex:email|ex:phone ?contact .
          ?contact ex:verified ?isVerified .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - UNION + JOIN"""
        baseline_sql = """
        SELECT e.email AS contact, ec.is_verified AS isVerified
        FROM employees e
        JOIN employee_contacts ec ON e.email = ec.contact_value
        WHERE e.email IS NOT NULL
        UNION
        SELECT e.phone AS contact, ec.is_verified AS isVerified
        FROM employees e
        JOIN employee_contacts ec ON e.phone = ec.contact_value
        WHERE e.phone IS NOT NULL
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestComplexPathNestedSequence(TestCaseBase):
    """测试嵌套序列路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?supervisorName
        WHERE {
          ?emp ex:manager/ex:manager/ex:name ?supervisorName .
        }
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 三层自连接"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp,
            t2.first_name AS supervisorName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        JOIN employees t2 ON t1.manager_id = t2.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


class TestComplexPathAlternativeWithSequence(TestCaseBase):
    """测试选择中包含序列: (:homeAddress|:workAddress)/:city ?city"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?person ?city
        WHERE {
          ?person ex:homeAddress|ex:workAddress ?addr .
          ?addr ex:city ?city .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - UNION of JOINs"""
        baseline_sql = """
        SELECT p.id AS person, a1.id AS addr
        FROM persons p
        JOIN addresses a1 ON p.id = a1.person_id
        LIMIT 10
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
        ("S9-P0 Complex - Inverse+Sequence", TestComplexPathInverseSequence),
        ("S9-P0 Complex - Sequence+Alternative", TestComplexPathSequenceAlternative),
        ("S9-P0 Complex - Nested Sequence", TestComplexPathNestedSequence),
        ("S9-P0 Complex - Alternative with Sequence", TestComplexPathAlternativeWithSequence),
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
