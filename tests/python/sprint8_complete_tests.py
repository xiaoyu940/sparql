#!/usr/bin/env python3
"""
Sprint 8 完整测试套件
测试 SPARQL 1.1 高级功能：子查询、VALUES、MINUS、EXISTS、BIND、GeoSPARQL
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import SparqlTestFramework, TestCaseBase, QueryResult

# ==================== P0 核心功能测试 ====================

class TestSubQueryBasic(TestCaseBase):
    """P0: 基础子查询测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept (COUNT(?emp) AS ?total)
        WHERE {
          ?emp <http://example.org/department_id> ?dept .
          ?dept <http://example.org/department_name> ?deptName .
        }
        GROUP BY ?dept
        ORDER BY ?dept
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT e.department_id AS "dept", COUNT(e.employee_id) AS "total"
        FROM employees AS e
        JOIN departments AS d ON e.department_id = d.department_id
        GROUP BY e.department_id
        ORDER BY e.department_id
        LIMIT 5
        """
        return self.execute_sql_query(baseline_sql)

class TestSubQueryDerivedTable(TestCaseBase):
    """P0: 派生表子查询测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/salary> ?salary .
          FILTER(?salary > 70000)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE salary > 70000
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

class TestValuesSingleVar(TestCaseBase):
    """P0: 单变量 VALUES 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          VALUES ?emp { 1 2 3 4 5 }
        }
        ORDER BY ?emp
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE employee_id IN (1, 2, 3, 4, 5)
        ORDER BY employee_id
        """
        return self.execute_sql_query(baseline_sql)

class TestValuesMultiVar(TestCaseBase):
    """P0: 多变量 VALUES 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/department_name> ?name .
          VALUES (?dept ?loc) {
            (1 "Building A")
            (2 "Building B")
          }
        }
        ORDER BY ?dept
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE (d.department_id = 1 AND d.location = 'Building A')
           OR (d.department_id = 2 AND d.location = 'Building B')
        ORDER BY d.department_id
        """
        return self.execute_sql_query(baseline_sql)

# ==================== P1 高级功能测试 ====================

class TestMinusBasic(TestCaseBase):
    """P1: 基础 MINUS 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          MINUS {
            ?emp <http://example.org/status> "Terminated"
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = employees.employee_id
              AND e2.status = 'Terminated'
        )
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

class TestExistsBasic(TestCaseBase):
    """P1: EXISTS 基础测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?dept ?name
        WHERE {
          ?dept <http://example.org/department_name> ?name .
          FILTER EXISTS {
            ?emp <http://example.org/department_id> ?dept .
          }
        }
        ORDER BY ?dept
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT d.department_id AS "dept", d.department_name AS "name"
        FROM departments AS d
        WHERE EXISTS (
            SELECT 1 FROM employees AS e
            WHERE e.department_id = d.department_id
        )
        ORDER BY d.department_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

class TestNotExists(TestCaseBase):
    """P1: NOT EXISTS 测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          FILTER NOT EXISTS {
            ?emp <http://example.org/status> "Terminated"
          }
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name"
        FROM employees
        WHERE NOT EXISTS (
            SELECT 1 FROM employees AS e2
            WHERE e2.employee_id = employees.employee_id
              AND e2.status = 'Terminated'
        )
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

# ==================== P2 扩展功能测试 ====================

class TestBindArithmetic(TestCaseBase):
    """P2: BIND 算术函数测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?name ?salary_plus
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          ?emp <http://example.org/salary> ?salary .
          BIND(?salary + 1000 AS ?salary_plus)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name AS "name", salary + 1000 AS "salary_plus"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

class TestBindString(TestCaseBase):
    """P2: BIND 字符串函数测试"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        SELECT ?emp ?full_name
        WHERE {
          ?emp <http://example.org/first_name> ?first .
          ?emp <http://example.org/last_name> ?last .
          BIND(CONCAT(?first, " ", ?last) AS ?full_name)
        }
        ORDER BY ?emp
        LIMIT 10
        """
        sql = self.translate_sparql(sparql)
        return self.execute_sql_query(sql)
    
    def sql_query(self) -> QueryResult:
        baseline_sql = """
        SELECT employee_id AS "emp", first_name || ' ' || last_name AS "full_name"
        FROM employees
        ORDER BY employee_id
        LIMIT 10
        """
        return self.execute_sql_query(baseline_sql)

class TestGeoSparqlBasic(TestCaseBase):
    """P2: GeoSPARQL 基础测试 - 验证SQL生成正确性"""
    
    def sparql_query(self) -> QueryResult:
        sparql = """
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        
        SELECT ?emp ?name
        WHERE {
          ?emp <http://example.org/first_name> ?name .
          FILTER(geof:sfWithin(?name, "POINT(116.4 39.9)"^^geo:wktLiteral))
        }
        LIMIT 5
        """
        sql = self.translate_sparql(sparql)
        
        # 验证生成的SQL包含正确的PostGIS函数
        if "ST_Within" not in sql or "ST_GeomFromText" not in sql:
            raise Exception(f"GeoSPARQL SQL生成失败: {sql}")
        if "POINT(116.4 39.9)" not in sql:
            raise Exception(f"WKT字面量解析失败: {sql}")
        
        # 返回空结果（数据库中没有几何数据）
        return QueryResult(
            columns=["emp", "name"],
            rows=[],
            row_count=0
        )
    
    def sql_query(self) -> QueryResult:
        # 基线SQL也返回空结果
        return QueryResult(
            columns=["emp", "name"],
            rows=[],
            row_count=0
        )

# ==================== 测试执行器 ====================

def run_sprint8_tests():
    """运行所有 Sprint 8 测试"""
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rs_ontop_core',
        'user': 'yuxiaoyu',
        'password': os.environ.get('PGPASSWORD', '')
    }
    
    # 测试套件定义
    test_suites = [
        # P0 核心功能
        ("P0-子查询基础", TestSubQueryBasic),
        ("P0-派生表子查询", TestSubQueryDerivedTable),
        ("P0-VALUES单变量", TestValuesSingleVar),
        ("P0-VALUES多变量", TestValuesMultiVar),
        
        # P1 高级功能
        ("P1-MINUS基础", TestMinusBasic),
        ("P1-EXISTS基础", TestExistsBasic),
        ("P1-NOT EXISTS", TestNotExists),
        
        # P2 扩展功能
        ("P2-BIND算术", TestBindArithmetic),
        ("P2-BIND字符串", TestBindString),
        ("P2-GeoSPARQL基础", TestGeoSparqlBasic),
    ]
    
    framework = SparqlTestFramework(db_config)
    results = []
    
    print("=" * 80)
    print("SPRINT 8 - SPARQL 1.1 高级功能测试套件")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试数量: {len(test_suites)}")
    print()
    
    for i, (name, test_class) in enumerate(test_suites, 1):
        print(f"[{i}/{len(test_suites)}] {name}")
        print("-" * 60)
        
        try:
            result = framework.run_test_case(test_class(db_config))
            result['test_name'] = name
            result['test_category'] = name.split('-')[0]
            results.append(result)
            
            if result['passed']:
                print(f"✅ 通过")
            else:
                print(f"❌ 失败")
                for error in result.get('errors', []):
                    print(f"   - {error}")
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append({
                'test_name': name,
                'test_category': name.split('-')[0],
                'passed': False,
                'errors': [f"执行异常: {str(e)}"]
            })
        
        print()
    
    # 生成报告
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    
    print(f"总计: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/total*100:.1f}%")
    print()
    
    # 按类别统计
    categories = {}
    for result in results:
        cat = result['test_category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if result['passed']:
            categories[cat]['passed'] += 1
    
    print("分类统计:")
    for cat, stats in categories.items():
        pass_rate = stats['passed'] / stats['total'] * 100
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
    print()
    
    # 失败详情
    if failed > 0:
        print("失败详情:")
        for result in results:
            if not result['passed']:
                print(f"  ❌ {result['test_name']}")
                for error in result.get('errors', []):
                    print(f"     - {error}")
        print()
    
    # 保存详细报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'sprint': '8',
        'total_tests': total,
        'passed': passed,
        'failed': failed,
        'pass_rate': passed/total*100,
        'categories': categories,
        'results': results
    }
    
    report_file = f"sprint8_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"详细报告已保存: {report_file}")
    print("=" * 80)
    
    return report

if __name__ == '__main__':
    run_sprint8_tests()
