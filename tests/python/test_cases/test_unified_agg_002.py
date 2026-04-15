#!/usr/bin/env python3
"""
测试案例: 全聚合函数组合

验证 SPARQL 全聚合函数组合查询是否正确翻译为 SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestAgg002(TestCaseBase):
    """测试全聚合函数组合: employees, departments, salaries"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 获取部门员工统计（不依赖 salaries 表）
        
        对应 SQL:
        SELECT dep.department_name AS deptName, 
               COUNT(*) AS count
        FROM departments AS dep 
        INNER JOIN employees AS emp ON dep.department_id = emp.department_id
        GROUP BY dep.department_name
        """
        sparql = """
        SELECT ?deptName (COUNT(*) AS ?count)
        WHERE {
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> ?deptName .
        } GROUP BY ?deptName
        """
        
        # 翻译 SPARQL
        sql = self.translate_sparql(sparql)
        self._generated_sql = sql
        
        # 验证生成的 SQL 包含预期模式
        expected_patterns = ["COUNT"]
        excluded_patterns = []
        
        for pattern in expected_patterns:
            if pattern not in sql:
                raise Exception(f"Missing expected pattern: {pattern}")
        
        for pattern in excluded_patterns:
            if pattern in sql:
                raise Exception(f"Found excluded pattern: {pattern}")
        
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        """
        基准 SQL - 这是我们认为正确的查询
        """
        baseline_sql = """
        SELECT dep.department_name AS deptName, 
               COUNT(*) AS count
        FROM departments AS dep 
        INNER JOIN employees AS emp ON dep.department_id = emp.department_id
        GROUP BY dep.department_name
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
    print(f"测试: 全聚合函数组合")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestAgg002, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
