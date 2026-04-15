#!/usr/bin/env python3
"""调试 ASK 查询"""

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
        
        sql = self.translate_sparql(sparql)
        print(f"生成的 SQL: {sql}")
        
        result = self.execute_sql_query(sql)
        print(f"返回行数: {result.row_count}")
        print(f"返回列: {result.columns}")
        print(f"返回数据: {result.rows}")
        
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
    
    # 调试存在的属性
    test.debug_query("ASK 存在属性", """ASK { 
        ?emp <http://example.org/first_name> ?firstName .
    }""")
    
    test.close()
