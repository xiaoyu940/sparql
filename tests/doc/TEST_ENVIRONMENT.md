# RS Ontop Core V2.0 - 测试环境文档

## 📋 文档信息

- **文档版本**: 1.0
- **创建日期**: 2026-03-28
- **适用系统**: RS Ontop Core V2.0
- **测试环境**: PostgreSQL + SPARQL Endpoint

---

## 🎯 测试环境概述

### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    测试环境架构                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   SPARQL     │      │   SPARQL     │                │
│  │   Client     │──────│   Endpoint   │                │
│  │  (测试脚本)   │      │  (Port 5820) │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                        │
│                       ┌────────┴────────┐               │
│                       │  Ontop Engine   │               │
│                       │  (Rust/pgrx)   │               │
│                       └────────┬────────┘               │
│                                │                        │
│                       ┌────────┴────────┐               │
│                       │   PostgreSQL    │               │
│                       │  (rs_ontop_core)│               │
│                       └─────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🗄️ 数据库环境

### PostgreSQL 配置

| 配置项 | 值 |
|--------|-----|
| **数据库名** | rs_ontop_core |
| **主机** | localhost |
| **端口** | 5432 |
| **用户名** | yuxiaoyu |
| **密码** | (空) |

### 数据库表结构 (7张表)

| 表名 | 记录数 | 说明 |
|------|--------|------|
| **employees** | 100,000 | 员工基本信息 |
| **departments** | 100 | 部门信息 |
| **positions** | 1,000 | 职位信息 |
| **salaries** | 100,000 | 薪资记录 |
| **attendance** | 3,000,000 | 考勤记录 |
| **projects** | 10,000 | 项目信息 |
| **employee_projects** | 200,000 | 员工项目关联 |

**总记录数**: ~3,400,000+ 条

### 表字段定义详情

#### 1. employees (员工表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| employee_id | SERIAL | PRIMARY KEY | 员工唯一标识 |
| first_name | VARCHAR(50) | NOT NULL | 名 |
| last_name | VARCHAR(50) | NOT NULL | 姓 |
| email | VARCHAR(100) | UNIQUE | 邮箱 |
| phone | VARCHAR(20) | - | 电话 |
| hire_date | DATE | DEFAULT CURRENT_DATE | 入职日期 |
| department_id | INTEGER | FOREIGN KEY → departments | 所属部门ID |
| position_id | INTEGER | FOREIGN KEY → positions | 职位ID |
| salary | DECIMAL(10,2) | - | 年薪 |
| status | VARCHAR(20) | DEFAULT 'Active' | 员工状态 |

#### 2. departments (部门表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| department_id | SERIAL | PRIMARY KEY | 部门唯一标识 |
| department_name | VARCHAR(100) | NOT NULL | 部门名称 |
| location | VARCHAR(100) | - | 办公地点 |
| manager_id | INTEGER | FOREIGN KEY → employees | 部门经理ID |

#### 3. positions (职位表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| position_id | SERIAL | PRIMARY KEY | 职位唯一标识 |
| position_title | VARCHAR(100) | NOT NULL | 职位名称 |
| position_level | INTEGER | CHECK 1-10 | 职级 |
| min_salary | DECIMAL(10,2) | - | 最低薪资 |
| max_salary | DECIMAL(10,2) | - | 最高薪资 |

#### 4. salaries (薪资记录表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| salary_id | SERIAL | PRIMARY KEY | 记录唯一标识 |
| employee_id | INTEGER | FOREIGN KEY → employees, NOT NULL | 员工ID |
| base_salary | DECIMAL(10,2) | NOT NULL | 基本工资 |
| bonus | DECIMAL(10,2) | DEFAULT 0 | 奖金 |
| deduction | DECIMAL(10,2) | DEFAULT 0 | 扣除 |
| net_salary | DECIMAL(10,2) | - | 净收入 |
| pay_date | DATE | DEFAULT CURRENT_DATE | 发放日期 |
| pay_period | VARCHAR(20) | DEFAULT 'Monthly' | 发放周期 |

#### 5. attendance (考勤记录表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| attendance_id | SERIAL | PRIMARY KEY | 记录唯一标识 |
| employee_id | INTEGER | FOREIGN KEY → employees, NOT NULL | 员工ID |
| work_date | DATE | DEFAULT CURRENT_DATE | 工作日期 |
| check_in | TIME | - | 签到时间 |
| check_out | TIME | - | 签退时间 |
| work_hours | DECIMAL(4,2) | - | 工作时长 |
| status | VARCHAR(20) | DEFAULT 'Present' | 考勤状态 |
| overtime_hours | DECIMAL(4,2) | DEFAULT 0 | 加班时长 |

#### 6. projects (项目表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| project_id | SERIAL | PRIMARY KEY | 项目唯一标识 |
| project_name | VARCHAR(200) | NOT NULL | 项目名称 |
| project_description | TEXT | - | 项目描述 |
| start_date | DATE | - | 开始日期 |
| end_date | DATE | - | 结束日期 |
| budget | DECIMAL(15,2) | - | 预算 |
| status | VARCHAR(20) | DEFAULT 'In Progress' | 项目状态 |

#### 7. employee_projects (员工项目关联表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PRIMARY KEY | 记录唯一标识 |
| employee_id | INTEGER | FOREIGN KEY → employees, NOT NULL | 员工ID |
| project_id | INTEGER | FOREIGN KEY → projects, NOT NULL | 项目ID |
| role | VARCHAR(100) | - | 项目角色 |
| hours_worked | DECIMAL(8,2) | DEFAULT 0 | 工作时长 |
| assigned_date | DATE | DEFAULT CURRENT_DATE | 分配日期 |

---

### 端点配置

| 配置项 | 值 |
|--------|-----|
| **端点URL** | http://localhost:5820/sparql |
| **HTTP方法** | POST |
| **Content-Type** | application/json |
| **请求格式** | `{"query": "SPARQL_QUERY"}` |
| **响应格式** | SPARQL 1.1 Query Results JSON |

### 响应格式示例

```json
{
  "head": {
    "vars": ["variable1", "variable2"]
  },
  "results": {
    "bindings": [
      {
        "variable1": {
          "type": "literal",
          "value": "data1"
        },
        "variable2": {
          "type": "uri",
          "value": "http://example.org/resource"
        }
      }
    ]
  }
}
```

---

## 🧪 测试工具清单

### 1. 基础测试脚本

| 脚本名称 | 功能 | 位置 |
|----------|------|------|
| `sparql_test_suite.py` | 13个SPARQL测试用例 | 项目根目录 |
| `advanced_sparql_test_suite_50.py` | 50个复杂测试用例 | 项目根目录 |
| `sparql_result_validation.py` | SQL/SPARQL结果对比验证 | 项目根目录 |

### 2. 辅助脚本

| 脚本名称 | 功能 |
|----------|------|
| `quick_test.sh` | 快速环境检查 |
| `generate_100k_data.sql` | 100K测试数据生成 |

### 3. 配置文件

| 文件名称 | 说明 |
|----------|------|
| `mapping.r2rml.ttl` | R2RML RDF映射文件 |
| `ontology.owl` | OWL本体定义 |
| `ontop-config.json` | Ontop引擎配置 |

---

## 📊 测试数据集详情

### 数据生成规则

#### employees 表 (100,000条)
- `employee_id`: 1-100000 (自增)
- `first_name`: First1, First2, ... First100000
- `last_name`: Last1, Last2, ... Last100000
- `email`: employee{id}@company.com
- `phone`: 555-{0001-9999}
- `hire_date`: 当前日期 - (0-3650)天
- `department_id`: 1-100 (循环分配)
- `position_id`: 1-1000 (循环分配)
- `salary`: 50000-250000
- `status`: Active/On Leave/Terminated (按权重)

#### departments 表 (100条)
- `department_id`: 1-100
- `department_name`: Department_1 到 Department_100
- `location`: Building A/B/C/D/Remote (循环)

#### positions 表 (1,000条)
- `position_id`: 1-1000
- `position_title`: Position_1 到 Position_1000
- `position_level`: 1-10 (循环)
- `min_salary`: 30000-120000
- `max_salary`: 80000-380000

#### salaries 表 (100,000条)
- 每个员工一条记录
- `base_salary`: 5000-20000
- `bonus`: 0-2500
- `deduction`: 0-500
- `net_salary`: base + bonus - deduction

#### attendance 表 (3,000,000条)
- 每个员工最近30天记录
- `work_hours`: 6.0-10.0
- `overtime_hours`: 0.0-2.5
- `status`: Present/Late/Absent/Half Day (加权)

#### projects 表 (10,000条)
- `project_name`: Project_1 到 Project_10000
- `budget`: 100000-1000000
- `status`: Planning/In Progress/Completed (加权)

#### employee_projects 表 (200,000条)
- 每个员工平均2个项目
- `hours_worked`: 0-2000
- `role`: Developer/Manager/Analyst/Designer/Tester/Consultant (循环)

---

## 🔧 环境启动步骤

### 1. 启动 PostgreSQL

```bash
# 确保PostgreSQL服务运行
sudo systemctl status postgresql

# 连接数据库
psql -U yuxiaoyu -d rs_ontop_core
```

### 2. 安装 PostgreSQL 扩展

```sql
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS rs_ontop_core;

-- 验证安装
SELECT * FROM pg_extension WHERE extname = 'rs_ontop_core';
```

### 3. 启动 SPARQL 服务器

```sql
-- 启动SPARQL端点
SELECT ontop_start_sparql_server();

-- 预期输出: (空，表示成功)
```

### 4. 验证端点可用性

```bash
# 检查端点
curl http://localhost:5820/

# 测试SPARQL查询
curl -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * WHERE {?s ?p ?o} LIMIT 1"}'
```

---

## 📈 性能基准

### 预期性能指标

| 操作类型 | 预期响应时间 | 备注 |
|----------|-------------|------|
| 简单查询 (1-10行) | < 10ms | 单表查询 |
| 聚合查询 | 10-50ms | COUNT/SUM/AVG |
| 多表JOIN (3表) | 50-200ms | 部门+员工+职位 |
| 大数据量 (1000行) | 100-500ms | LIMIT 1000 |
| 复杂聚合+分组 | 200-1000ms | GROUP BY + ORDER |

### 实际测试结果

| 指标 | 实测值 | 状态 |
|------|--------|------|
| HTTP响应时间 | 1-3ms | ✅ 正常 |
| HTTP状态码 | 200 | ✅ 正常 |
| 连接稳定性 | 100% | ✅ 正常 |
| SPARQL结果 | 空 | ⚠️ 待修复 |

---

## 🔍 常见问题排查

### 问题1: 数据库连接失败

**症状**: `psql: connection refused`

**解决**:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 问题2: 扩展不存在

**症状**: `extension "rs_ontop_core" does not exist`

**解决**:
```sql
-- 重新安装扩展
DROP EXTENSION IF EXISTS rs_ontop_core;
CREATE EXTENSION rs_ontop_core;
```

### 问题3: SPARQL端点无响应

**症状**: `curl: (7) Failed to connect`

**解决**:
```sql
-- 检查后端工作器状态
SELECT * FROM pg_stat_activity WHERE application_name LIKE '%ontop%';

-- 重启SPARQL服务器
SELECT ontop_start_sparql_server();
```

### 问题4: SPARQL返回空结果

**症状**: `{"results":{"bindings":[]}}`

**原因**: RDF映射未加载到SPARQL服务器

**解决**: 需要代码实现R2RML映射加载功能

---

## 📝 测试执行命令

### 快速测试

```bash
# 执行所有基础测试
python3 sparql_test_suite.py

# 执行高级测试
python3 advanced_sparql_test_suite_50.py

# 执行结果验证
python3 sparql_result_validation.py
```

### 手动测试

```bash
# 员工计数测试
curl -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT (COUNT(*) AS ?c) WHERE {?e a ex:Employee}"}'

# 部门统计测试
curl -X POST http://localhost:5820/sparql \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT ?dept (COUNT(*) AS ?c) WHERE {?e ex:department_id ?dept} GROUP BY ?dept"}'
```

---

## 📋 检查清单

### 环境准备检查表

- [ ] PostgreSQL 服务运行中
- [ ] 数据库 `rs_ontop_core` 存在
- [ ] 7张数据表已创建
- [ ] 测试数据已加载 (100K employees)
- [ ] PostgreSQL扩展 `rs_ontop_core` 已安装
- [ ] SPARQL 服务器已启动 (Port 5820)
- [ ] 端点响应正常 (HTTP 200)

### 测试前检查

- [ ] 检查数据库连接: `psql -U yuxiaoyu -d rs_ontop_core -c "SELECT 1"`
- [ ] 检查表数据: `SELECT COUNT(*) FROM employees;`
- [ ] 检查端点: `curl http://localhost:5820/`
- [ ] 检查测试脚本: `python3 --version`

---

## 📞 联系方式

- **文档维护**: RS Ontop Core Team
- **最后更新**: 2026-03-28
- **问题反馈**: GitHub Issues

---

## 📚 相关文档

- `RDF_MAPPING_GUIDE.md` - RDF映射配置指南

---

**文档结束**
