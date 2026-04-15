#!/usr/bin/env python3
"""
日期时间函数测试 (SPARQL 1.1 Date/Time Functions)
涵盖: now, year, month, day, hours, minutes, seconds, timezone
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from framework import TestCaseBase, run_test_suite


class TestNowFunction(TestCaseBase):
    """当前时间函数 NOW()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?currentTime
        WHERE {
            ?emp ex:first_name ?firstName .
            BIND(NOW() AS ?currentTime)
        }
        LIMIT 5
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", CURRENT_TIMESTAMP AS "currentTime"
        FROM employees
        LIMIT 5
        """


class TestYearFunction(TestCaseBase):
    """年份提取 YEAR()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?hireYear
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:hire_date ?hireDate .
            BIND(YEAR(?hireDate) AS ?hireYear)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", EXTRACT(YEAR FROM hire_date) AS "hireYear"
        FROM employees
        LIMIT 10
        """


class TestMonthFunction(TestCaseBase):
    """月份提取 MONTH()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?hireMonth
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:hire_date ?hireDate .
            BIND(MONTH(?hireDate) AS ?hireMonth)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", EXTRACT(MONTH FROM hire_date) AS "hireMonth"
        FROM employees
        LIMIT 10
        """


class TestDayFunction(TestCaseBase):
    """日期提取 DAY()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?hireDay
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:hire_date ?hireDate .
            BIND(DAY(?hireDate) AS ?hireDay)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", EXTRACT(DAY FROM hire_date) AS "hireDay"
        FROM employees
        LIMIT 10
        """


class TestHoursFunction(TestCaseBase):
    """小时提取 HOURS()"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?checkInHour
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:check_in_time ?checkIn .
            BIND(HOURS(?checkIn) AS ?checkInHour)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT e.first_name AS "firstName", EXTRACT(HOUR FROM a.check_in) AS "checkInHour"
        FROM employees e
        JOIN attendance a ON e.employee_id = a.employee_id
        LIMIT 10
        """


class TestDateDiff(TestCaseBase):
    """日期差计算 - 计算工龄"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?yearsOfService
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:hire_date ?hireDate .
            BIND((YEAR(NOW()) - YEAR(?hireDate)) AS ?yearsOfService)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName",
               (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM hire_date)) AS "yearsOfService"
        FROM employees
        LIMIT 10
        """


class TestDateComparison(TestCaseBase):
    """日期比较 - 查询2020年前入职的员工"""
    
    def sparql_query(self) -> str:
        return """
        PREFIX ex: <http://example.org/>
        SELECT ?firstName ?hireDate
        WHERE {
            ?emp ex:first_name ?firstName ;
                 ex:hire_date ?hireDate .
            FILTER(YEAR(?hireDate) < 2020)
        }
        LIMIT 10
        """
    
    def baseline_sql(self) -> str:
        return """
        SELECT first_name AS "firstName", hire_date AS "hireDate"
        FROM employees
        WHERE EXTRACT(YEAR FROM hire_date) < 2020
        LIMIT 10
        """


if __name__ == "__main__":
    test_cases = [
        TestNowFunction(),
        TestYearFunction(),
        TestMonthFunction(),
        TestDayFunction(),
        TestHoursFunction(),
        TestDateDiff(),
        TestDateComparison(),
    ]
    
    results = run_test_suite(test_cases, output_file="test_datetime_functions_results.json")
    sys.exit(0 if all(r["passed"] for r in results) else 1)
