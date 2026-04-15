# RS Ontop Core V2.0 - RDF映射架构文档

## 📋 文档信息

- **文档版本**: 1.0
- **创建日期**: 2026-03-28
- **适用系统**: RS Ontop Core V2.0
- **相关源码**: `src/lib.rs`, `src/mapping.rs`

---

## 🎯 架构概述

RS Ontop Core 的 RDF 映射系统采用**数据库表存储**方式，而非文件系统。

所有 OWL 本体定义和 R2RML 映射规则都存储在 PostgreSQL 的专用表中，
由后端工作器在启动时加载到内存的 `MappingStore` 结构中。

```
┌─────────────────────────────────────────────────────────────────┐
│                     MappingStore (内存)                         │
├─────────────────────────────────────────────────────────────────┤
│  classes:       { "ex:Employee" → OntologyClass }                │
│  properties:    { "ex:first_name" → OntologyProperty }         │
│  mappings:      { "ex:employee_id" → MappingRule }             │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌────────────────────┐          ┌────────────────────┐
│   TBox (本体层)     │          │   ABox (映射层)     │
│  ontop_ontology_   │          │  ontop_mappings    │
│  snapshots         │          │                    │
└────────────────────┘          └────────────────────┘
```

---

## 🗄️ 数据库表结构

### 表1: ontop_ontology_snapshots (TBox - 本体定义)

存储 OWL/RDFS 本体定义的 Turtle 格式文本。

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| **id** | SERIAL | PRIMARY KEY | 自增ID |
| **ttl_content** | TEXT | NOT NULL | Turtle格式的本体定义 |

#### 内容格式示例

```turtle
@prefix ex: <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Employee a owl:Class ;
    rdfs:label "Employee" ;
    rdfs:comment "A person employed by the company" .

ex:employee_id a owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:integer ;
    rdfs:label "employee ID" .
```

#### 加载逻辑 (lib.rs:206-214)

```rust
if mapping_table_exists(client, "public.ontop_ontology_snapshots") {
    let turtles = client.select(
        "SELECT ttl_content::text FROM ontop_ontology_snapshots", 
        None, None
    );
    if let Ok(t_rows) = turtles {
        for row in t_rows {
            if let Some(content) = row.get::<String>(1).ok().flatten() {
                let _ = store.load_turtle(&content);
            }
        }
    }
}
```

#### 解析规则 (mapping.rs:81-178)

| Turtle 谓词 | 处理逻辑 | 内存结构 |
|-------------|----------|----------|
| `rdf:type owl:Class` | 创建 OntologyClass | `classes` HashMap |
| `rdf:type owl:ObjectProperty` | 创建 PropertyType::Object | `properties` HashMap |
| `rdf:type owl:DatatypeProperty` | 创建 PropertyType::Datatype | `properties` HashMap |
| `rdfs:subClassOf` | 添加到 parent_classes | OntologyClass |
| `rdfs:label` | 设置 label 字段 | OntologyClass/Property |
| `rdfs:comment` | 设置 comment 字段 | OntologyClass/Property |
| `rdfs:domain` | 设置 domain 字段 | OntologyProperty |
| `rdfs:range` | 设置 range 字段 | OntologyProperty |

---

### 表2: ontop_mappings (ABox - 实例映射)

存储 RDF 谓词到 SQL 表的映射规则。

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| **id** | SERIAL | PRIMARY KEY | 自增ID |
| **predicate** | TEXT | NOT NULL | RDF谓词URI |
| **table_name** | TEXT | NOT NULL | SQL表名 |
| **subject_template** | TEXT | - | 主体URI模板 |
| **object_col** | TEXT | NOT NULL | 对象列名 |

#### 字段对应关系

| 表字段 | MappingRule 字段 | 说明 |
|--------|------------------|------|
| `predicate` | `predicate` | RDF谓词URI |
| `table_name` | `table_name` | 物理表名 |
| `subject_template` | `subject_template` | URI生成模板 |
| `object_col` | `position_to_column[1]` | 第1位置对应列 |

#### 内容格式示例

| predicate | table_name | subject_template | object_col |
|-----------|------------|------------------|------------|
| `http://example.org/employee_id` | `employees` | `http://example.org/employee/{employee_id}` | `employee_id` |
| `http://example.org/first_name` | `employees` | `http://example.org/employee/{employee_id}` | `first_name` |
| `http://example.org/department_name` | `departments` | `http://example.org/department/{department_id}` | `department_name` |

#### 加载逻辑 (lib.rs:219-268)

```rust
if mapping_table_exists(client, "public.ontop_mappings") {
    let mappings = client.select(
        "SELECT predicate::text, table_name::text, subject_template::text, object_col::text 
         FROM ontop_mappings",
        None, None
    );
    if let Ok(m_rows) = mappings {
        for row in m_rows {
            // 提取字段值
            let s_pred = row.get::<String>(1).ok().flatten()?;
            let table = row.get::<String>(2).ok().flatten()?;
            let s_temp = row.get::<String>(3).ok().flatten()?;
            let o_col = row.get::<String>(4).ok().flatten()?;
            
            // 构建 MappingRule
            let mut pos_map = HashMap::new();
            pos_map.insert(1, o_col);
            
            store.insert_mapping(MappingRule {
                predicate: s_pred,
                table_name: table,
                subject_template: Some(s_temp),
                position_to_column: pos_map,
            });
        }
    }
}
```

---

## 🔗 两表关系

### 架构层次

```
┌─────────────────────────────────────────────────────────┐
│                    SPARQL 查询层                        │
│              SELECT ?name WHERE {?e ex:name ?name}       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    MappingStore (内存)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │   TBox (本体层)     │◄───│  ontop_ontology_      │  │
│  │                     │    │  snapshots (表)        │  │
│  │ • 定义有哪些类      │    │                         │  │
│  │ • 定义有哪些属性    │    │ 存储: owl:Class        │  │
│  │ • 定义属性类型      │    │ 存储: owl:DatatypeProp │  │
│  │ • 定义类层次关系    │    │ 存储: rdfs:domain/range│  │
│  │                     │    │                         │  │
│  │ 作用: 语义验证      │    │  作用: 元数据定义      │  │
│  └──────────┬──────────┘    └─────────────────────────┘  │
│             │                                           │
│             │ 引用定义                                  │
│             ▼                                           │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │   ABox (映射层)     │◄───│  ontop_mappings (表)   │  │
│  │                     │    │                         │  │
│  │ • predicate指向TBox │    │ 存储: predicate         │  │
│  │ • table_name指向SQL │    │ 存储: table_name        │  │
│  │ • column指向数据    │    │ 存储: subject_template  │  │
│  │                     │    │ 存储: object_col       │  │
│  │ 作用: 物理映射      │    │  作用: 物理位置        │  │
│  └─────────────────────┘    └─────────────────────────┘  │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    SQL 生成层                            │
│              SELECT first_name FROM employees            │
└─────────────────────────────────────────────────────────┘
```

### 协作流程

**查询: `?employee ex:first_name ?name`**

1. **TBox 验证**
   - 查 `ontop_ontology_snapshots`
   - 确认 `ex:first_name` 是 `owl:DatatypeProperty`
   - 确认 domain 是 `ex:Employee`

2. **ABox 映射**
   - 查 `ontop_mappings`
   - 找到 `predicate = "ex:first_name"` 的行
   - 获取 `table_name = "employees"`, `object_col = "first_name"`

3. **SQL 生成**
   ```sql
   SELECT employee_id, first_name FROM employees
   ```

---

## 📐 MappingRule 数据结构

```rust
/// 映射规则 (src/mapping.rs:47-53)
pub struct MappingRule {
    /// RDF谓词URI (如 "http://example.org/employee_id")
    pub predicate: String,
    
    /// SQL表名 (如 "employees")
    pub table_name: String,
    
    /// 主体URI模板 (如 "http://example.org/employee/{employee_id}")
    pub subject_template: Option<String>,
    
    /// 位置到列的映射 (position_to_column[1] = "employee_id")
    pub position_to_column: HashMap<usize, String>,
}
```

### 字段说明

| 字段 | 类型 | SPARQL中的作用 | SQL中的作用 |
|------|------|----------------|-------------|
| `predicate` | String | 三元组的谓词 | WHERE子句匹配 |
| `table_name` | String | - | FROM表名 |
| `subject_template` | Option<String> | 主体URI生成 | 主键值替换 |
| `position_to_column` | HashMap | 对象变量绑定 | SELECT列名 |

---

## 🔄 查询转换示例

### 完整转换流程

**输入 SPARQL:**
```sparql
SELECT ?first_name ?last_name
WHERE {
  ?employee <http://example.org/employee_id> ?id .
  ?employee <http://example.org/first_name> ?first_name .
  ?employee <http://example.org/last_name> ?last_name .
}
LIMIT 10
```

**系统处理:**

1. **解析 SPARQL** → 提取三元组模式
   - `?employee ex:employee_id ?id`
   - `?employee ex:first_name ?first_name`
   - `?employee ex:last_name ?last_name`

2. **查 ontop_mappings:**
   
   | 三元组 | 查表结果 |
   |--------|----------|
   | `ex:employee_id` | `employees.employee_id` |
   | `ex:first_name` | `employees.first_name` |
   | `ex:last_name` | `employees.last_name` |

3. **生成 SQL:**
   ```sql
   SELECT 
       e.first_name,
       e.last_name
   FROM employees e
   LIMIT 10
   ```

---

## 📝 SQL 建表脚本

### 创建本体表

```sql
CREATE TABLE IF NOT EXISTS ontop_ontology_snapshots (
    id SERIAL PRIMARY KEY,
    ttl_content TEXT NOT NULL
);

COMMENT ON TABLE ontop_ontology_snapshots IS 
    '存储OWL/RDFS本体定义的Turtle格式文本';
```

### 创建映射表

```sql
CREATE TABLE IF NOT EXISTS ontop_mappings (
    id SERIAL PRIMARY KEY,
    predicate TEXT NOT NULL,
    table_name TEXT NOT NULL,
    subject_template TEXT,
    object_col TEXT NOT NULL
);

COMMENT ON TABLE ontop_mappings IS 
    '存储RDF谓词到SQL表的映射规则';

CREATE INDEX idx_ontop_mappings_predicate ON ontop_mappings(predicate);
CREATE INDEX idx_ontop_mappings_table ON ontop_mappings(table_name);
```

---

## 🔧 数据导入示例

### 导入本体定义

```sql
INSERT INTO ontop_ontology_snapshots (ttl_content) VALUES (
'@prefix ex: <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Employee a owl:Class .
ex:Department a owl:Class .

ex:employee_id a owl:DatatypeProperty ;
    rdfs:domain ex:Employee .
    
ex:first_name a owl:DatatypeProperty ;
    rdfs:domain ex:Employee .
'
);
```

### 导入映射规则

```sql
INSERT INTO ontop_mappings (predicate, table_name, subject_template, object_col) VALUES
('http://example.org/employee_id', 'employees', 'http://example.org/employee/{employee_id}', 'employee_id'),
('http://example.org/first_name', 'employees', 'http://example.org/employee/{employee_id}', 'first_name'),
('http://example.org/last_name', 'employees', 'http://example.org/employee/{employee_id}', 'last_name'),
('http://example.org/department_name', 'departments', 'http://example.org/department/{department_id}', 'department_name');
```

---

## 🎯 关键设计决策

### 1. 为什么选择数据库存储？

| 优势 | 说明 |
|------|------|
| **事务性** | 映射变更可以事务管理 |
| **版本控制** | 支持多版本本体快照 |
| **动态加载** | 无需重启即可更新映射 |
| **权限控制** | 利用PostgreSQL权限系统 |
| **备份恢复** | 与业务数据一同备份 |

### 2. 与文件存储对比

| 特性 | 数据库表 | 文件系统 |
|------|----------|----------|
| 热更新 | ✅ 支持 | ❌ 需重启 |
| 版本管理 | ✅ 表内多行 | ❌ 需Git |
| 分布式 | ✅ 数据库同步 | ❌ 需NAS |
| 编辑体验 | ⚠️ SQL操作 | ✅ 文本编辑器 |

### 3. 扩展性考虑

```rust
// 未来可扩展字段
pub struct MappingRule {
    // ... 现有字段
    
    // 可选: 支持多列对象
    // position_to_column: HashMap<usize, String>,  // 已支持
    
    // 可选: SQL条件过滤
    // filter_condition: Option<String>,
    
    // 可选: 常量绑定
    // constant_bindings: HashMap<String, String>,
}
```

---

## 📚 相关源码文件

| 文件 | 职责 |
|------|------|
| `src/lib.rs` | 加载逻辑 `fetch_ontop_mappings_with_client` |
| `src/mapping.rs` | 内存结构 `MappingStore`, `MappingRule` |
| `src/mapping/manager_v2.rs` | 映射管理 `MappingManagerV2` |
| `src/rewriter/mapping_unfolder.rs` | 映射展开逻辑 |
| `src/ir/builder.rs` | IR构建时使用映射 |

---

## 🔍 故障排查

### 问题: SPARQL返回空结果

**检查步骤:**

1. **确认表存在:**
   ```sql
   SELECT * FROM ontop_ontology_snapshots;
   SELECT * FROM ontop_mappings;
   ```

2. **确认数据已加载:**
   ```sql
   SELECT COUNT(*) FROM ontop_mappings;
   ```

3. **重启SPARQL服务器:**
   ```sql
   SELECT ontop_start_sparql_server();
   ```

4. **查看日志:**
   ```
   rs-ontop-core: ontop_ontology_snapshots table not found
   rs-ontop-core: ontop_mappings table not found
   ```

---

**文档结束**
