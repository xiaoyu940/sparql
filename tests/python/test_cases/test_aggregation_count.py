#!/usr/bin/env python3
"""
测试案例: 聚合查询 (COUNT)

验证 SPARQL 聚合函数是否正确翻译为 SQL COUNT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestAggregationCount(TestCaseBase):
    """测试 COUNT 聚合"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 按部门统计员工数量
        """
        sparql = """
        SELECT ?deptName (COUNT(?emp) AS ?empCount)
        WHERE {
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
        }
        GROUP BY ?deptName
        """
        
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        基准 SQL
        """
        baseline_sql = """
        SELECT d.department_name AS deptname, COUNT(e.employee_id) AS empcount
        FROM departments d
        JOIN employees e ON e.department_id = d.department_id
        GROUP BY d.department_name
        """
        
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
    print(f"测试: 聚合查询 (COUNT)")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestAggregationCount, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
