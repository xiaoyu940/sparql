#!/usr/bin/env python3
"""
调试脚本: TestAskWithJoin 问题分析
检查实际生成的SQL与基线SQL的差异
"""

import sys
import os
sys.path.insert(0, '/home/yuxiaoyu/rs_ontop_core/tests/python')

from framework import TestCaseBase, QueryResult

class DebugAskWithJoin(TestCaseBase):
    """调试ASK带JOIN测试"""
    
    def test_debug(self):
        """调试并打印生成的SQL"""
        sparql = """ASK { 
            ?emp <http://example.org/department_id> ?dept .
            ?dept <http://example.org/department_name> "Engineering" .
        }"""
        
        print("=" * 80)
        print("SPARQL 查询:")
        print(sparql)
        print("=" * 80)
        
        # 生成SQL
        try:
            generated_sql = self.translate_sparql(sparql)
            print("\n生成的 SQL:")
            print(generated_sql)
        except Exception as e:
            print(f"\n翻译错误: {e}")
            return
        
        print("\n" + "=" * 80)
        print("基线 SQL (预期):")
        baseline_sql = """
        SELECT EXISTS(
            SELECT 1 FROM employees e
            JOIN departments d ON e.department_id = d.department_id
            WHERE d.department_name = 'Engineering'
        ) AS result
        """
        print(baseline_sql)
        print("=" * 80)
        
        # 执行并对比结果
        print("\n执行生成的 SQL...")
        try:
            result1 = self.execute_sql_query(generated_sql)
            print(f"生成的 SQL 结果: {result1.rows}")
        except Exception as e:
            print(f"生成的 SQL 执行错误: {e}")
        
        print("\n执行基线 SQL...")
        try:
            result2 = self.execute_sql_query(baseline_sql)
            print(f"基线 SQL 结果: {result2.rows}")
        except Exception as e:
            print(f"基线 SQL 执行错误: {e}")

if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '123456')
    }
    
    test = DebugAskWithJoin(db_config)
    test.test_debug()
