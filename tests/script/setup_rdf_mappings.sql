-- =============================================================================
-- RS Ontop Core V2.0 - RDF 映射表初始化脚本
-- 说明: 创建映射表并插入本体定义和映射规则
-- 日期: 2026-03-28
-- =============================================================================

-- =============================================================================
-- 1. 创建本体快照表 (TBox)
-- =============================================================================
DROP TABLE IF EXISTS ontop_ontology_snapshots CASCADE;

CREATE TABLE ontop_ontology_snapshots (
    id SERIAL PRIMARY KEY,
    ttl_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ontop_ontology_snapshots IS 
    '存储OWL/RDFS本体定义的Turtle格式文本 (TBox层)';

-- =============================================================================
-- 2. 创建映射规则表 (ABox)
-- =============================================================================
DROP TABLE IF EXISTS ontop_mappings CASCADE;

CREATE TABLE ontop_mappings (
    id SERIAL PRIMARY KEY,
    predicate TEXT NOT NULL,
    table_name TEXT NOT NULL,
    subject_template TEXT,
    object_col TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ontop_mappings IS 
    '存储RDF谓词到SQL表的映射规则 (ABox层)';

CREATE INDEX idx_ontop_mappings_predicate ON ontop_mappings(predicate);
CREATE INDEX idx_ontop_mappings_table ON ontop_mappings(table_name);

-- =============================================================================
-- 3. 插入本体定义 (Turtle格式)
-- =============================================================================
INSERT INTO ontop_ontology_snapshots (ttl_content) VALUES (
'@prefix : <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

<http://example.org/ontology>
    rdf:type owl:Ontology ;
    owl:versionIRI <http://example.org/ontology/1.0> ;
    rdfs:label "RS Ontop Core HR Ontology"@en ;
    rdfs:comment "Human Resource Management System Ontology for RS Ontop Core V2.0"@en .

# ============================================
# 类定义 Classes
# ============================================

ex:Department rdf:type owl:Class ;
    rdfs:label "Department"@en ;
    rdfs:comment "An organizational unit within the company"@en .

ex:Position rdf:type owl:Class ;
    rdfs:label "Position"@en ;
    rdfs:comment "A job position within the company"@en .

ex:Employee rdf:type owl:Class ;
    rdfs:label "Employee"@en ;
    rdfs:comment "A person employed by the company"@en .

ex:Salary rdf:type owl:Class ;
    rdfs:label "Salary"@en ;
    rdfs:comment "Salary information for an employee"@en .

ex:Attendance rdf:type owl:Class ;
    rdfs:label "Attendance"@en ;
    rdfs:comment "Attendance record for an employee"@en .

ex:Project rdf:type owl:Class ;
    rdfs:label "Project"@en ;
    rdfs:comment "A project within the company"@en .

ex:EmployeeProjectAssignment rdf:type owl:Class ;
    rdfs:label "Employee Project Assignment"@en ;
    rdfs:comment "Assignment of an employee to a project"@en .

# ============================================
# 数据属性 Data Properties
# ============================================

# Department properties
ex:department_id rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Department ;
    rdfs:range xsd:integer ;
    rdfs:label "department ID"@en .

ex:department_name rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Department ;
    rdfs:range xsd:string ;
    rdfs:label "department name"@en .

ex:location rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Department ;
    rdfs:range xsd:string ;
    rdfs:label "location"@en .

# Position properties
ex:position_id rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Position ;
    rdfs:range xsd:integer ;
    rdfs:label "position ID"@en .

ex:position_title rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Position ;
    rdfs:range xsd:string ;
    rdfs:label "position title"@en .

ex:position_level rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Position ;
    rdfs:range xsd:integer ;
    rdfs:label "position level"@en .

ex:min_salary rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Position ;
    rdfs:range xsd:decimal ;
    rdfs:label "minimum salary"@en .

ex:max_salary rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Position ;
    rdfs:range xsd:decimal ;
    rdfs:label "maximum salary"@en .

# Employee properties
ex:employee_id rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:integer ;
    rdfs:label "employee ID"@en .

ex:first_name rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "first name"@en .

ex:last_name rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "last name"@en .

ex:email rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "email"@en .

ex:phone rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "phone"@en .

ex:hire_date rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:date ;
    rdfs:label "hire date"@en .

ex:salary rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:decimal ;
    rdfs:label "salary"@en .

ex:status rdf:type owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "status"@en .
'
);

-- =============================================================================
-- 4. 插入映射规则 (ABox)
-- =============================================================================

-- employees 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/employee_id', 'employees', 'http://example.org/employee/{employee_id}', 'employee_id'),
('http://example.org/first_name', 'employees', 'http://example.org/employee/{employee_id}', 'first_name'),
('http://example.org/last_name', 'employees', 'http://example.org/employee/{employee_id}', 'last_name'),
('http://example.org/email', 'employees', 'http://example.org/employee/{employee_id}', 'email'),
('http://example.org/phone', 'employees', 'http://example.org/employee/{employee_id}', 'phone'),
('http://example.org/hire_date', 'employees', 'http://example.org/employee/{employee_id}', 'hire_date'),
('http://example.org/salary', 'employees', 'http://example.org/employee/{employee_id}', 'salary'),
('http://example.org/status', 'employees', 'http://example.org/employee/{employee_id}', 'status'),
('http://example.org/department_id', 'employees', 'http://example.org/employee/{employee_id}', 'department_id'),
('http://example.org/position_id', 'employees', 'http://example.org/employee/{employee_id}', 'position_id');

-- departments 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/department_id', 'departments', 'http://example.org/department/{department_id}', 'department_id'),
('http://example.org/department_name', 'departments', 'http://example.org/department/{department_id}', 'department_name'),
('http://example.org/location', 'departments', 'http://example.org/department/{department_id}', 'location'),
('http://example.org/manager_id', 'departments', 'http://example.org/department/{department_id}', 'manager_id');

-- positions 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/position_id', 'positions', 'http://example.org/position/{position_id}', 'position_id'),
('http://example.org/position_title', 'positions', 'http://example.org/position/{position_id}', 'position_title'),
('http://example.org/position_level', 'positions', 'http://example.org/position/{position_id}', 'position_level'),
('http://example.org/min_salary', 'positions', 'http://example.org/position/{position_id}', 'min_salary'),
('http://example.org/max_salary', 'positions', 'http://example.org/position/{position_id}', 'max_salary');

-- salaries 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/salary_id', 'salaries', 'http://example.org/salary/{salary_id}', 'salary_id'),
('http://example.org/base_salary', 'salaries', 'http://example.org/salary/{salary_id}', 'base_salary'),
('http://example.org/bonus', 'salaries', 'http://example.org/salary/{salary_id}', 'bonus'),
('http://example.org/deduction', 'salaries', 'http://example.org/salary/{salary_id}', 'deduction'),
('http://example.org/net_salary', 'salaries', 'http://example.org/salary/{salary_id}', 'net_salary'),
('http://example.org/pay_date', 'salaries', 'http://example.org/salary/{salary_id}', 'pay_date'),
('http://example.org/pay_period', 'salaries', 'http://example.org/salary/{salary_id}', 'pay_period'),
('http://example.org/salary_employee_id', 'salaries', 'http://example.org/salary/{salary_id}', 'employee_id');

-- attendance 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/attendance_id', 'attendance', 'http://example.org/attendance/{attendance_id}', 'attendance_id'),
('http://example.org/work_date', 'attendance', 'http://example.org/attendance/{attendance_id}', 'work_date'),
('http://example.org/check_in', 'attendance', 'http://example.org/attendance/{attendance_id}', 'check_in'),
('http://example.org/check_out', 'attendance', 'http://example.org/attendance/{attendance_id}', 'check_out'),
('http://example.org/work_hours', 'attendance', 'http://example.org/attendance/{attendance_id}', 'work_hours'),
('http://example.org/attendance_status', 'attendance', 'http://example.org/attendance/{attendance_id}', 'status'),
('http://example.org/overtime_hours', 'attendance', 'http://example.org/attendance/{attendance_id}', 'overtime_hours'),
('http://example.org/attendance_employee_id', 'attendance', 'http://example.org/attendance/{attendance_id}', 'employee_id');

-- projects 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/project_id', 'projects', 'http://example.org/project/{project_id}', 'project_id'),
('http://example.org/project_name', 'projects', 'http://example.org/project/{project_id}', 'project_name'),
('http://example.org/project_description', 'projects', 'http://example.org/project/{project_id}', 'project_description'),
('http://example.org/budget', 'projects', 'http://example.org/project/{project_id}', 'budget'),
('http://example.org/project_status', 'projects', 'http://example.org/project/{project_id}', 'status'),
('http://example.org/start_date', 'projects', 'http://example.org/project/{project_id}', 'start_date'),
('http://example.org/end_date', 'projects', 'http://example.org/project/{project_id}', 'end_date');

-- employee_projects 表映射
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/assignment_id', 'employee_projects', 'http://example.org/employee_project/{id}', 'id'),
('http://example.org/role', 'employee_projects', 'http://example.org/employee_project/{id}', 'role'),
('http://example.org/hours_worked', 'employee_projects', 'http://example.org/employee_project/{id}', 'hours_worked'),
('http://example.org/assigned_date', 'employee_projects', 'http://example.org/employee_project/{id}', 'assigned_date'),
('http://example.org/ep_employee_id', 'employee_projects', 'http://example.org/employee_project/{id}', 'employee_id'),
('http://example.org/ep_project_id', 'employee_projects', 'http://example.org/employee_project/{id}', 'project_id');

-- =============================================================================
-- 5. 验证插入结果
-- =============================================================================
SELECT 'ontop_ontology_snapshots 记录数:' AS info, COUNT(*) AS count FROM ontop_ontology_snapshots
UNION ALL
SELECT 'ontop_mappings 记录数:' AS info, COUNT(*) AS count FROM ontop_mappings;

-- 查看映射规则示例
SELECT * FROM ontop_mappings LIMIT 5;
