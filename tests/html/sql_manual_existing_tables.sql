-- File: tests/html/sql_manual_existing_tables.sql
-- Purpose: Manual SQL test cases for existing business tables via /sql endpoint
-- Usage example:
--   curl --get --data-urlencode "query=SELECT COUNT(*) FROM employees" http://127.0.0.1:5820/sql

-- 0) Basic connectivity
SELECT 1 AS ping;

-- 1) Row counts by core tables
SELECT 'employees' AS table_name, COUNT(*)::bigint AS row_count FROM employees;
SELECT 'departments' AS table_name, COUNT(*)::bigint AS row_count FROM departments;
SELECT 'positions' AS table_name, COUNT(*)::bigint AS row_count FROM positions;
SELECT 'projects' AS table_name, COUNT(*)::bigint AS row_count FROM projects;
SELECT 'employee_projects' AS table_name, COUNT(*)::bigint AS row_count FROM employee_projects;

-- 2) Sample preview rows
SELECT * FROM departments ORDER BY department_id LIMIT 10;
SELECT * FROM positions ORDER BY position_id LIMIT 10;
SELECT * FROM projects ORDER BY project_id LIMIT 10;
SELECT * FROM employees ORDER BY employee_id LIMIT 10;

-- 3) Multi-table join verification
SELECT
  e.employee_id,
  e.first_name,
  e.last_name,
  d.department_name,
  p.position_name,
  e.salary
FROM employees e
LEFT JOIN departments d ON d.department_id = e.department_id
LEFT JOIN positions p ON p.position_id = e.position_id
ORDER BY e.employee_id
LIMIT 20;

-- 4) Aggregation by department
SELECT
  d.department_name,
  COUNT(*)::bigint AS employee_count,
  ROUND(AVG(e.salary)::numeric, 2) AS avg_salary,
  MAX(e.salary) AS max_salary,
  MIN(e.salary) AS min_salary
FROM employees e
JOIN departments d ON d.department_id = e.department_id
GROUP BY d.department_name
ORDER BY avg_salary DESC;

-- 5) Employee-project relation check
SELECT
  e.employee_id,
  e.first_name,
  e.last_name,
  pr.project_name
FROM employee_projects ep
JOIN employees e ON e.employee_id = ep.employee_id
JOIN projects pr ON pr.project_id = ep.project_id
ORDER BY e.employee_id, pr.project_name
LIMIT 30;

-- 6) Data quality quick checks
SELECT COUNT(*) AS null_department_rows FROM employees WHERE department_id IS NULL;
SELECT COUNT(*) AS null_position_rows FROM employees WHERE position_id IS NULL;
SELECT COUNT(*) AS salary_le_0_rows FROM employees WHERE salary <= 0;

-- 7) Optional write test (execute only if you need DML verification)
-- BEGIN;
-- INSERT INTO departments (department_id, department_name) VALUES (9999, 'TEMP_DEP');
-- SELECT * FROM departments WHERE department_id = 9999;
-- DELETE FROM departments WHERE department_id = 9999;
-- ROLLBACK;
