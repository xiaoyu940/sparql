#!/usr/bin/env python3
"""
UNION 和高级特性测试 (SPARQL 1.1/1.2)
涵盖: UNION, VALUES, MINUS, IN/NOT IN, COALESCE, 条件表达式
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestUnionTwoPatterns(TestCaseBase):
    """UNION：查询Engineering或Sales部门的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?deptName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept .
            ?dept ex:department_name ?deptName .
            {
                FILTER(?deptName = "Engineering")
            }
            UNION
            {
                FILTER(?deptName = "Sales")
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               d.department_name AS "deptName"
        FROM employees e
        JOIN departments d ON e.department_id = d.department_id
        WHERE d.department_name IN ('Engineering', 'Sales')
        LIMIT 10
        """


class TestValuesBlock(TestCaseBase):
    """VALUES：内联数据 - 查询特定部门ID的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?dept
        WHERE {
            VALUES ?dept { 1 2 3 }
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:department_id ?dept .
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName", department_id AS "dept"
        FROM employees
        WHERE department_id IN (1, 2, 3)
        LIMIT 10
        """


class TestInFilter(TestCaseBase):
    """IN 过滤器：查询特定职位的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?positionTitle
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:position_id ?pos .
            ?pos ex:position_title ?positionTitle .
            FILTER(?positionTitle IN ("Software Engineer", "Senior Engineer", "Tech Lead"))
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName",
               p.position_title AS "positionTitle"
        FROM employees e
        JOIN positions p ON e.position_id = p.position_id
        WHERE p.position_title IN ('Software Engineer', 'Senior Engineer', 'Tech Lead')
        LIMIT 10
        """


class TestCoalesce(TestCaseBase):
    """COALESCE：处理NULL值 - 员工电话或邮箱"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?contact
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            OPTIONAL { ?emp ex:phone ?phone }
            OPTIONAL { ?emp ex:email ?email }
            BIND(COALESCE(?phone, ?email, "N/A") AS ?contact)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName",
               COALESCE(phone, email, 'N/A') AS "contact"
        FROM employees
        LIMIT 10
        """


class TestIfExpression(TestCaseBase):
    """IF条件表达式：根据薪资等级分类"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName ?salaryLevel
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName ;
                 ex:salary ?salary .
            BIND(IF(?salary > 100000, "High", IF(?salary > 60000, "Medium", "Low")) AS ?salaryLevel)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", last_name AS "lastName",
               CASE 
                   WHEN salary > 100000 THEN 'High'
                   WHEN salary > 60000 THEN 'Medium'
                   ELSE 'Low'
               END AS "salaryLevel"
        FROM employees
        LIMIT 10
        """


class TestMinusPattern(TestCaseBase):
    """MINUS：排除特定模式 - 查询有薪资记录但没有项目的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            ?emp ex:salary_record ?sal .
            MINUS {
                ?emp ex:assigned_to ?assignment .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", e.last_name AS "lastName"
        FROM employees e
        WHERE EXISTS (SELECT 1 FROM salaries s WHERE s.employee_id = e.employee_id)
          AND NOT EXISTS (SELECT 1 FROM employee_projects ep WHERE ep.employee_id = e.employee_id)
        LIMIT 10
        """


class TestServicePattern(TestCaseBase):
    """SERVICE：跨数据源查询（模拟）"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?lastName
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:last_name ?lastName .
            SERVICE <http://example.org/employee-info> {
                ?emp ex:status "Active" .
            }
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        # SERVICE 在本地测试中简化为普通查询
        return """
        SELECT first_name AS "firstName", last_name AS "lastName"
        FROM employees
        WHERE status = 'Active'
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestUnionTwoPatterns(),
        TestValuesBlock(),
        TestInFilter(),
        TestCoalesce(),
        TestIfExpression(),
        TestMinusPattern(),
        TestServicePattern(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_union_advanced_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
