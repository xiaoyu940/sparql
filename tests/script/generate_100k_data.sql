-- 生成100000条测试数据脚本
-- 作者: RS Ontop Core
-- 日期: 2026-03-28

-- 首先清空现有数据（保留表结构）
TRUNCATE TABLE employee_projects, salaries, attendance, employees, projects, positions, departments RESTART IDENTITY CASCADE;

-- 1. 生成100个部门
INSERT INTO departments (department_name, location, manager_id)
SELECT 
    'Department_' || i,
    CASE (i % 5)
        WHEN 0 THEN 'Building A'
        WHEN 1 THEN 'Building B'
        WHEN 2 THEN 'Building C'
        WHEN 3 THEN 'Building D'
        ELSE 'Remote'
    END,
    NULL
FROM generate_series(1, 100) AS i;

-- 2. 生成1000个职位
INSERT INTO positions (position_title, position_level, min_salary, max_salary)
SELECT 
    'Position_' || i,
    (i % 10) + 1,
    30000 + (i % 20) * 5000,
    80000 + (i % 30) * 10000
FROM generate_series(1, 1000) AS i;

-- 3. 生成100000个员工（核心）
INSERT INTO employees (first_name, last_name, email, phone, hire_date, department_id, position_id, salary, status)
SELECT 
    'First' || i,
    'Last' || i,
    'employee' || i || '@company.com',
    '555-' || LPAD((i % 10000)::text, 4, '0'),
    CURRENT_DATE - (i % 3650) * INTERVAL '1 day',
    (i % 100) + 1,
    (i % 1000) + 1,
    50000 + (i % 200) * 1000,
    CASE (i % 5)
        WHEN 0 THEN 'Active'
        WHEN 1 THEN 'Active'
        WHEN 2 THEN 'On Leave'
        WHEN 3 THEN 'Active'
        ELSE 'Terminated'
    END
FROM generate_series(1, 100000) AS i;

-- 4. 生成100000条薪资记录（每个员工一条）
INSERT INTO salaries (employee_id, base_salary, bonus, deduction, net_salary, pay_date)
SELECT 
    i,
    5000 + (i % 150) * 100,
    (i % 50) * 50,
    (i % 20) * 25,
    5000 + (i % 150) * 100 + (i % 50) * 50 - (i % 20) * 25,
    CURRENT_DATE - (i % 12) * INTERVAL '1 month'
FROM generate_series(1, 100000) AS i;

-- 5. 生成100000条考勤记录（每个员工最近30天的记录）
INSERT INTO attendance (employee_id, work_date, check_in, check_out, work_hours, status, overtime_hours)
SELECT 
    ((i - 1) / 30) + 1,
    CURRENT_DATE - ((i - 1) % 30) * INTERVAL '1 day',
    '08:00:00'::time + (i % 120) * INTERVAL '1 minute',
    '17:00:00'::time + (i % 180) * INTERVAL '1 minute',
    8.0 + (i % 4) * 0.5,
    CASE (i % 10)
        WHEN 0 THEN 'Present'
        WHEN 1 THEN 'Present'
        WHEN 2 THEN 'Present'
        WHEN 3 THEN 'Late'
        WHEN 4 THEN 'Present'
        WHEN 5 THEN 'Present'
        WHEN 6 THEN 'Absent'
        WHEN 7 THEN 'Present'
        WHEN 8 THEN 'Present'
        ELSE 'Half Day'
    END,
    (i % 5) * 0.5
FROM generate_series(1, 3000000) AS i;

-- 6. 生成10000个项目
INSERT INTO projects (project_name, project_description, start_date, end_date, budget, status)
SELECT 
    'Project_' || i,
    'Description for project number ' || i || ' with detailed requirements and specifications.',
    CURRENT_DATE - (i % 730) * INTERVAL '1 day',
    CURRENT_DATE + (i % 365) * INTERVAL '1 day',
    100000 + (i % 900000),
    CASE (i % 4)
        WHEN 0 THEN 'Planning'
        WHEN 1 THEN 'In Progress'
        WHEN 2 THEN 'In Progress'
        ELSE 'Completed'
    END
FROM generate_series(1, 10000) AS i;

-- 7. 生成200000条员工项目关联（每个员工平均参与2个项目）
INSERT INTO employee_projects (employee_id, project_id, role, hours_worked, assigned_date)
SELECT 
    ((i - 1) / 2) + 1,
    ((i - 1) % 10000) + 1,
    CASE (i % 6)
        WHEN 0 THEN 'Developer'
        WHEN 1 THEN 'Manager'
        WHEN 2 THEN 'Analyst'
        WHEN 3 THEN 'Designer'
        WHEN 4 THEN 'Tester'
        ELSE 'Consultant'
    END,
    (i % 200) * 10,
    CURRENT_DATE - (i % 365) * INTERVAL '1 day'
FROM generate_series(1, 200000) AS i;

-- 更新部门经理（随机分配）
UPDATE departments 
SET manager_id = (SELECT employee_id FROM employees WHERE department_id = departments.department_id LIMIT 1);

-- 验证数据
SELECT 'departments' as table_name, COUNT(*) as count FROM departments
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'salaries', COUNT(*) FROM salaries
UNION ALL SELECT 'attendance', COUNT(*) FROM attendance
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'employee_projects', COUNT(*) FROM employee_projects;
