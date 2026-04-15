#!/usr/bin/env python3
"""
Sprint 9 P0 Property Path 测试 - 序列路径 (p1/p2)

测试目标：验证序列路径在OBDA架构下的多表JOIN生成
序列路径 p1/p2 展开为多表JOIN链
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult


class TestSequencePathManagerName(TestCaseBase):
    """测试序列路径: ?emp :manager/:name ?mgrName (自连接序列)"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?mgrName
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:manager/ex:name ?mgrName .
        }
        ORDER BY ?emp
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        print(f"[S9-P0-2] 生成 SQL: {sql}")
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 自连接获取经理姓名"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp, 
            t1.name AS mgrName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        ORDER BY t0.employee_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)


class TestSequencePathMultiTable(TestCaseBase):
    """测试跨表序列: ?emp :worksIn/:locatedIn/:country ?country"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?country
        WHERE {
          ?emp a ex:Employee .
          ?emp ex:worksIn/ex:locatedIn/ex:country ?country .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 三表 JOIN 链"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp, 
            t2.name AS country
        FROM employees t0
        JOIN departments t1 ON t0.department_id = t1.department_id
        JOIN locations t2 ON t1.location_id = t2.id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)


class TestSequencePathWithFilter(TestCaseBase):
    """测试带 FILTER 的序列路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?mgrName
        WHERE {
          ?emp ex:manager/ex:name ?mgrName .
          FILTER(CONTAINS(?mgrName, "Smith"))
        }
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 自连接 + 字符串过滤"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp, 
            t1.first_name AS mgrName
        FROM employees t0
        JOIN employees t1 ON t0.manager_id = t1.employee_id
        WHERE t1.first_name LIKE '%Smith%'
        """
        return self.execute_sql_query(baseline_sql)


class TestSequencePathFourStep(TestCaseBase):
    """测试四步序列路径"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX ex: <http://example.org/>
        
        SELECT ?emp ?region
        WHERE {
          ?emp ex:department/ex:location/ex:city/ex:region ?region .
        }
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """基准 SQL - 四表 JOIN 链"""
        baseline_sql = """
        SELECT 
            t0.employee_id AS emp,
            t3.city_name AS region
        FROM employees t0
        JOIN departments t1 ON t0.department_id = t1.department_id
        JOIN locations t2 ON t1.location_id = t2.id
        JOIN cities t3 ON t2.city = t3.city_name
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
        ("S9-P0 Sequence Path - Manager/Name (自连接)", TestSequencePathManagerName),
        ("S9-P0 Sequence Path - WorksIn/LocatedIn/Country (跨表)", TestSequencePathMultiTable),
        ("S9-P0 Sequence Path - With Filter", TestSequencePathWithFilter),
        ("S9-P0 Sequence Path - Four Steps", TestSequencePathFourStep),
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
