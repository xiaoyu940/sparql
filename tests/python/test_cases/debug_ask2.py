#!/usr/bin/env python3
"""调试 ASK 查询 - 详细版"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TestCaseBase, QueryResult

class TestAskDebug(TestCaseBase):
    def sparql_query(self) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0)
    
    def sql_query(self) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0)
    
    def debug_query(self, name, sparql):
        print(f"\n{'='*80}")
        print(f"调试: {name}")
        print(f"{'='*80}")
        print(f"SPARQL: {sparql}")
        
        # 获取翻译的 SQL
        sql = self.translate_sparql(sparql)
        print(f"\n生成的 SQL: {sql}")
        
        # 直接执行 SQL 看结果
        result = self.execute_sql_query(sql)
        print(f"\n直接执行结果:")
        print(f"  行数: {result.row_count}")
        print(f"  列: {result.columns}")
        print(f"  数据: {result.rows}")
        
        # 对于 ASK 查询，还需要看包装后的 EXISTS 结果
        if 'ASK' in sparql.upper():
            ask_sql = f"SELECT EXISTS({sql}) AS result"
            print(f"\nASK 包装 SQL: {ask_sql}")
            ask_result = self.execute_sql_query(ask_sql)
            print(f"ASK 结果:")
            print(f"  行数: {ask_result.row_count}")
            print(f"  列: {ask_result.columns}")
            print(f"  数据: {ask_result.rows}")
        
        return result

if __name__ == '__main__':
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    test = TestAskDebug(db_config)
    
    # 调试不存在的属性
    test.debug_query("ASK 不存在属性", """ASK { 
        ?emp <http://example.org/nonexistent_property> ?value .
    }""")
    
    test.close()
