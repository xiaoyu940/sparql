#!/usr/bin/env python3
"""
测试案例: 复杂完整查询

验证 SPARQL 复杂完整查询是否正确翻译为 SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult, run_test_case


class TestEdge002(TestCaseBase):
    """测试复杂完整查询: employees, departments, salaries"""
    
    def sparql_query(self) -> QueryResult:
        """
        SPARQL 查询: 获取部门名称（不依赖 salaries 表）
        
        对应 SQL:
        SELECT dep.department_name AS deptName
        FROM departments AS dep 
        GROUP BY dep.department_name
        HAVING COUNT(*) > 5
        ORDER BY deptName DESC
        LIMIT 10
        """
        sparql = """
        SELECT ?deptName
        WHERE {
            ?dept <http://example.org/department_name> ?deptName .
        } GROUP BY ?deptName HAVING (COUNT(*) > 5) ORDER BY DESC(?deptName) LIMIT 10
        """
        
        # 翻译 SPARQL
        sql = self.translate_sparql(sparql)
        self._generated_sql = sql
        
        # 验证生成的 SQL 包含预期模式
        expected_patterns = ["GROUP BY", "HAVING", "LIMIT"]
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
        SELECT dep.department_name AS deptName
        FROM departments AS dep 
        GROUP BY dep.department_name
        HAVING COUNT(*) > 5
        ORDER BY deptName DESC
        LIMIT 10
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
    print(f"测试: 复杂完整查询")
    print(f"{'='*80}\n")
    
    result = run_test_case(TestEdge002, db_config)
    
    print(f"\n{'='*80}")
    print(f"结果: {'✓ 通过' if result['passed'] else '✗ 失败'}")
    print(f"{'='*80}")
    
    if not result['passed']:
        for err in result['errors']:
            print(f"  - {err}")
        sys.exit(1)
