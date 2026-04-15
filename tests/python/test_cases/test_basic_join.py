#!/usr/bin/env python3
"""
测试案例: 基础 JOIN 查询

验证 SPARQL 两表 JOIN 是否正确翻译为 SQL INNER JOIN
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestBasicJoin(TestCaseBase):
    """测试基础 JOIN: employees 和 departments"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 通过 SQL 函数 ontop_query 执行（跳过 HTTP 5820）
        
        对应 SQL:
        SELECT e.first_name, d.department_name
        FROM employees e
        JOIN departments d ON e.department_id = d.id
        LIMIT 5
        """
        sparql = """
        SELECT ?firstName ?deptName
        WHERE {
            ?emp <http://example.org/first_name> ?firstName .
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
        }
        LIMIT 5
        """
        
        # 通过 SQL 函数 ontop_query 执行 SPARQL（跳过 HTTP 服务）
        return self.execute_sparql_sql(sparql)
    
    def sql_query(self) -> QueryResult:
        """
        对应的 SQL 查询（作为基准）
        注意：这里直接使用预定义的 SQL，不依赖翻译
        """
        # 基准 SQL - 这是我们认为正确的查询
        baseline_sql = """
        SELECT e.first_name AS firstname, d.department_name AS deptname
        FROM employees e
        INNER JOIN departments d ON e.department_id = d.department_id
        LIMIT 5
        """
        
        # 如果 sparql_query 已经生成了 SQL，我们可以对比
        # 但为了独立验证，这里使用基准 SQL
        return self.execute_sql_query(baseline_sql)


if __name__ == '__main__':
    import json
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    print(f"\n{'='*80}")
    print(f"测试: 基础 JOIN 查询")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestBasicJoin, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
