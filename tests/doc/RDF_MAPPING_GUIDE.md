# RS Ontop Core V2.0 - RDF映射配置指南

## 📋 配置概述

已成功配置完整的RDF映射，将PostgreSQL 7张关系型表映射为RDF三元组，支持SPARQL查询。

## 📁 配置文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| **R2RML映射** | `mapping.r2rml.ttl` | R2RML标准映射文件 |
| **OWL本体** | `ontology.owl` | 领域本体定义(TBox) |
| **配置文件** | `ontop-config.json` | Ontop引擎配置 |
| **Rust模块** | `src/mapping/mod.rs` | 映射加载Rust代码 |

## 🔗 命名空间定义

```turtle
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rr: <http://www.w3.org/ns/r2rml#> .
```

## 📊 数据映射详情

### 1. 员工表 (employees) → ex:Employee

**URI模式**: `http://example.org/employee/{employee_id}`

**属性映射**:
| SQL列 | RDF谓词 | 数据类型 |
|-------|---------|----------|
| employee_id | ex:employee_id | xsd:integer |
| first_name | ex:first_name | xsd:string |
| last_name | ex:last_name | xsd:string |
| email | ex:email | xsd:string |
| phone | ex:phone | xsd:string |
| hire_date | ex:hire_date | xsd:date |
| salary | ex:salary | xsd:decimal |
| status | ex:status | xsd:string |

**关系映射**:
- `ex:department_id` → Department (外键)
- `ex:position_id` → Position (外键)

### 2. 部门表 (departments) → ex:Department

**URI模式**: `http://example.org/department/{department_id}`

### 3. 职位表 (positions) → ex:Position

**URI模式**: `http://example.org/position/{position_id}`

### 4. 薪资表 (salaries) → ex:Salary

**URI模式**: `http://example.org/salary/{salary_id}`

### 5. 考勤表 (attendance) → ex:Attendance

**URI模式**: `http://example.org/attendance/{attendance_id}`

### 6. 项目表 (projects) → ex:Project

**URI模式**: `http://example.org/project/{project_id}`

### 7. 员工项目关联 (employee_projects) → ex:EmployeeProjectAssignment

**URI模式**: `http://example.org/employee_project/{id}`

## 🎯 SPARQL查询示例

### 示例1: 查询所有员工
```sparql
SELECT ?employee_id ?first_name ?last_name ?email
WHERE {
  ?employee ex:employee_id ?employee_id .
  ?employee ex:first_name ?first_name .
  ?employee ex:last_name ?last_name .
  ?employee ex:email ?email .
}
LIMIT 10
```

### 示例2: 部门统计
```sparql
SELECT ?department_name (COUNT(?employee) AS ?emp_count)
WHERE {
  ?employee ex:department_id ?dept .
  ?dept ex:department_name ?department_name .
}
GROUP BY ?department_name
ORDER BY DESC(?emp_count)
```

### 示例3: 高薪资员工
```sparql
SELECT ?first_name ?last_name ?salary ?department_name
WHERE {
  ?employee ex:first_name ?first_name .
  ?employee ex:last_name ?last_name .
  ?employee ex:salary ?salary .
  ?employee ex:department_id ?dept .
  ?dept ex:department_name ?department_name .
  FILTER(?salary > 100000)
}
ORDER BY DESC(?salary)
```

### 示例4: 项目参与度
```sparql
SELECT ?project_name (COUNT(DISTINCT ?employee_id) AS ?team_size)
WHERE {
  ?project ex:project_name ?project_name .
  ?emp_proj ex:project_id ?project .
  ?emp_proj ex:employee_id ?employee_id .
}
GROUP BY ?project_name
```

## 🔧 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    SPARQL Endpoint                      │
│                    (Port 5820)                           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              SPARQL to SQL Translation                    │
│              (R2RML Mapping Engine)                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              RDF Mapping Configuration                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Employee │ │Department│ │ Position │ │  Salary  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │Attendance│ │  Project │ │EmpProject│                │
│  └──────────┘ └──────────┘ └──────────┘                │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 PostgreSQL Database                     │
│              (rs_ontop_core, 7 tables)                  │
│              100,000+ employees, 3M+ records           │
└─────────────────────────────────────────────────────────┘
```

## 🚀 使用步骤

### 1. 确认配置文件存在
```bash
ls -la mapping.r2rml.ttl ontology.owl ontop-config.json
```

### 2. 重启SPARQL服务器
```sql
SELECT ontop_reload_mapping();  -- 重新加载映射
SELECT ontop_start_sparql_server();  -- 启动服务器
```

### 3. 测试SPARQL查询
```bash
curl -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT (COUNT(*) AS ?count) WHERE {?e a ex:Employee}"}'
```

## 📈 数据规模

| 实体类型 | 数量 | URI前缀 |
|---------|------|---------|
| Employees | 100,000 | `http://example.org/employee/` |
| Departments | 100 | `http://example.org/department/` |
| Positions | 1,000 | `http://example.org/position/` |
| Salaries | 100,000 | `http://example.org/salary/` |
| Attendance | 3,000,000 | `http://example.org/attendance/` |
| Projects | 10,000 | `http://example.org/project/` |
| EmpProjects | 200,000 | `http://example.org/employee_project/` |

**总计**: ~3,400,000+ RDF三元组

## 🔍 验证测试

运行验证脚本确认映射正确性：
```bash
python3 sparql_result_validation.py
```

## 📝 注意事项

1. **URI唯一性**: 所有实体使用数据库主键构建URI，确保全局唯一
2. **外键关系**: 自动映射为RDF对象属性，支持SPARQL JOIN查询
3. **数据类型**: 严格遵循XSD数据类型定义
4. **性能优化**: 大表(如attendance)使用分页查询
5. **空值处理**: SQL NULL值映射为OPTIONAL模式

## 🎉 完成状态

✅ **RDF映射配置完成！**
- ✅ R2RML映射文件
- ✅ OWL本体定义
- ✅ 配置文件
- ✅ Rust集成代码
- ✅ 7张表完整映射
- ✅ 3,400,000+ 三元组支持

**现在可以执行SPARQL查询验证结果正确性了！**
