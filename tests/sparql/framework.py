#!/usr/bin/env python3
"""
SPARQL HTTP 测试框架 v1.0
基于 SPARQL 1.1/1.2 协议，结合 HR 业务场景

架构:
- HTTP 端口 5280: SPARQL 查询
- SQL 端口 5432: 基线验证
"""

import requests
import psycopg2
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import sys
import os

# 测试配置
SPARQL_ENDPOINT = "http://localhost:5820/sparql"
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rs_ontop_core',
    'user': 'yuxiaoyu',
    'password': os.environ.get('PGPASSWORD', '123456')
}


@dataclass
class QueryResult:
    """统一查询结果格式"""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    passed: bool = True
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "columns": self.columns,
            "rows": self.rows[:100] if len(self.rows) > 100 else self.rows,  # 限制输出
            "row_count": self.row_count,
            "passed": self.passed,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms
        }


class SparqlExecutor:
    """SPARQL HTTP 执行器"""
    
    def __init__(self, endpoint: str = SPARQL_ENDPOINT):
        self.endpoint = endpoint
        self.headers = {
            'Accept': 'application/sparql-results+json,application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def execute(self, query: str, timeout: int = 30) -> QueryResult:
        """执行 SPARQL 查询"""
        import time
        start_time = time.time()
        
        try:
            data = {'query': query}
            response = requests.post(
                self.endpoint,
                data=data,
                headers=self.headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            result_data = response.json()
            execution_time = (time.time() - start_time) * 1000
            
            # 解析 SPARQL 结果
            if 'results' in result_data:
                # SELECT 查询
                bindings = result_data['results'].get('bindings', [])
                vars_list = result_data['head'].get('vars', [])
                
                rows = []
                for binding in bindings:
                    row = {}
                    for var in vars_list:
                        if var in binding:
                            val = binding[var]
                            # 提取值（处理不同类型）
                            if 'value' in val:
                                row[var] = val['value']
                            else:
                                row[var] = val
                        else:
                            row[var] = None
                    rows.append(row)
                
                return QueryResult(
                    columns=vars_list,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=execution_time
                )
            elif 'boolean' in result_data:
                # ASK 查询
                return QueryResult(
                    columns=['result'],
                    rows=[{'result': result_data['boolean']}],
                    row_count=1,
                    execution_time_ms=execution_time
                )
            else:
                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    error="Unknown response format",
                    passed=False
                )
                
        except requests.exceptions.ConnectionError as e:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"Connection error: {str(e)}. Is the SPARQL endpoint running at {self.endpoint}?",
                passed=False
            )
        except requests.exceptions.Timeout:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"Query timeout after {timeout}s",
                passed=False
            )
        except Exception as e:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"SPARQL execution error: {str(e)}",
                passed=False
            )


class SqlExecutor:
    """SQL 基线执行器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
    
    def execute(self, query: str) -> QueryResult:
        """执行 SQL 查询"""
        import time
        start_time = time.time()
        
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(query)
            
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = []
                for record in cur.fetchall():
                    row = dict(zip(columns, record))
                    rows.append(row)
                
                execution_time = (time.time() - start_time) * 1000
                
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=execution_time
                )
            else:
                # 无结果（如 ASK 查询）
                conn.commit()
                return QueryResult(
                    columns=['result'],
                    rows=[{'result': True}],
                    row_count=1,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return QueryResult(
                columns=[], rows=[], row_count=0,
                error=f"SQL execution error: {str(e)}",
                passed=False
            )
        finally:
            if conn:
                conn.close()


class TestCaseBase(ABC):
    """SPARQL 测试案例基类"""
    
    def __init__(self):
        self.sparql_executor = SparqlExecutor()
        self.sql_executor = SqlExecutor(DB_CONFIG)
        self.name = self.__class__.__name__
        self.description = self.__doc__ or "No description"
    
    @abstractmethod
    def sparql_query(self) -> str:
        """返回 SPARQL 查询字符串"""
        pass
    
    @abstractmethod
    def baseline_sql(self) -> str:
        """返回对应的基线 SQL 查询"""
        pass
    
    def compare_results(self, sparql_result: QueryResult, sql_result: QueryResult) -> Tuple[bool, List[str]]:
        """比较 SPARQL 和 SQL 结果"""
        errors = []
        
        # 检查错误
        if sparql_result.error:
            errors.append(f"SPARQL error: {sparql_result.error}")
            return False, errors
        if sql_result.error:
            errors.append(f"SQL error: {sql_result.error}")
            return False, errors
        
        # 检查行数
        if sparql_result.row_count != sql_result.row_count:
            errors.append(f"Row count mismatch: SPARQL={sparql_result.row_count}, SQL={sql_result.row_count}")
            return False, errors
        
        # 检查数据（简化对比）
        if sparql_result.rows and sql_result.rows:
            # 对比第一行数据
            sparql_row = sparql_result.rows[0]
            sql_row = sql_result.rows[0]
            
            for key in sparql_row.keys():
                if key in sql_row:
                    sparql_val = sparql_row[key]
                    sql_val = sql_row[key]
                    
                    # 类型转换后对比
                    if not self._values_equal(sparql_val, sql_val):
                        errors.append(f"Value mismatch for '{key}': SPARQL='{sparql_val}', SQL='{sql_val}'")
        
        return len(errors) == 0, errors
    
    def _values_equal(self, v1: Any, v2: Any) -> bool:
        """比较两个值是否相等（处理类型差异）"""
        if v1 == v2:
            return True
        
        # 处理字符串/数字转换
        try:
            return float(v1) == float(v2)
        except (ValueError, TypeError):
            pass
        
        # 处理布尔值
        if isinstance(v1, bool) or isinstance(v2, bool):
            return str(v1).lower() == str(v2).lower()
        
        return str(v1) == str(v2)
    
    def run(self) -> Dict[str, Any]:
        """运行测试案例"""
        print(f"\n{'='*80}")
        print(f"测试: {self.name}")
        print(f"描述: {self.description}")
        print(f"{'='*80}")
        
        # 执行 SPARQL
        print("\n[1/3] 执行 SPARQL 查询...")
        sparql = self.sparql_query()
        print(f"SPARQL:\n{sparql[:500]}..." if len(sparql) > 500 else f"SPARQL:\n{sparql}")
        sparql_result = self.sparql_executor.execute(sparql)
        print(f"结果: {sparql_result.row_count} 行, {sparql_result.execution_time_ms:.2f} ms")
        
        # 执行 SQL
        print("\n[2/3] 执行 SQL 基线查询...")
        sql = self.baseline_sql()
        print(f"SQL:\n{sql[:500]}..." if len(sql) > 500 else f"SQL:\n{sql}")
        sql_result = self.sql_executor.execute(sql)
        print(f"结果: {sql_result.row_count} 行, {sql_result.execution_time_ms:.2f} ms")
        
        # 对比结果
        print("\n[3/3] 对比结果...")
        passed, errors = self.compare_results(sparql_result, sql_result)
        
        if passed:
            print("✓ 测试通过")
        else:
            print("✗ 测试失败:")
            for error in errors:
                print(f"  - {error}")
        
        return {
            "name": self.name,
            "description": self.description,
            "passed": passed,
            "errors": errors,
            "sparql_result": sparql_result.to_dict(),
            "sql_result": sql_result.to_dict()
        }


def run_test_suite(test_cases: List[TestCaseBase], output_file: Optional[str] = None):
    """运行测试套件"""
    print("\n" + "="*80)
    print("SPARQL HTTP 测试套件")
    print("="*80)
    
    results = []
    passed_count = 0
    failed_count = 0
    
    for test_case in test_cases:
        result = test_case.run()
        results.append(result)
        
        if result["passed"]:
            passed_count += 1
        else:
            failed_count += 1
    
    # 汇总
    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)
    print(f"总计: {len(test_cases)} 个测试")
    print(f"通过: {passed_count} ✓")
    print(f"失败: {failed_count} ✗")
    print(f"通过率: {passed_count/len(test_cases)*100:.1f}%")
    
    # 保存结果
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n详细结果已保存至: {output_file}")
    
    return results


if __name__ == "__main__":
    print("SPARQL HTTP 测试框架已加载")
    print(f"SPARQL Endpoint: {SPARQL_ENDPOINT}")
    print(f"SQL Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
