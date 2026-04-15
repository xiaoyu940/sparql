#!/usr/bin/env python3
"""
Sprint 9 P0 Property Path 测试 - 反向路径 (^predicate)

测试目标：验证反向路径在OBDA架构下的SQL生成
反向路径 ^p 等价于交换subject/object角色
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestInversePathManager(TestCaseBase):
    """测试反向路径: ?subordinate ^:manager ?manager"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?subordinate ?manager
        WHERE {
          ?subordinate ex:name ?subName .
          ?manager ex:name ?mgrName .
          ?subordinate ^ex:manager ?manager .
        }
        ORDER BY ?subordinate
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P0-1] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 反向路径即交换JOIN条件"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS subordinate, 
            t1.first_name AS manager
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        ORDER BY t0.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


class TestInversePathDepartment(TestCaseBase):
    """测试反向路径跨表: ?emp ^:worksIn ?dept"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?dept
        WHERE {
          ?emp a ex:Employee .
          ?dept a ex:Department .
          ?emp ^ex:worksIn ?dept .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 反向即交换主外键关系"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp, 
            t1.department_id AS dept
        FROM employees t0
        JOIN departments t1 ON t0.department_id = t1.department_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestInversePathSimple(TestCaseBase):
    """测试简单反向路径绑定"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        
        SELECT ?parent ?child
        WHERE {
          ?parent foaf:name "Alice" .
          ?child ^foaf:parent ?parent .
          ?child foaf:name ?childName .
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 反向路径展开为正向交换"""
        baseline_sql = """
        SELECT 
            p.id AS parent,
            c.id AS child,
            c.first_name AS childName
        FROM persons p
        JOIN family_relations fr ON p.id = fr.parent_id
        JOIN persons c ON fr.child_id = c.id
        WHERE p.first_name = 'Alice'
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
        ("S9-P0 Inverse Path - Manager (自连接)", TestInversePathManager),
        ("S9-P0 Inverse Path - Department (跨表)", TestInversePathDepartment),
        ("S9-P0 Inverse Path - Simple", TestInversePathSimple),
    ]
    
    all_passed = True
    
    for name, test_class in tests:
        print(f"\n{'='*80}")
        print(f"测试: {name}")
        print(f"{'='*80}")
        
        test_instance = test_class(db_config)
        result = test_instance.run()
        test_instance.close()
        
        if not result['passed']:
            all_passed = False
    
    print(f"\n{'='*80}")
    print(f"结果: {'全部通过' if all_passed else '有失败'}")
    print(f"{'='*80}")
    
    sys.exit(0 if all_passed else 1)
