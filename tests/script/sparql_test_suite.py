#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RS Ontop Core V2.0 - Comprehensive SPARQL Test Suite
通过5820端口测试SPARQL端点
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5820"
SPARQL_ENDPOINT = f"{BASE_URL}/sparql"

# 测试用例定义
TEST_CASES = [
    # ===== 基本查询测试 =====
    {
        "id": "BASIC_001",
        "name": "查询所有员工基本信息",
        "category": "Basic Query",
        "sparql": """SELECT ?employee_id ?first_name ?last_name ?email 
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/email> ?email .
                     }
                     LIMIT 10""",
        "expected_vars": ["employee_id", "first_name", "last_name", "email"],
        "expected_row_count": 10,
        "description": "测试基本的SELECT查询，获取员工基本信息"
    },
    
    {
        "id": "BASIC_002",
        "name": "查询特定部门员工",
        "category": "Basic Query",
        "sparql": """SELECT ?employee_id ?first_name ?last_name ?department_name
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/department_id> ?dept .
                         ?dept <http://example.org/department_name> ?department_name .
                         FILTER(?department_name = "Department_1")
                     }
                     LIMIT 5""",
        "expected_vars": ["employee_id", "first_name", "last_name", "department_name"],
        "expected_row_count_range": [1, 1000],
        "description": "测试FILTER条件和JOIN查询"
    },
    
    {
        "id": "BASIC_003",
        "name": "查询员工薪资信息",
        "category": "Basic Query",
        "sparql": """SELECT ?first_name ?last_name ?base_salary ?bonus ?net_salary
                     WHERE { 
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/employee_id> ?emp_id .
                         ?salary <http://example.org/employee_id> ?emp_id .
                         ?salary <http://example.org/base_salary> ?base_salary .
                         ?salary <http://example.org/bonus> ?bonus .
                         ?salary <http://example.org/net_salary> ?net_salary .
                     }
                     LIMIT 5""",
        "expected_vars": ["first_name", "last_name", "base_salary", "bonus", "net_salary"],
        "expected_row_count_range": [1, 1000],
        "description": "测试员工和薪资表的JOIN查询"
    },
    
    # ===== 聚合查询测试 =====
    {
        "id": "AGG_001",
        "name": "统计员工总数",
        "category": "Aggregation",
        "sparql": """SELECT (COUNT(?employee) AS ?total_count)
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                     }""",
        "expected_vars": ["total_count"],
        "expected_row_count": 1,
        "expected_value_range": {"total_count": [100000, 100000]},
        "description": "测试COUNT聚合函数"
    },
    
    {
        "id": "AGG_002",
        "name": "按部门统计员工数量",
        "category": "Aggregation",
        "sparql": """SELECT ?department_name (COUNT(?employee) AS ?employee_count)
                     WHERE { 
                         ?employee <http://example.org/department_id> ?dept .
                         ?dept <http://example.org/department_name> ?department_name .
                     }
                     GROUP BY ?department_name
                     ORDER BY DESC(?employee_count)
                     LIMIT 10""",
        "expected_vars": ["department_name", "employee_count"],
        "expected_row_count_range": [1, 100],
        "description": "测试GROUP BY和ORDER BY聚合查询"
    },
    
    {
        "id": "AGG_003",
        "name": "计算平均薪资",
        "category": "Aggregation",
        "sparql": """SELECT (AVG(?net_salary) AS ?avg_salary) 
                            (MIN(?net_salary) AS ?min_salary)
                            (MAX(?net_salary) AS ?max_salary)
                     WHERE { 
                         ?salary <http://example.org/net_salary> ?net_salary .
                     }""",
        "expected_vars": ["avg_salary", "min_salary", "max_salary"],
        "expected_row_count": 1,
        "description": "测试AVG、MIN、MAX聚合函数"
    },
    
    {
        "id": "AGG_004",
        "name": "部门薪资总和统计",
        "category": "Aggregation",
        "sparql": """SELECT ?department_name (SUM(?net_salary) AS ?total_salary)
                     WHERE { 
                         ?employee <http://example.org/department_id> ?dept .
                         ?employee <http://example.org/employee_id> ?emp_id .
                         ?dept <http://example.org/department_name> ?department_name .
                         ?salary <http://example.org/employee_id> ?emp_id .
                         ?salary <http://example.org/net_salary> ?net_salary .
                     }
                     GROUP BY ?department_name
                     ORDER BY DESC(?total_salary)
                     LIMIT 5""",
        "expected_vars": ["department_name", "total_salary"],
        "expected_row_count_range": [1, 100],
        "description": "测试SUM聚合和多表JOIN"
    },
    
    # ===== 复杂查询测试 =====
    {
        "id": "COMPLEX_001",
        "name": "查询员工项目参与度",
        "category": "Complex Query",
        "sparql": """SELECT ?first_name ?last_name (COUNT(?project) AS ?project_count)
                     WHERE { 
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/employee_id> ?emp_id .
                         ?emp_project <http://example.org/employee_id> ?emp_id .
                         ?emp_project <http://example.org/project_id> ?project .
                     }
                     GROUP BY ?first_name ?last_name
                     HAVING (COUNT(?project) > 0)
                     ORDER BY DESC(?project_count)
                     LIMIT 5""",
        "expected_vars": ["first_name", "last_name", "project_count"],
        "expected_row_count_range": [1, 100],
        "description": "测试多表JOIN、GROUP BY和HAVING"
    },
    
    {
        "id": "COMPLEX_002",
        "name": "查询高薪资员工详细信息",
        "category": "Complex Query",
        "sparql": """SELECT ?first_name ?last_name ?department_name ?position_title ?net_salary
                     WHERE { 
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/employee_id> ?emp_id .
                         ?employee <http://example.org/department_id> ?dept .
                         ?employee <http://example.org/position_id> ?pos .
                         ?dept <http://example.org/department_name> ?department_name .
                         ?pos <http://example.org/position_title> ?position_title .
                         ?salary <http://example.org/employee_id> ?emp_id .
                         ?salary <http://example.org/net_salary> ?net_salary .
                         FILTER(?net_salary > 15000)
                     }
                     ORDER BY DESC(?net_salary)
                     LIMIT 10""",
        "expected_vars": ["first_name", "last_name", "department_name", "position_title", "net_salary"],
        "expected_row_count_range": [1, 1000],
        "description": "测试多表JOIN和复杂FILTER条件"
    },
    
    {
        "id": "COMPLEX_003",
        "name": "查询员工考勤统计",
        "category": "Complex Query",
        "sparql": """SELECT ?first_name ?last_name 
                            (COUNT(?attendance) AS ?work_days)
                            (SUM(?overtime_hours) AS ?total_overtime)
                     WHERE { 
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                         ?employee <http://example.org/employee_id> ?emp_id .
                         ?attendance <http://example.org/employee_id> ?emp_id .
                         ?attendance <http://example.org/status> ?status .
                         ?attendance <http://example.org/overtime_hours> ?overtime_hours .
                         FILTER(?status = "Present")
                     }
                     GROUP BY ?first_name ?last_name
                     ORDER BY DESC(?total_overtime)
                     LIMIT 10""",
        "expected_vars": ["first_name", "last_name", "work_days", "total_overtime"],
        "expected_row_count_range": [1, 100],
        "description": "测试考勤数据的多表聚合查询"
    },
    
    # ===== 边界条件测试 =====
    {
        "id": "BOUNDARY_001",
        "name": "查询不存在的部门",
        "category": "Boundary Test",
        "sparql": """SELECT ?employee_id ?first_name
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/department_id> ?dept .
                         ?dept <http://example.org/department_name> ?department_name .
                         FILTER(?department_name = "NonExistentDepartment")
                     }""",
        "expected_vars": ["employee_id", "first_name"],
        "expected_row_count": 0,
        "description": "测试查询不存在的数据，应返回空结果"
    },
    
    {
        "id": "BOUNDARY_002",
        "name": "大量数据LIMIT测试",
        "category": "Boundary Test",
        "sparql": """SELECT ?employee_id ?first_name ?last_name
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                     }
                     LIMIT 1000""",
        "expected_vars": ["employee_id", "first_name", "last_name"],
        "expected_row_count": 1000,
        "description": "测试大数量级LIMIT查询"
    },
    
    {
        "id": "BOUNDARY_003",
        "name": "OFFSET分页测试",
        "category": "Boundary Test",
        "sparql": """SELECT ?employee_id ?first_name ?last_name
                     WHERE { 
                         ?employee <http://example.org/employee_id> ?employee_id .
                         ?employee <http://example.org/first_name> ?first_name .
                         ?employee <http://example.org/last_name> ?last_name .
                     }
                     ORDER BY ?employee_id
                     LIMIT 10
                     OFFSET 100""",
        "expected_vars": ["employee_id", "first_name", "last_name"],
        "expected_row_count": 10,
        "description": "测试OFFSET分页功能"
    }
]

def execute_sparql_test(test_case):
    """执行单个SPARQL测试"""
    print(f"\n{'='*60}")
    print(f"测试ID: {test_case['id']}")
    print(f"测试名称: {test_case['name']}")
    print(f"类别: {test_case['category']}")
    print(f"描述: {test_case['description']}")
    print(f"{'='*60}")
    
    try:
        # 准备请求
        headers = {"Content-Type": "application/json"}
        payload = {"query": test_case['sparql']}
        
        print(f"\n发送请求到: {SPARQL_ENDPOINT}")
        print(f"SPARQL查询:\n{test_case['sparql'][:200]}...")
        
        # 发送请求
        start_time = time.time()
        response = requests.post(
            SPARQL_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"\n响应时间: {response_time:.3f}秒")
        print(f"HTTP状态码: {response.status_code}")
        
        # 检查HTTP响应
        if response.status_code != 200:
            print(f"❌ HTTP错误: {response.status_code}")
            return {
                "test_id": test_case['id'],
                "status": "FAILED",
                "error": f"HTTP {response.status_code}",
                "response_time": response_time
            }
        
        # 解析响应
        try:
            result = response.json()
        except json.JSONDecodeError:
            print(f"❌ JSON解析错误")
            return {
                "test_id": test_case['id'],
                "status": "FAILED",
                "error": "JSON解析失败",
                "response_time": response_time
            }
        
        print(f"\n响应结果:\n{json.dumps(result, indent=2)[:500]}...")
        
        # 验证结果结构
        if "head" not in result or "results" not in result:
            print(f"❌ 响应格式错误: 缺少head或results")
            return {
                "test_id": test_case['id'],
                "status": "FAILED",
                "error": "响应格式错误",
                "response_time": response_time
            }
        
        # 验证变量
        actual_vars = result["head"].get("vars", [])
        expected_vars = test_case.get('expected_vars', [])
        
        if expected_vars:
            missing_vars = [var for var in expected_vars if var not in actual_vars]
            if missing_vars:
                print(f"❌ 缺少预期变量: {missing_vars}")
                return {
                    "test_id": test_case['id'],
                    "status": "FAILED",
                    "error": f"缺少变量: {missing_vars}",
                    "response_time": response_time
                }
        
        # 验证行数
        bindings = result["results"].get("bindings", [])
        actual_row_count = len(bindings)
        
        if 'expected_row_count' in test_case:
            expected_row_count = test_case['expected_row_count']
            if actual_row_count != expected_row_count:
                print(f"❌ 行数不匹配: 预期 {expected_row_count}, 实际 {actual_row_count}")
                return {
                    "test_id": test_case['id'],
                    "status": "FAILED",
                    "error": f"行数不匹配: 预期 {expected_row_count}, 实际 {actual_row_count}",
                    "actual_row_count": actual_row_count,
                    "response_time": response_time
                }
        
        if 'expected_row_count_range' in test_case:
            min_count, max_count = test_case['expected_row_count_range']
            if actual_row_count < min_count or actual_row_count > max_count:
                print(f"❌ 行数超出范围: 预期 {min_count}-{max_count}, 实际 {actual_row_count}")
                return {
                    "test_id": test_case['id'],
                    "status": "FAILED",
                    "error": f"行数超出范围: 预期 {min_count}-{max_count}, 实际 {actual_row_count}",
                    "actual_row_count": actual_row_count,
                    "response_time": response_time
                }
        
        print(f"✅ 测试通过!")
        print(f"   - 变量: {actual_vars}")
        print(f"   - 行数: {actual_row_count}")
        
        return {
            "test_id": test_case['id'],
            "status": "PASSED",
            "actual_row_count": actual_row_count,
            "response_time": response_time
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return {
            "test_id": test_case['id'],
            "status": "FAILED",
            "error": "请求超时",
            "response_time": 30
        }
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return {
            "test_id": test_case['id'],
            "status": "FAILED",
            "error": str(e),
            "response_time": 0
        }

def run_all_tests():
    """运行所有测试"""
    print("=" * 80)
    print("RS Ontop Core V2.0 - Comprehensive SPARQL Test Suite")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"SPARQL端点: {SPARQL_ENDPOINT}")
    print(f"测试用例数: {len(TEST_CASES)}")
    print("=" * 80)
    
    results = []
    passed_count = 0
    failed_count = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] ", end="")
        result = execute_sparql_test(test_case)
        results.append(result)
        
        if result['status'] == 'PASSED':
            passed_count += 1
        else:
            failed_count += 1
    
    # 生成报告
    generate_report(results, passed_count, failed_count)
    
    return results

def generate_report(results, passed_count, failed_count):
    """生成测试报告"""
    print("\n" + "=" * 80)
    print("测试报告")
    print("=" * 80)
    
    total_tests = len(results)
    pass_rate = (passed_count / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_count}")
    print(f"失败: {failed_count}")
    print(f"通过率: {pass_rate:.1f}%")
    
    if failed_count > 0:
        print("\n失败测试详情:")
        print("-" * 80)
        for result in results:
            if result['status'] == 'FAILED':
                print(f"  {result['test_id']}: {result.get('error', 'Unknown error')}")
    
    # 按类别统计
    print("\n按类别统计:")
    print("-" * 80)
    categories = {}
    for i, test_case in enumerate(TEST_CASES):
        category = test_case['category']
        if category not in categories:
            categories[category] = {'total': 0, 'passed': 0}
        categories[category]['total'] += 1
        if results[i]['status'] == 'PASSED':
            categories[category]['passed'] += 1
    
    for category, stats in categories.items():
        rate = (stats['passed'] / stats['total']) * 100
        print(f"  {category}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
    
    print("\n" + "=" * 80)
    
    # 保存详细报告
    report_data = {
        "test_time": datetime.now().isoformat(),
        "total_tests": total_tests,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": pass_rate,
        "results": results,
        "categories": {cat: stats for cat, stats in categories.items()}
    }
    
    with open('/home/yuxiaoyu/rs_ontop_core/sparql_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"详细报告已保存到: sparql_test_report.json")

if __name__ == "__main__":
    try:
        # 测试连接
        print("检查SPARQL端点连接...")
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ 连接成功: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到SPARQL端点: {e}")
        print("请确保服务器已启动: psql -c \"SELECT ontop_start_sparql_server();\"")
        exit(1)
    
    # 运行所有测试
    run_all_tests()
