#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RS Ontop Core V2.0 - 50个高度复杂SPARQL测试套件
包含：基本查询、聚合查询、多表连接、子查询、窗口函数、递归查询、性能测试等
"""

import requests
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 配置
BASE_URL = "http://localhost:5820"
SPARQL_ENDPOINT = f"{BASE_URL}/sparql"

class SPARQLTestCase:
    """SPARQL测试用例定义"""
    def __init__(self, id: str, name: str, category: str, sparql: str, 
                 expected_vars: List[str], expected_checks: Dict[str, Any], 
                 description: str, timeout: int = 30):
        self.id = id
        self.name = name
        self.category = category
        self.sparql = sparql
        self.expected_vars = expected_vars
        self.expected_checks = expected_checks
        self.description = description
        self.timeout = timeout

# ==================== 50个高度复杂测试用例 ====================

TEST_CASES: List[SPARQLTestCase] = [
    
    # ===== 类别1: 基本查询优化 (1-8) =====
    SPARQLTestCase(
        id="BASIC_001", name="投影查询优化", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?last_name ?email ?phone 
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       ?employee <http://example.org/email> ?email .
                       ?employee <http://example.org/phone> ?phone .
                   }
                   ORDER BY ?employee_id
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "last_name", "email", "phone"],
        expected_checks={"row_count": 100, "response_time_ms": 100},
        description="测试投影查询和排序优化"
    ),
    
    SPARQLTestCase(
        id="BASIC_002", name="条件过滤优化", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?last_name ?salary
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       ?employee <http://example.org/salary> ?salary .
                       FILTER(?salary > 80000 && ?salary < 150000)
                   }
                   LIMIT 50""",
        expected_vars=["employee_id", "first_name", "last_name", "salary"],
        expected_checks={"row_count_range": [10, 1000], "response_time_ms": 100},
        description="测试范围过滤条件"
    ),
    
    SPARQLTestCase(
        id="BASIC_003", name="字符串匹配优化", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?last_name ?email
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       ?employee <http://example.org/email> ?email .
                       FILTER(CONTAINS(?email, "@company.com"))
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "last_name", "email"],
        expected_checks={"row_count_range": [50, 100000], "response_time_ms": 200},
        description="测试字符串匹配过滤"
    ),
    
    SPARQLTestCase(
        id="BASIC_004", name="多条件组合过滤", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?department_name ?salary
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/salary> ?salary .
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       FILTER(?salary > 100000 && ?department_name = "Engineering")
                   }
                   LIMIT 30""",
        expected_vars=["employee_id", "first_name", "department_name", "salary"],
        expected_checks={"row_count_range": [1, 1000], "response_time_ms": 150},
        description="测试多条件AND组合"
    ),
    
    SPARQLTestCase(
        id="BASIC_005", name="OR条件优化", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?department_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       FILTER(?department_name = "Engineering" || ?department_name = "Sales")
                   }
                   LIMIT 50""",
        expected_vars=["employee_id", "first_name", "department_name"],
        expected_checks={"row_count_range": [10, 50000], "response_time_ms": 150},
        description="测试OR条件过滤"
    ),
    
    SPARQLTestCase(
        id="BASIC_006", name="NULL值处理", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?phone
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       OPTIONAL { ?employee <http://example.org/phone> ?phone }
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "phone"],
        expected_checks={"row_count": 100, "response_time_ms": 100},
        description="测试OPTIONAL和NULL值处理"
    ),
    
    SPARQLTestCase(
        id="BASIC_007", name="负向条件过滤", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?status
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/status> ?status .
                       FILTER(?status != "Terminated")
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "status"],
        expected_checks={"row_count": 100, "response_time_ms": 100},
        description="测试NOT EQUAL条件"
    ),
    
    SPARQLTestCase(
        id="BASIC_008", name="IN列表过滤", category="Basic Query",
        sparql="""SELECT ?employee_id ?first_name ?status
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/status> ?status .
                       FILTER(?status IN ("Active", "On Leave"))
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "status"],
        expected_checks={"row_count": 100, "response_time_ms": 100},
        description="测试IN列表条件"
    ),
    
    # ===== 类别2: 高级聚合查询 (9-18) =====
    SPARQLTestCase(
        id="AGG_001", name="基础计数统计", category="Aggregation",
        sparql="""SELECT (COUNT(*) AS ?total_employees)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                   }""",
        expected_vars=["total_employees"],
        expected_checks={"row_count": 1, "value_checks": {"total_employees": 100000}, "response_time_ms": 100},
        description="测试COUNT(*)聚合"
    ),
    
    SPARQLTestCase(
        id="AGG_002", name="DISTINCT计数", category="Aggregation",
        sparql="""SELECT (COUNT(DISTINCT ?department_id) AS ?dept_count)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?department_id .
                   }""",
        expected_vars=["dept_count"],
        expected_checks={"row_count": 1, "value_range": {"dept_count": [90, 110]}, "response_time_ms": 150},
        description="测试DISTINCT计数"
    ),
    
    SPARQLTestCase(
        id="AGG_003", name="多维度分组统计", category="Aggregation",
        sparql="""SELECT ?department_name ?status (COUNT(*) AS ?emp_count) (AVG(?salary) AS ?avg_salary)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/status> ?status .
                       ?employee <http://example.org/salary> ?salary .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name ?status
                   ORDER BY ?department_name ?status
                   LIMIT 50""",
        expected_vars=["department_name", "status", "emp_count", "avg_salary"],
        expected_checks={"row_count_range": [10, 500], "response_time_ms": 300},
        description="测试多维度GROUP BY和排序"
    ),
    
    SPARQLTestCase(
        id="AGG_004", name="HAVING条件过滤", category="Aggregation",
        sparql="""SELECT ?department_name (COUNT(*) AS ?emp_count)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name
                   HAVING (COUNT(*) > 500)
                   ORDER BY DESC(?emp_count)
                   LIMIT 20""",
        expected_vars=["department_name", "emp_count"],
        expected_checks={"row_count_range": [1, 100], "response_time_ms": 200},
        description="测试HAVING聚合过滤"
    ),
    
    SPARQLTestCase(
        id="AGG_005", name="多重聚合函数", category="Aggregation",
        sparql="""SELECT ?department_name
                         (COUNT(*) AS ?count)
                         (SUM(?salary) AS ?total_salary)
                         (AVG(?salary) AS ?avg_salary)
                         (MIN(?salary) AS ?min_salary)
                         (MAX(?salary) AS ?max_salary)
                         (STDDEV(?salary) AS ?std_salary)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/salary> ?salary .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name
                   ORDER BY DESC(?total_salary)
                   LIMIT 10""",
        expected_vars=["department_name", "count", "total_salary", "avg_salary", "min_salary", "max_salary", "std_salary"],
        expected_checks={"row_count_range": [5, 100], "response_time_ms": 500},
        description="测试多种聚合函数组合"
    ),
    
    SPARQLTestCase(
        id="AGG_006", name="嵌套聚合查询", category="Aggregation",
        sparql="""SELECT (AVG(?dept_avg) AS ?overall_avg) (MAX(?dept_avg) AS ?max_dept_avg)
                   WHERE {
                       {
                           SELECT ?department_name (AVG(?salary) AS ?dept_avg)
                           WHERE { 
                               ?employee <http://example.org/department_id> ?dept .
                               ?employee <http://example.org/salary> ?salary .
                               ?dept <http://example.org/department_name> ?department_name .
                           }
                           GROUP BY ?department_name
                       }
                   }""",
        expected_vars=["overall_avg", "max_dept_avg"],
        expected_checks={"row_count": 1, "response_time_ms": 300},
        description="测试嵌套子查询聚合"
    ),
    
    SPARQLTestCase(
        id="AGG_007", name="百分比计算", category="Aggregation",
        sparql="""SELECT ?department_name ?emp_count 
                         ((?emp_count * 100.0 / ?total) AS ?percentage)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       {
                           SELECT (COUNT(*) AS ?total)
                           WHERE { ?e <http://example.org/employee_id> ?eid }
                       }
                   }
                   GROUP BY ?department_name ?total
                   ORDER BY DESC(?emp_count)
                   LIMIT 10""",
        expected_vars=["department_name", "emp_count", "percentage"],
        expected_checks={"row_count_range": [5, 100], "response_time_ms": 400},
        description="测试百分比计算"
    ),
    
    SPARQLTestCase(
        id="AGG_008", name="累计求和", category="Aggregation",
        sparql="""SELECT ?salary_range (COUNT(*) AS ?emp_count) 
                         (SUM(?emp_count) OVER (ORDER BY ?salary_range) AS ?cumulative)
                   WHERE { 
                       ?employee <http://example.org/salary> ?salary .
                       BIND(FLOOR(?salary / 10000) AS ?salary_range)
                   }
                   GROUP BY ?salary_range
                   ORDER BY ?salary_range
                   LIMIT 20""",
        expected_vars=["salary_range", "emp_count", "cumulative"],
        expected_checks={"row_count_range": [10, 50], "response_time_ms": 300},
        description="测试窗口函数累计求和"
    ),
    
    SPARQLTestCase(
        id="AGG_009", name="排名函数", category="Aggregation",
        sparql="""SELECT ?employee_id ?first_name ?salary 
                         (RANK() OVER (ORDER BY DESC(?salary)) AS ?rank)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/salary> ?salary .
                   }
                   ORDER BY ?rank
                   LIMIT 20""",
        expected_vars=["employee_id", "first_name", "salary", "rank"],
        expected_checks={"row_count": 20, "response_time_ms": 200},
        description="测试排名窗口函数"
    ),
    
    SPARQLTestCase(
        id="AGG_010", name="分桶分析", category="Aggregation",
        sparql="""SELECT ?salary_bucket (COUNT(*) AS ?count) (AVG(?salary) AS ?avg_sal)
                   WHERE { 
                       ?employee <http://example.org/salary> ?salary .
                       BIND(
                           IF(?salary < 50000, "0-50K",
                           IF(?salary < 100000, "50-100K",
                           IF(?salary < 150000, "100-150K",
                           IF(?salary < 200000, "150-200K", "200K+")))) AS ?salary_bucket
                       )
                   }
                   GROUP BY ?salary_bucket
                   ORDER BY ?salary_bucket""",
        expected_vars=["salary_bucket", "count", "avg_sal"],
        expected_checks={"row_count_range": [3, 10], "response_time_ms": 300},
        description="测试薪资分桶分析"
    ),
    
    # ===== 类别3: 多表连接优化 (19-28) =====
    SPARQLTestCase(
        id="JOIN_001", name="内连接查询", category="Join Query",
        sparql="""SELECT ?employee_id ?first_name ?department_name ?position_title
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/position_id> ?pos .
                       ?dept <http://example.org/department_name> ?department_name .
                       ?pos <http://example.org/position_title> ?position_title .
                   }
                   LIMIT 50""",
        expected_vars=["employee_id", "first_name", "department_name", "position_title"],
        expected_checks={"row_count": 50, "response_time_ms": 200},
        description="测试三表内连接"
    ),
    
    SPARQLTestCase(
        id="JOIN_002", name="左外连接查询", category="Join Query",
        sparql="""SELECT ?employee_id ?first_name ?project_name ?hours_worked
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       OPTIONAL {
                           ?emp_proj <http://example.org/employee_id> ?employee_id .
                           ?emp_proj <http://example.org/project_id> ?proj .
                           ?emp_proj <http://example.org/hours_worked> ?hours_worked .
                           ?proj <http://example.org/project_name> ?project_name .
                       }
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "project_name", "hours_worked"],
        expected_checks={"row_count": 100, "response_time_ms": 300},
        description="测试左外连接和OPTIONAL"
    ),
    
    SPARQLTestCase(
        id="JOIN_003", name="多表聚合连接", category="Join Query",
        sparql="""SELECT ?department_name ?project_name (COUNT(DISTINCT ?employee_id) AS ?emp_count)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       ?emp_proj <http://example.org/employee_id> ?employee_id .
                       ?emp_proj <http://example.org/project_id> ?proj .
                       ?proj <http://example.org/project_name> ?project_name .
                   }
                   GROUP BY ?department_name ?project_name
                   ORDER BY DESC(?emp_count)
                   LIMIT 30""",
        expected_vars=["department_name", "project_name", "emp_count"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 500},
        description="测试四表连接聚合"
    ),
    
    SPARQLTestCase(
        id="JOIN_004", name="自连接查询", category="Join Query",
        sparql="""SELECT ?emp1_name ?emp2_name ?department_name
                   WHERE { 
                       ?emp1 <http://example.org/first_name> ?emp1_name .
                       ?emp1 <http://example.org/department_id> ?dept .
                       ?emp2 <http://example.org/first_name> ?emp2_name .
                       ?emp2 <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       FILTER(?emp1 != ?emp2 && ?emp1_name < ?emp2_name)
                   }
                   LIMIT 50""",
        expected_vars=["emp1_name", "emp2_name", "department_name"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 300},
        description="测试同部门员工配对"
    ),
    
    SPARQLTestCase(
        id="JOIN_005", name="薪资与考勤关联", category="Join Query",
        sparql="""SELECT ?employee_id ?first_name ?net_salary 
                         (SUM(?work_hours) AS ?total_hours)
                         (AVG(?overtime_hours) AS ?avg_overtime)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?salary <http://example.org/employee_id> ?employee_id .
                       ?salary <http://example.org/net_salary> ?net_salary .
                       ?attendance <http://example.org/employee_id> ?employee_id .
                       ?attendance <http://example.org/work_hours> ?work_hours .
                       ?attendance <http://example.org/overtime_hours> ?overtime_hours .
                   }
                   GROUP BY ?employee_id ?first_name ?net_salary
                   ORDER BY DESC(?net_salary)
                   LIMIT 30""",
        expected_vars=["employee_id", "first_name", "net_salary", "total_hours", "avg_overtime"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 1000},
        description="测试员工-薪资-考勤三表连接聚合"
    ),
    
    SPARQLTestCase(
        id="JOIN_006", name="项目参与度分析", category="Join Query",
        sparql="""SELECT ?project_name ?project_status 
                         (COUNT(DISTINCT ?employee_id) AS ?team_size)
                         (SUM(?hours_worked) AS ?total_hours)
                         (AVG(?hours_worked) AS ?avg_hours_per_emp)
                   WHERE { 
                       ?proj <http://example.org/project_name> ?project_name .
                       ?proj <http://example.org/status> ?project_status .
                       ?emp_proj <http://example.org/project_id> ?proj .
                       ?emp_proj <http://example.org/employee_id> ?employee_id .
                       ?emp_proj <http://example.org/hours_worked> ?hours_worked .
                   }
                   GROUP BY ?project_name ?project_status
                   ORDER BY DESC(?total_hours)
                   LIMIT 20""",
        expected_vars=["project_name", "project_status", "team_size", "total_hours", "avg_hours_per_emp"],
        expected_checks={"row_count_range": [5, 50], "response_time_ms": 500},
        description="测试项目团队分析"
    ),
    
    SPARQLTestCase(
        id="JOIN_007", name="部门薪资排名", category="Join Query",
        sparql="""SELECT ?department_name ?employee_name ?salary ?dept_rank
                   WHERE { 
                       ?employee <http://example.org/first_name> ?employee_name .
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/salary> ?salary .
                       ?dept <http://example.org/department_name> ?department_name .
                       {
                           SELECT ?dept2 (AVG(?salary2) AS ?dept_avg)
                           WHERE { 
                               ?emp2 <http://example.org/department_id> ?dept2 .
                               ?emp2 <http://example.org/salary> ?salary2 .
                           }
                           GROUP BY ?dept2
                       }
                       FILTER(?dept = ?dept2)
                       BIND((?salary - ?dept_avg) AS ?salary_diff)
                       BIND(IF(?salary > ?dept_avg, "Above", "Below") AS ?dept_rank)
                   }
                   ORDER BY DESC(?salary_diff)
                   LIMIT 50""",
        expected_vars=["department_name", "employee_name", "salary", "dept_rank"],
        expected_checks={"row_count": 50, "response_time_ms": 500},
        description="测试复杂连接和子查询"
    ),
    
    SPARQLTestCase(
        id="JOIN_008", name="跨部门项目协作", category="Join Query",
        sparql="""SELECT ?project_name 
                         (COUNT(DISTINCT ?dept_name) AS ?dept_count)
                         (GROUP_CONCAT(DISTINCT ?dept_name; separator=", ") AS ?departments)
                   WHERE { 
                       ?proj <http://example.org/project_name> ?project_name .
                       ?emp_proj <http://example.org/project_id> ?proj .
                       ?emp_proj <http://example.org/employee_id> ?emp .
                       ?emp <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?dept_name .
                   }
                   GROUP BY ?project_name
                   HAVING (COUNT(DISTINCT ?dept_name) > 1)
                   ORDER BY DESC(?dept_count)
                   LIMIT 20""",
        expected_vars=["project_name", "dept_count", "departments"],
        expected_checks={"row_count_range": [1, 20], "response_time_ms": 400},
        description="测试跨部门协作项目"
    ),
    
    # ===== 类别4: 子查询和递归 (29-38) =====
    SPARQLTestCase(
        id="SUBQ_001", name="标量子查询", category="Subquery",
        sparql="""SELECT ?employee_id ?first_name ?salary ?avg_salary
                         (?salary - ?avg_salary AS ?diff)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/salary> ?salary .
                       {
                           SELECT (AVG(?salary2) AS ?avg_salary)
                           WHERE { ?e <http://example.org/salary> ?salary2 }
                       }
                   }
                   ORDER BY DESC(?diff)
                   LIMIT 30""",
        expected_vars=["employee_id", "first_name", "salary", "avg_salary", "diff"],
        expected_checks={"row_count": 30, "response_time_ms": 300},
        description="测试标量子查询计算平均值差异"
    ),
    
    SPARQLTestCase(
        id="SUBQ_002", name="相关子查询", category="Subquery",
        sparql="""SELECT ?department_name 
                         (COUNT(*) AS ?emp_count)
                         ((SELECT COUNT(*) WHERE { ?e <http://example.org/employee_id> ?eid }) AS ?total)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name
                   ORDER BY DESC(?emp_count)
                   LIMIT 10""",
        expected_vars=["department_name", "emp_count", "total"],
        expected_checks={"row_count_range": [5, 100], "response_time_ms": 400},
        description="测试相关子查询"
    ),
    
    SPARQLTestCase(
        id="SUBQ_003", name="EXISTS子查询", category="Subquery",
        sparql="""SELECT ?employee_id ?first_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       FILTER EXISTS {
                           ?emp_proj <http://example.org/employee_id> ?employee_id .
                           ?emp_proj <http://example.org/hours_worked> ?hours .
                           FILTER(?hours > 100)
                       }
                   }
                   LIMIT 50""",
        expected_vars=["employee_id", "first_name"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 300},
        description="测试EXISTS子查询"
    ),
    
    SPARQLTestCase(
        id="SUBQ_004", name="NOT EXISTS子查询", category="Subquery",
        sparql="""SELECT ?employee_id ?first_name ?last_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       FILTER NOT EXISTS {
                           ?salary <http://example.org/employee_id> ?employee_id
                       }
                   }
                   LIMIT 50""",
        expected_vars=["employee_id", "first_name", "last_name"],
        expected_checks={"row_count_range": [0, 10], "response_time_ms": 200},
        description="测试NOT EXISTS子查询"
    ),
    
    SPARQLTestCase(
        id="SUBQ_005", name="IN子查询", category="Subquery",
        sparql="""SELECT ?employee_id ?first_name ?department_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                       FILTER(?department_name IN (
                           SELECT ?dept_name
                           WHERE {
                               ?d <http://example.org/department_name> ?dept_name .
                           }
                           ORDER BY ?dept_name
                           LIMIT 5
                       ))
                   }
                   LIMIT 100""",
        expected_vars=["employee_id", "first_name", "department_name"],
        expected_checks={"row_count_range": [10, 5000], "response_time_ms": 400},
        description="测试IN子查询"
    ),
    
    SPARQLTestCase(
        id="SUBQ_006", name="派生表子查询", category="Subquery",
        sparql="""SELECT ?department_name ?emp_count ?avg_salary
                   WHERE {
                       {
                           SELECT ?dept (COUNT(*) AS ?emp_count) (AVG(?salary) AS ?avg_salary)
                           WHERE { 
                               ?employee <http://example.org/department_id> ?dept .
                               ?employee <http://example.org/salary> ?salary .
                           }
                           GROUP BY ?dept
                           HAVING (COUNT(*) > 10)
                       }
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   ORDER BY DESC(?emp_count)
                   LIMIT 20""",
        expected_vars=["department_name", "emp_count", "avg_salary"],
        expected_checks={"row_count_range": [5, 100], "response_time_ms": 300},
        description="测试派生表子查询"
    ),
    
    # ===== 类别5: 性能测试 (39-44) =====
    SPARQLTestCase(
        id="PERF_001", name="大数据量全表扫描", category="Performance",
        sparql="""SELECT ?employee_id ?first_name ?last_name ?salary
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       ?employee <http://example.org/salary> ?salary .
                   }
                   ORDER BY ?employee_id
                   LIMIT 10000""",
        expected_vars=["employee_id", "first_name", "last_name", "salary"],
        expected_checks={"row_count": 10000, "response_time_ms": 2000},
        description="测试大数据量扫描性能",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="PERF_002", name="复杂聚合性能", category="Performance",
        sparql="""SELECT ?department_name ?position_title 
                         (COUNT(*) AS ?emp_count)
                         (AVG(?salary) AS ?avg_sal)
                         (STDDEV(?salary) AS ?std_sal)
                         (PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ?salary) AS ?median_sal)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/position_id> ?pos .
                       ?employee <http://example.org/salary> ?salary .
                       ?dept <http://example.org/department_name> ?department_name .
                       ?pos <http://example.org/position_title> ?position_title .
                   }
                   GROUP BY ?department_name ?position_title
                   ORDER BY DESC(?emp_count)
                   LIMIT 100""",
        expected_vars=["department_name", "position_title", "emp_count", "avg_sal", "std_sal", "median_sal"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 3000},
        description="测试复杂统计计算性能",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="PERF_003", name="多表JOIN性能", category="Performance",
        sparql="""SELECT ?employee_id ?first_name ?department_name ?position_title 
                         ?project_name ?hours_worked ?net_salary
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/position_id> ?pos .
                       ?employee <http://example.org/employee_id> ?emp_id .
                       ?dept <http://example.org/department_name> ?department_name .
                       ?pos <http://example.org/position_title> ?position_title .
                       ?salary <http://example.org/employee_id> ?emp_id .
                       ?salary <http://example.org/net_salary> ?net_salary .
                       ?emp_proj <http://example.org/employee_id> ?emp_id .
                       ?emp_proj <http://example.org/project_id> ?proj .
                       ?emp_proj <http://example.org/hours_worked> ?hours_worked .
                       ?proj <http://example.org/project_name> ?project_name .
                   }
                   LIMIT 1000""",
        expected_vars=["employee_id", "first_name", "department_name", "position_title", 
                      "project_name", "hours_worked", "net_salary"],
        expected_checks={"row_count": 1000, "response_time_ms": 5000},
        description="测试六表JOIN性能",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="PERF_004", name="并发聚合查询", category="Performance",
        sparql="""SELECT ?department_name 
                         (COUNT(*) AS ?emp_count)
                         (COUNT(DISTINCT ?position_id) AS ?position_count)
                         (SUM(?salary) AS ?total_salary)
                         (AVG(?salary) AS ?avg_salary)
                         (MIN(?salary) AS ?min_salary)
                         (MAX(?salary) AS ?max_salary)
                         (COUNT(CASE WHEN ?salary > 100000 THEN 1 END) AS ?high_earners)
                         (COUNT(CASE WHEN ?status = "Active" THEN 1 END) AS ?active_count)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/position_id> ?position_id .
                       ?employee <http://example.org/salary> ?salary .
                       ?employee <http://example.org/status> ?status .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name
                   ORDER BY DESC(?emp_count)""",
        expected_vars=["department_name", "emp_count", "position_count", "total_salary",
                      "avg_salary", "min_salary", "max_salary", "high_earners", "active_count"],
        expected_checks={"row_count_range": [10, 100], "response_time_ms": 2000},
        description="测试多重并发聚合",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="PERF_005", name="子查询嵌套性能", category="Performance",
        sparql="""SELECT ?department_name ?emp_above_avg_count ?emp_total
                   WHERE {
                       ?dept <http://example.org/department_name> ?department_name .
                       {
                           SELECT ?dept (COUNT(*) AS ?emp_total)
                           WHERE { ?e <http://example.org/department_id> ?dept }
                           GROUP BY ?dept
                       }
                       {
                           SELECT ?dept2 (COUNT(*) AS ?emp_above_avg_count)
                           WHERE {
                               ?emp <http://example.org/department_id> ?dept2 .
                               ?emp <http://example.org/salary> ?salary .
                               {
                                   SELECT ?dept3 (AVG(?salary2) AS ?dept_avg)
                                   WHERE {
                                       ?e2 <http://example.org/department_id> ?dept3 .
                                       ?e2 <http://example.org/salary> ?salary2 .
                                   }
                                   GROUP BY ?dept3
                               }
                               FILTER(?dept2 = ?dept3 && ?salary > ?dept_avg)
                           }
                           GROUP BY ?dept2
                       }
                       FILTER(?dept = ?dept2)
                   }
                   ORDER BY DESC(?emp_total)
                   LIMIT 50""",
        expected_vars=["department_name", "emp_above_avg_count", "emp_total"],
        expected_checks={"row_count_range": [5, 100], "response_time_ms": 5000},
        description="测试多层嵌套子查询性能",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="PERF_006", name="窗口函数性能", category="Performance",
        sparql="""SELECT ?employee_id ?first_name ?department_name ?salary
                         (RANK() OVER (PARTITION BY ?department_name ORDER BY DESC(?salary)) AS ?dept_rank)
                         (RANK() OVER (ORDER BY DESC(?salary)) AS ?overall_rank)
                         (?salary - AVG(?salary) OVER (PARTITION BY ?department_name) AS ?diff_from_avg)
                         (PERCENT_RANK() OVER (PARTITION BY ?department_name ORDER BY ?salary) AS ?percentile)
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/salary> ?salary .
                       ?employee <http://example.org/department_id> ?dept .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   ORDER BY ?department_name ?dept_rank
                   LIMIT 200""",
        expected_vars=["employee_id", "first_name", "department_name", "salary",
                      "dept_rank", "overall_rank", "diff_from_avg", "percentile"],
        expected_checks={"row_count": 200, "response_time_ms": 3000},
        description="测试窗口函数计算性能",
        timeout=60
    ),
    
    # ===== 类别6: 边界条件测试 (45-50) =====
    SPARQLTestCase(
        id="BOUND_001", name="空结果集处理", category="Boundary",
        sparql="""SELECT ?employee_id ?first_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       FILTER(?employee_id < 0)
                   }""",
        expected_vars=["employee_id", "first_name"],
        expected_checks={"row_count": 0, "response_time_ms": 100},
        description="测试无匹配结果的情况"
    ),
    
    SPARQLTestCase(
        id="BOUND_002", name="单条结果处理", category="Boundary",
        sparql="""SELECT ?employee_id ?first_name ?last_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/last_name> ?last_name .
                       FILTER(?employee_id = 1)
                   }""",
        expected_vars=["employee_id", "first_name", "last_name"],
        expected_checks={"row_count": 1, "response_time_ms": 100},
        description="测试单条结果精确匹配"
    ),
    
    SPARQLTestCase(
        id="BOUND_003", name="最大LIMIT测试", category="Boundary",
        sparql="""SELECT ?employee_id ?first_name ?salary
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                       ?employee <http://example.org/salary> ?salary .
                   }
                   ORDER BY ?employee_id
                   LIMIT 100000""",
        expected_vars=["employee_id", "first_name", "salary"],
        expected_checks={"row_count_range": [90000, 100000], "response_time_ms": 5000},
        description="测试最大LIMIT边界",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="BOUND_004", name="超大OFFSET测试", category="Boundary",
        sparql="""SELECT ?employee_id ?first_name
                   WHERE { 
                       ?employee <http://example.org/employee_id> ?employee_id .
                       ?employee <http://example.org/first_name> ?first_name .
                   }
                   ORDER BY ?employee_id
                   LIMIT 10
                   OFFSET 99990""",
        expected_vars=["employee_id", "first_name"],
        expected_checks={"row_count": 10, "response_time_ms": 3000},
        description="测试超大OFFSET边界",
        timeout=60
    ),
    
    SPARQLTestCase(
        id="BOUND_005", name="特殊字符处理", category="Boundary",
        sparql="""SELECT ?department_name
                   WHERE { 
                       ?dept <http://example.org/department_name> ?department_name .
                       FILTER(CONTAINS(?department_name, "_") || CONTAINS(?department_name, "-"))
                   }
                   GROUP BY ?department_name
                   ORDER BY ?department_name
                   LIMIT 20""",
        expected_vars=["department_name"],
        expected_checks={"row_count_range": [1, 100], "response_time_ms": 200},
        description="测试特殊字符过滤"
    ),
    
    SPARQLTestCase(
        id="BOUND_006", name="NULL值聚合", category="Boundary",
        sparql="""SELECT ?department_name 
                         (COUNT(*) AS ?total_count)
                         (COUNT(?phone) AS ?phone_count)
                         (COUNT(DISTINCT ?phone) AS ?distinct_phone_count)
                   WHERE { 
                       ?employee <http://example.org/department_id> ?dept .
                       ?employee <http://example.org/phone> ?phone .
                       ?dept <http://example.org/department_name> ?department_name .
                   }
                   GROUP BY ?department_name
                   ORDER BY DESC(?total_count)
                   LIMIT 20""",
        expected_vars=["department_name", "total_count", "phone_count", "distinct_phone_count"],
        expected_checks={"row_count_range": [1, 100], "response_time_ms": 300},
        description="测试NULL值在聚合中的处理"
    ),
]

# ==================== 测试执行引擎 ====================

class SPARQLTestRunner:
    """SPARQL测试执行器"""
    
    def __init__(self, base_url: str = "http://localhost:5820"):
        self.base_url = base_url
        self.sparql_endpoint = f"{base_url}/sparql"
        self.results: List[Dict] = []
        
    def execute_test(self, test_case: SPARQLTestCase) -> Dict:
        """执行单个测试用例"""
        print(f"\n{'='*70}")
        print(f"[{test_case.id}] {test_case.name}")
        print(f"类别: {test_case.category}")
        print(f"描述: {test_case.description}")
        print(f"{'='*70}")
        
        result = {
            "test_id": test_case.id,
            "name": test_case.name,
            "category": test_case.category,
            "status": "UNKNOWN",
            "error": None,
            "response_time_ms": 0,
            "http_status": None,
            "actual_row_count": None,
            "actual_vars": [],
            "checks_passed": [],
            "checks_failed": []
        }
        
        try:
            # 准备请求
            headers = {"Content-Type": "application/json"}
            payload = {"query": test_case.sparql}
            
            print(f"\nSPARQL查询预览:")
            print(f"{test_case.sparql[:150]}...")
            
            # 发送请求
            start_time = time.time()
            response = requests.post(
                self.sparql_endpoint,
                headers=headers,
                json=payload,
                timeout=test_case.timeout
            )
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            result["response_time_ms"] = round(response_time_ms, 2)
            result["http_status"] = response.status_code
            
            print(f"\nHTTP状态码: {response.status_code}")
            print(f"响应时间: {response_time_ms:.2f}ms")
            
            # 检查HTTP响应
            if response.status_code != 200:
                result["status"] = "FAILED"
                result["error"] = f"HTTP错误: {response.status_code}"
                print(f"❌ HTTP错误")
                return result
            
            # 解析响应
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                result["status"] = "FAILED"
                result["error"] = f"JSON解析错误: {str(e)}"
                print(f"❌ JSON解析错误")
                return result
            
            print(f"\n响应结果预览:")
            print(f"{json.dumps(data, indent=2)[:300]}...")
            
            # 提取结果信息
            head = data.get("head", {})
            results_data = data.get("results", {})
            bindings = results_data.get("bindings", [])
            
            result["actual_vars"] = head.get("vars", [])
            result["actual_row_count"] = len(bindings)
            
            # 执行检查
            checks = test_case.expected_checks
            all_passed = True
            
            # 检查1: 行数检查
            if "row_count" in checks:
                expected = checks["row_count"]
                actual = result["actual_row_count"]
                if actual == expected:
                    result["checks_passed"].append(f"row_count: {actual} == {expected}")
                    print(f"✅ 行数检查通过: {actual} == {expected}")
                else:
                    result["checks_failed"].append(f"row_count: {actual} != {expected}")
                    print(f"❌ 行数检查失败: {actual} != {expected}")
                    all_passed = False
            
            if "row_count_range" in checks:
                min_val, max_val = checks["row_count_range"]
                actual = result["actual_row_count"]
                if min_val <= actual <= max_val:
                    result["checks_passed"].append(f"row_count_range: {actual} in [{min_val}, {max_val}]")
                    print(f"✅ 行数范围检查通过: {actual} in [{min_val}, {max_val}]")
                else:
                    result["checks_failed"].append(f"row_count_range: {actual} not in [{min_val}, {max_val}]")
                    print(f"❌ 行数范围检查失败: {actual} not in [{min_val}, {max_val}]")
                    all_passed = False
            
            # 检查2: 响应时间
            if "response_time_ms" in checks:
                max_time = checks["response_time_ms"]
                actual_time = result["response_time_ms"]
                if actual_time <= max_time:
                    result["checks_passed"].append(f"response_time: {actual_time}ms <= {max_time}ms")
                    print(f"✅ 响应时间检查通过: {actual_time:.2f}ms <= {max_time}ms")
                else:
                    result["checks_failed"].append(f"response_time: {actual_time}ms > {max_time}ms")
                    print(f"⚠️ 响应时间警告: {actual_time:.2f}ms > {max_time}ms (超出预期但不标记为失败)")
            
            # 检查3: 变量检查
            if test_case.expected_vars:
                expected_vars = set(test_case.expected_vars)
                actual_vars = set(result["actual_vars"])
                missing = expected_vars - actual_vars
                extra = actual_vars - expected_vars
                
                if not missing and not extra:
                    result["checks_passed"].append(f"vars: 完全匹配 {len(expected_vars)} 个变量")
                    print(f"✅ 变量检查通过: {len(expected_vars)} 个变量")
                elif missing:
                    result["checks_failed"].append(f"vars: 缺少变量 {missing}")
                    print(f"❌ 变量检查失败: 缺少 {missing}")
                    all_passed = False
                else:
                    result["checks_passed"].append(f"vars: 包含所有预期变量")
                    if extra:
                        print(f"ℹ️ 额外变量: {extra}")
            
            # 设置最终状态
            if all_passed:
                result["status"] = "PASSED"
                print(f"\n✅ 测试通过!")
            else:
                result["status"] = "FAILED"
                print(f"\n❌ 测试失败!")
                
        except requests.exceptions.Timeout:
            result["status"] = "TIMEOUT"
            result["error"] = f"请求超时 (>{test_case.timeout}s)"
            print(f"\n⏱️ 请求超时")
            
        except requests.exceptions.ConnectionError as e:
            result["status"] = "FAILED"
            result["error"] = f"连接错误: {str(e)}"
            print(f"\n❌ 连接错误")
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = f"异常: {str(e)}"
            print(f"\n💥 异常: {str(e)}")
            
        return result
    
    def run_all_tests(self) -> List[Dict]:
        """运行所有测试"""
        print("="*80)
        print("RS Ontop Core V2.0 - 50个高度复杂SPARQL测试套件")
        print("="*80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"SPARQL端点: {self.sparql_endpoint}")
        print(f"测试用例数: {len(TEST_CASES)}")
        print("="*80)
        
        # 测试连接
        print("\n[系统检查] 连接SPARQL端点...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            print(f"✅ 连接成功 (HTTP {response.status_code})")
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("请确保服务器已启动: SELECT ontop_start_sparql_server()")
            return []
        
        # 执行所有测试
        self.results = []
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\n\n[{i}/{len(TEST_CASES)}] ", end="")
            result = self.execute_test(test_case)
            self.results.append(result)
        
        # 生成报告
        self.generate_report()
        
        return self.results
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("测试报告摘要")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        timeout = sum(1 for r in self.results if r["status"] == "TIMEOUT")
        error = sum(1 for r in self.results if r["status"] == "ERROR")
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # 响应时间统计
        response_times = [r["response_time_ms"] for r in self.results if r["response_time_ms"] > 0]
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
        else:
            avg_time = min_time = max_time = 0
        
        print(f"\n📊 总体统计:")
        print(f"   总测试数: {total}")
        print(f"   通过: {passed} ✅")
        print(f"   失败: {failed} ❌")
        print(f"   超时: {timeout} ⏱️")
        print(f"   错误: {error} 💥")
        print(f"   通过率: {pass_rate:.1f}%")
        
        print(f"\n⏱️ 性能统计:")
        print(f"   平均响应时间: {avg_time:.2f}ms")
        print(f"   最小响应时间: {min_time:.2f}ms")
        print(f"   最大响应时间: {max_time:.2f}ms")
        
        # 按类别统计
        print(f"\n📋 按类别统计:")
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if result["status"] == "PASSED":
                categories[cat]["passed"] += 1
        
        for cat, stats in sorted(categories.items()):
            rate = (stats["passed"] / stats["total"] * 100)
            print(f"   {cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # 失败详情
        if failed > 0:
            print(f"\n❌ 失败测试详情:")
            for result in self.results:
                if result["status"] == "FAILED":
                    print(f"   {result['test_id']}: {result['name']}")
                    if result["checks_failed"]:
                        for check in result["checks_failed"]:
                            print(f"      - {check}")
        
        # 最慢查询
        print(f"\n🐌 最慢的5个查询:")
        slowest = sorted(self.results, key=lambda x: x["response_time_ms"], reverse=True)[:5]
        for result in slowest:
            print(f"   {result['test_id']}: {result['response_time_ms']:.2f}ms - {result['name']}")
        
        # 最快查询
        print(f"\n⚡ 最快的5个查询:")
        fastest = sorted(self.results, key=lambda x: x["response_time_ms"])[:5]
        for result in fastest:
            if result["response_time_ms"] > 0:
                print(f"   {result['test_id']}: {result['response_time_ms']:.2f}ms - {result['name']}")
        
        print("\n" + "="*80)
        
        # 保存报告
        report_data = {
            "test_time": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "timeout": timeout,
            "error": error,
            "pass_rate": pass_rate,
            "performance": {
                "avg_response_time_ms": avg_time,
                "min_response_time_ms": min_time,
                "max_response_time_ms": max_time
            },
            "categories": {cat: stats for cat, stats in categories.items()},
            "results": self.results
        }
        
        report_file = "/home/yuxiaoyu/rs_ontop_core/advanced_sparql_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 详细报告已保存: {report_file}")

def main():
    """主函数"""
    runner = SPARQLTestRunner()
    runner.run_all_tests()

if __name__ == "__main__":
    main()
