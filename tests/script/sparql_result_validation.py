#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RS Ontop Core V2.0 - SPARQL结果正确性验证套件
对比SQL基准结果与SPARQL查询结果，验证数据一致性
"""

import psycopg2
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import statistics

class ResultValidator:
    """结果验证器 - 对比SQL和SPARQL结果"""
    
    def __init__(self, db_config: Dict[str, str], sparql_url: str):
        self.db_config = db_config
        self.sparql_url = sparql_url
        self.conn = None
        self.validation_results = []
        
    def connect_db(self):
        """连接PostgreSQL数据库"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            print("✅ 数据库连接成功")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
    
    def execute_sql(self, sql: str) -> List[Dict]:
        """执行SQL查询并返回结果"""
        if not self.conn:
            if not self.connect_db():
                return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            
            # 获取结果
            rows = cursor.fetchall()
            
            # 转换为字典列表
            results = []
            for row in rows:
                result_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # 处理不同类型的数据
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    elif hasattr(value, 'isoformat'):  # date, time等
                        value = value.isoformat()
                    result_dict[col] = value
                results.append(result_dict)
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"❌ SQL执行错误: {e}")
            return []
    
    def execute_sparql(self, sparql: str, timeout: int = 30) -> Dict:
        """执行SPARQL查询"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {"query": sparql}
            
            response = requests.post(
                self.sparql_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "data": []
                }
            
            result = response.json()
            bindings = result.get("results", {}).get("bindings", [])
            
            # 解析SPARQL结果
            parsed_results = []
            for binding in bindings:
                parsed_row = {}
                for var, value_info in binding.items():
                    value = value_info.get("value")
                    datatype = value_info.get("datatype", "")
                    
                    # 尝试类型转换
                    if datatype and "integer" in datatype:
                        try:
                            value = int(value)
                        except:
                            pass
                    elif datatype and "decimal" in datatype:
                        try:
                            value = float(value)
                        except:
                            pass
                    
                    parsed_row[var] = value
                
                parsed_results.append(parsed_row)
            
            return {
                "status": "success",
                "data": parsed_results,
                "vars": result.get("head", {}).get("vars", [])
            }
            
        except requests.exceptions.Timeout:
            return {"status": "timeout", "error": "请求超时", "data": []}
        except Exception as e:
            return {"status": "error", "error": str(e), "data": []}
    
    def compare_results(self, sql_results: List[Dict], sparql_results: List[Dict], 
                       tolerance: float = 0.01) -> Dict:
        """对比SQL和SPARQL结果"""
        comparison = {
            "sql_count": len(sql_results),
            "sparql_count": len(sparql_results),
            "count_match": len(sql_results) == len(sparql_results),
            "column_match": True,
            "data_match": True,
            "differences": [],
            "details": []
        }
        
        if not sql_results and not sparql_results:
            comparison["status"] = "MATCH"
            comparison["message"] = "两者都返回空结果"
            return comparison
        
        if not comparison["count_match"]:
            comparison["status"] = "MISMATCH"
            comparison["message"] = f"行数不匹配: SQL={len(sql_results)}, SPARQL={len(sparql_results)}"
            return comparison
        
        # 对比每一行数据
        for i, (sql_row, sparql_row) in enumerate(zip(sql_results, sparql_results)):
            row_comparison = {"row_index": i, "matches": True, "fields": []}
            
            # 获取所有列
            all_keys = set(sql_row.keys()) | set(sparql_row.keys())
            
            for key in all_keys:
                sql_val = sql_row.get(key)
                sparql_val = sparql_row.get(key)
                
                field_match = self._values_equal(sql_val, sparql_val, tolerance)
                
                field_info = {
                    "column": key,
                    "sql_value": sql_val,
                    "sparql_value": sparql_val,
                    "match": field_match
                }
                
                if not field_match:
                    row_comparison["matches"] = False
                    comparison["data_match"] = False
                    field_info["difference"] = f"SQL: {sql_val} vs SPARQL: {sparql_val}"
                
                row_comparison["fields"].append(field_info)
            
            comparison["details"].append(row_comparison)
        
        if comparison["count_match"] and comparison["data_match"]:
            comparison["status"] = "MATCH"
            comparison["message"] = "结果完全匹配"
        else:
            comparison["status"] = "MISMATCH"
            comparison["message"] = "数据不匹配"
        
        return comparison
    
    def _values_equal(self, val1, val2, tolerance: float = 0.01) -> bool:
        """比较两个值是否相等（支持数值容差）"""
        if val1 is None and val2 is None:
            return True
        if val1 is None or val2 is None:
            return False
        
        # 数值比较（带容差）
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if isinstance(val1, float) or isinstance(val2, float):
                return abs(float(val1) - float(val2)) <= tolerance
            return val1 == val2
        
        # 字符串比较
        return str(val1) == str(val2)
    
    def run_validation_test(self, test_case: Dict) -> Dict:
        """运行单个验证测试"""
        print(f"\n{'='*70}")
        print(f"[验证测试] {test_case['id']}: {test_case['name']}")
        print(f"描述: {test_case['description']}")
        print(f"{'='*70}")
        
        result = {
            "test_id": test_case['id'],
            "name": test_case['name'],
            "category": test_case['category'],
            "description": test_case['description'],
            "timestamp": datetime.now().isoformat(),
            "sql_execution": {},
            "sparql_execution": {},
            "validation": {},
            "overall_status": "PENDING"
        }
        
        # 执行SQL查询
        print(f"\n📊 执行SQL基准查询...")
        sql_start = time.time()
        sql_results = self.execute_sql(test_case['sql'])
        sql_time = time.time() - sql_start
        
        result["sql_execution"] = {
            "success": len(sql_results) >= 0,  # 空结果也算成功
            "row_count": len(sql_results),
            "execution_time_ms": round(sql_time * 1000, 2),
            "query_preview": test_case['sql'][:100] + "..."
        }
        
        print(f"   SQL结果: {len(sql_results)} 行, 耗时: {sql_time*1000:.2f}ms")
        if sql_results:
            print(f"   预览: {json.dumps(sql_results[0], indent=2, default=str)[:200]}")
        
        # 执行SPARQL查询
        print(f"\n🔗 执行SPARQL查询...")
        sparql_start = time.time()
        sparql_response = self.execute_sparql(test_case['sparql'])
        sparql_time = time.time() - sparql_start
        
        sparql_results = sparql_response.get("data", [])
        
        result["sparql_execution"] = {
            "status": sparql_response.get("status"),
            "error": sparql_response.get("error"),
            "row_count": len(sparql_results),
            "execution_time_ms": round(sparql_time * 1000, 2),
            "query_preview": test_case['sparql'][:100] + "..."
        }
        
        print(f"   SPARQL结果: {len(sparql_results)} 行, 耗时: {sparql_time*1000:.2f}ms")
        if sparql_results:
            print(f"   预览: {json.dumps(sparql_results[0], indent=2, default=str)[:200]}")
        
        # 对比结果
        print(f"\n🔍 对比结果...")
        comparison = self.compare_results(sql_results, sparql_results)
        
        result["validation"] = comparison
        
        # 确定整体状态
        if result["sparql_execution"]["status"] != "success":
            result["overall_status"] = "FAILED"
            print(f"❌ 测试失败: SPARQL执行错误")
        elif comparison["status"] == "MATCH":
            result["overall_status"] = "PASSED"
            print(f"✅ 测试通过: 结果完全匹配")
        else:
            result["overall_status"] = "MISMATCH"
            print(f"⚠️ 结果不匹配: {comparison.get('message', '')}")
        
        print(f"\n   详细对比:")
        print(f"   - SQL行数: {comparison['sql_count']}")
        print(f"   - SPARQL行数: {comparison['sparql_count']}")
        print(f"   - 行数匹配: {'✅' if comparison['count_match'] else '❌'}")
        print(f"   - 数据匹配: {'✅' if comparison['data_match'] else '❌'}")
        
        if not comparison['data_match'] and comparison.get('differences'):
            print(f"   - 差异详情:")
            for diff in comparison['differences'][:5]:  # 只显示前5个差异
                print(f"     行{diff.get('row_index')}: {diff.get('difference', '')}")
        
        return result
    
    def run_all_validations(self, test_cases: List[Dict]):
        """运行所有验证测试"""
        print("="*80)
        print("RS Ontop Core V2.0 - SPARQL结果正确性验证套件")
        print("="*80)
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据库: {self.db_config.get('dbname', 'unknown')}")
        print(f"SPARQL端点: {self.sparql_url}")
        print(f"测试用例数: {len(test_cases)}")
        print("="*80)
        
        # 连接数据库
        if not self.connect_db():
            print("❌ 无法连接数据库，测试中止")
            return []
        
        # 执行所有测试
        self.validation_results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n\n[{i}/{len(test_cases)}] ", end="")
            result = self.run_validation_test(test_case)
            self.validation_results.append(result)
        
        # 生成验证报告
        self.generate_validation_report()
        
        # 关闭数据库连接
        if self.conn:
            self.conn.close()
            print("\n✅ 数据库连接已关闭")
        
        return self.validation_results
    
    def generate_validation_report(self):
        """生成验证报告"""
        print("\n" + "="*80)
        print("验证报告摘要")
        print("="*80)
        
        total = len(self.validation_results)
        passed = sum(1 for r in self.validation_results if r["overall_status"] == "PASSED")
        failed = sum(1 for r in self.validation_results if r["overall_status"] == "FAILED")
        mismatch = sum(1 for r in self.validation_results if r["overall_status"] == "MISMATCH")
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 总体统计:")
        print(f"   总测试数: {total}")
        print(f"   通过: {passed} ✅ (结果完全匹配)")
        print(f"   不匹配: {mismatch} ⚠️ (结果不一致)")
        print(f"   失败: {failed} ❌ (执行错误)")
        print(f"   通过率: {pass_rate:.1f}%")
        
        # 性能统计
        sql_times = [r["sql_execution"]["execution_time_ms"] for r in self.validation_results]
        sparql_times = [r["sparql_execution"]["execution_time_ms"] for r in self.validation_results]
        
        print(f"\n⏱️ 性能对比:")
        print(f"   SQL平均响应时间: {statistics.mean(sql_times):.2f}ms")
        print(f"   SPARQL平均响应时间: {statistics.mean(sparql_times):.2f}ms")
        print(f"   SQL最小响应时间: {min(sql_times):.2f}ms")
        print(f"   SPARQL最小响应时间: {min(sparql_times):.2f}ms")
        print(f"   SQL最大响应时间: {max(sql_times):.2f}ms")
        print(f"   SPARQL最大响应时间: {max(sparql_times):.2f}ms")
        
        # 按类别统计
        print(f"\n📋 按类别统计:")
        categories = {}
        for result in self.validation_results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "mismatch": 0, "failed": 0}
            categories[cat]["total"] += 1
            if result["overall_status"] == "PASSED":
                categories[cat]["passed"] += 1
            elif result["overall_status"] == "MISMATCH":
                categories[cat]["mismatch"] += 1
            else:
                categories[cat]["failed"] += 1
        
        for cat, stats in sorted(categories.items()):
            pass_rate = (stats["passed"] / stats["total"] * 100)
            print(f"   {cat}: {stats['passed']}/{stats['total']} 通过, "
                  f"{stats['mismatch']} 不匹配, {stats['failed']} 失败 "
                  f"({pass_rate:.1f}%)")
        
        # 不匹配详情
        if mismatch > 0:
            print(f"\n⚠️ 结果不匹配的测试:")
            for result in self.validation_results:
                if result["overall_status"] == "MISMATCH":
                    val = result["validation"]
                    print(f"   {result['id']}: {result['name']}")
                    print(f"      SQL: {val['sql_count']}行, SPARQL: {val['sparql_count']}行")
                    print(f"      原因: {val.get('message', '')}")
        
        # 失败详情
        if failed > 0:
            print(f"\n❌ 执行失败的测试:")
            for result in self.validation_results:
                if result["overall_status"] == "FAILED":
                    print(f"   {result['id']}: {result['name']}")
                    print(f"      错误: {result['sparql_execution'].get('error', 'Unknown')}")
        
        print("\n" + "="*80)
        
        # 保存报告
        report_data = {
            "validation_time": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "mismatch": mismatch,
            "failed": failed,
            "pass_rate": pass_rate,
            "performance": {
                "sql_avg_ms": statistics.mean(sql_times),
                "sparql_avg_ms": statistics.mean(sparql_times),
                "sql_min_ms": min(sql_times),
                "sparql_min_ms": min(sparql_times),
                "sql_max_ms": max(sql_times),
                "sparql_max_ms": max(sparql_times)
            },
            "categories": categories,
            "results": self.validation_results
        }
        
        report_file = "/home/yuxiaoyu/rs_ontop_core/sparql_validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 详细验证报告已保存: {report_file}")


# ==================== 验证测试用例定义 ====================

VALIDATION_TEST_CASES = [
    {
        "id": "VAL_001",
        "name": "员工总数验证",
        "category": "数据一致性",
        "description": "验证SQL和SPARQL查询的员工总数是否一致",
        "sql": "SELECT COUNT(*) as total_count FROM employees",
        "sparql": """SELECT (COUNT(*) AS ?total_count)
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                     }"""
    },
    
    {
        "id": "VAL_002",
        "name": "部门统计验证",
        "category": "聚合验证",
        "description": "验证部门员工数量统计的一致性",
        "sql": """SELECT d.department_name, COUNT(e.employee_id) as emp_count
                  FROM departments d
                  LEFT JOIN employees e ON d.department_id = e.department_id
                  GROUP BY d.department_name
                  ORDER BY emp_count DESC
                  LIMIT 10""",
        "sparql": """SELECT ?department_name (COUNT(?employee) AS ?emp_count)
                     WHERE { 
                         ?employee <http://example.org/department_id> ?dept .
                         ?dept <http://example.org/department_name> ?department_name .
                     }
                     GROUP BY ?department_name
                     ORDER BY DESC(?emp_count)
                     LIMIT 10"""
    },
    
    {
        "id": "VAL_003",
        "name": "薪资范围验证",
        "category": "数值验证",
        "description": "验证薪资统计值的一致性",
        "sql": """SELECT MIN(salary) as min_sal, MAX(salary) as max_sal, 
                         AVG(salary) as avg_sal, SUM(salary) as total_sal
                  FROM employees""",
        "sparql": """SELECT (MIN(?salary) AS ?min_sal) (MAX(?salary) AS ?max_sal)
                            (AVG(?salary) AS ?avg_sal) (SUM(?salary) AS ?total_sal)
                     WHERE { 
                         ?employee <http://example.org/salary> ?salary .
                     }"""
    },
    
    {
        "id": "VAL_004",
        "name": "员工基本信息验证",
        "category": "字段验证",
        "description": "验证员工基本信息的完整性和一致性",
        "sql": """SELECT employee_id, first_name, last_name, email, salary, status
                  FROM employees
                  WHERE employee_id <= 10
                  ORDER BY employee_id""",
        "sparql": """SELECT ?employee_id ?first_name ?last_name ?email ?salary ?status
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/email> ?email .
                         ?employee <http://example.org/salary> ?salary .
                         ?employee <http://example.org/status> ?status .
                         FILTER(?employee_id <= 10)
                     }
                     ORDER BY ?employee_id"""
    },
    
    {
        "id": "VAL_005",
        "name": "高薪资员工验证",
        "category": "条件过滤验证",
        "description": "验证FILTER条件的一致性",
        "sql": """SELECT e.employee_id, e.first_name, e.last_name, e.salary,
                         d.department_name
                  FROM employees e
                  JOIN departments d ON e.department_id = d.department_id
                  WHERE e.salary > 100000
                  ORDER BY e.salary DESC
                  LIMIT 20""",
        "sparql": """SELECT ?employee_id ?first_name ?last_name ?salary ?department_name
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/salary> ?salary .
                         ?employee <http://example.org/department_id> ?dept .
                         ?dept <http://example.org/department_name> ?department_name .
                         FILTER(?salary > 100000)
                     }
                     ORDER BY DESC(?salary)
                     LIMIT 20"""
    },
    
    {
        "id": "VAL_006",
        "name": "薪资记录验证",
        "category": "关联表验证",
        "description": "验证员工薪资记录的关联查询一致性",
        "sql": """SELECT e.employee_id, e.first_name, s.base_salary, s.bonus, s.net_salary
                  FROM employees e
                  JOIN salaries s ON e.employee_id = s.employee_id
                  WHERE e.employee_id <= 20
                  ORDER BY e.employee_id""",
        "sparql": """SELECT ?employee_id ?first_name ?base_salary ?bonus ?net_salary
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?salary <http://example.org/employee_id> ?employee_id .
                         ?salary <http://example.org/base_salary> ?base_salary .
                         ?salary <http://example.org/bonus> ?bonus .
                         ?salary <http://example.org/net_salary> ?net_salary .
                         FILTER(?employee_id <= 20)
                     }
                     ORDER BY ?employee_id"""
    },
    
    {
        "id": "VAL_007",
        "name": "项目统计验证",
        "category": "复杂关联验证",
        "description": "验证项目参与度统计的一致性",
        "sql": """SELECT p.project_name, COUNT(DISTINCT ep.employee_id) as team_size,
                         SUM(ep.hours_worked) as total_hours
                  FROM projects p
                  JOIN employee_projects ep ON p.project_id = ep.project_id
                  GROUP BY p.project_name
                  ORDER BY team_size DESC
                  LIMIT 10""",
        "sparql": """SELECT ?project_name (COUNT(DISTINCT ?employee_id) AS ?team_size)
                                    (SUM(?hours_worked) AS ?total_hours)
                     WHERE { 
                         ?project <http://example.org/project_name> ?project_name .
                         ?emp_proj <http://example.org/project_id> ?project .
                         ?emp_proj <http://example.org/employee_id> ?employee_id .
                         ?emp_proj <http://example.org/hours_worked> ?hours_worked .
                     }
                     GROUP BY ?project_name
                     ORDER BY DESC(?team_size)
                     LIMIT 10"""
    },
    
    {
        "id": "VAL_008",
        "name": "考勤统计验证",
        "category": "时间序列验证",
        "description": "验证考勤数据统计的一致性",
        "sql": """SELECT e.employee_id, e.first_name,
                         COUNT(a.attendance_id) as work_days,
                         SUM(a.work_hours) as total_hours,
                         SUM(a.overtime_hours) as total_overtime
                  FROM employees e
                  JOIN attendance a ON e.employee_id = a.employee_id
                  WHERE e.employee_id <= 20
                  GROUP BY e.employee_id, e.first_name
                  ORDER BY e.employee_id""",
        "sparql": """SELECT ?employee_id ?first_name (COUNT(?attendance) AS ?work_days)
                                    (SUM(?work_hours) AS ?total_hours)
                                    (SUM(?overtime_hours) AS ?total_overtime)
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?attendance <http://example.org/employee_id> ?employee_id .
                         ?attendance <http://example.org/work_hours> ?work_hours .
                         ?attendance <http://example.org/overtime_hours> ?overtime_hours .
                         FILTER(?employee_id <= 20)
                     }
                     GROUP BY ?employee_id ?first_name
                     ORDER BY ?employee_id"""
    }
]


def main():
    """主函数"""
    # 数据库配置
    db_config = {
        "dbname": "rs_ontop_core",
        "user": "yuxiaoyu",
        "password": "",
        "host": "localhost",
        "port": "5432"
    }
    
    # SPARQL端点
    sparql_url = "http://localhost:5820/sparql"
    
    # 创建验证器
    validator = ResultValidator(db_config, sparql_url)
    
    # 运行所有验证测试
    validator.run_all_validations(VALIDATION_TEST_CASES)


if __name__ == "__main__":
    main()
