# Sprint 9 P0 设计文档：Property Path 扩展与 OBDA SQL 生成

> **文档版本**: 1.0  
> **创建日期**: 2026-04-02  
> **阶段**: P0 (最高优先级)  
> **目标**: 实现 Property Path 在 OBDA 架构下的 SQL 生成

---

## 1. 概述

### 1.1 背景与问题

当前系统已实现 Property Path 的解析和 IR 表示，但 SQL 生成器 (`path_sql_generator.rs`) 基于 **RDF 三元组表** 模型（使用 `rdf_triples` 表），而非 **OBDA 虚拟知识图谱** 模型。

**当前实现（RDF 模型）**:
```sql
-- 生成针对 rdf_triples 表的递归 CTE
WITH RECURSIVE path_cte AS (
  SELECT DISTINCT ?s AS start_node, o AS end_node, 1 AS depth 
  FROM rdf_triples 
  WHERE p = 'foaf:knows' AND s = ?s
  UNION ALL
  SELECT t.start_node, r.o AS end_node, t.depth + 1 
  FROM path_cte t 
  JOIN rdf_triples r ON t.end_node = r.s 
  WHERE r.p = 'foaf:knows' AND t.depth < 10
)
```

**目标实现（OBDA 模型）**:
```sql
-- 生成针对关系表的 JOIN / UNION
-- 反向路径 ^:knows
SELECT t0.employee_id, t1.employee_id AS colleague_id
FROM employees t0
JOIN employees t1 ON t0.manager_id = t1.employee_id

-- 序列路径 :worksIn/:locatedIn
SELECT t0.employee_id, t2.country_name
FROM employees t0
JOIN departments t1 ON t0.department_id = t1.department_id
JOIN locations t2 ON t1.location_id = t2.location_id

-- 选择路径 :email\|:phone
SELECT employee_id, email AS contact FROM employees
UNION
SELECT employee_id, phone AS contact FROM employees
```

### 1.2 Sprint 9 P0 范围

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 反向路径 (`^p`) | P0-1 | 交换 subject/object，生成反向 JOIN |
| 序列路径 (`p1/p2`) | P0-2 | 多表 JOIN 链生成 |
| 选择路径 (`p1\|p2`) | P0-3 | UNION 查询生成 |

---

## 2. 架构设计

### 2.1 核心挑战

Property Path 在 OBDA 架构下的核心挑战是：**路径表达的是跨多个映射的关系，需要展开为关系代数中的 JOIN/UNION 操作**。

```
SPARQL: ?emp :manager/:manager ?grandManager
        
映射关系:
- :manager → employees.manager_id = employees.employee_id (自连接)
        
展开逻辑:
1. 第一个 :manager 从 employees 表获取经理 ID
2. 第二个 :manager 从 employees 表获取经理的经理
3. 需要两个表别名 + JOIN 条件
```

### 2.2 设计决策

**决策 1: 路径展开时机**
- **选择**: 在 Unfolding Pass 中展开，而非 SQL 生成阶段
- **原因**: 
  - 路径展开会产生多个 ExtensionalData 节点，可被优化器处理
  - 与现有架构一致（Intensional → Extensional）
  - 支持后续的自连接消除等优化

**决策 2: 别名管理策略**
- **方案**: 路径中的每个步骤分配独立表别名
- **命名规则**: `{table_name}_path{step_idx}_{path_id}`
- **示例**: `employees_path0_1`, `departments_path1_1`

**决策 3: 复杂路径处理**
- **序列路径**: 展开为 N 元 Join 节点
- **选择路径**: 展开为 Union 节点
- **反向路径**: 交换列映射后正常展开

---

## 3. 模块设计

### 3.1 路径展开模块 `src/rewriter/path_unfolder.rs`

**职责**: 将 `LogicNode::Path` 展开为 `Join` / `Union` / `ExtensionalData` 的组合

```rust
/// 路径展开器
pub struct PathUnfolder<'a> {
    mapping_store: &'a MappingStore,
    metadata_cache: &'a HashMap<String, Arc<TableMetadata>>,
    alias_counter: usize,
}

impl<'a> PathUnfolder<'a> {
    /// 展开 Path 节点为关系代数表达式
    pub fn unfold_path(
        &mut self,
        subject: &Term,
        path: &PropertyPath,
        object: &Term,
    ) -> Result<LogicNode, UnfoldError> {
        match path {
            PropertyPath::Inverse(inner) => self.unfold_inverse(subject, inner, object),
            PropertyPath::Sequence(seq) => self.unfold_sequence(subject, seq, object),
            PropertyPath::Alternative(alts) => self.unfold_alternative(subject, alts, object),
            PropertyPath::Predicate(pred) => self.unfold_predicate(subject, pred, object),
            _ => Err(UnfoldError::UnsupportedPath(format!("{:?}", path))),
        }
    }
}
```

**关键算法 - 序列路径展开**:
```rust
fn unfold_sequence(
    &mut self,
    subject: &Term,
    seq: &[PropertyPath],
    object: &Term,
) -> Result<LogicNode, UnfoldError> {
    if seq.is_empty() {
        return Err(UnfoldError::EmptyPath);
    }
    
    // 1. 展开第一个谓词，创建基础扫描
    let first_path = &seq[0];
    let first_var = self.generate_intermediate_var(0);
    let mut current_node = self.unfold_path(subject, first_path, &first_var)?;
    
    // 2. 依次展开后续谓词，创建 Join 链
    let mut last_var = first_var;
    
    for (idx, path) in seq[1..].iter().enumerate() {
        let next_var = if idx == seq.len() - 2 {
            // 最后一个路径使用原始 object
            object.clone()
        } else {
            self.generate_intermediate_var(idx + 1)
        };
        
        // 展开当前路径段
        let next_node = self.unfold_path(&last_var, path, &next_var)?;
        
        // 创建 Join 节点
        current_node = LogicNode::Join {
            children: vec![current_node, next_node],
            condition: None, // 条件通过列映射隐含
            join_type: JoinType::Inner,
        };
        
        last_var = next_var;
    }
    
    Ok(current_node)
}
```

**关键算法 - 反向路径展开**:
```rust
fn unfold_inverse(
    &mut self,
    subject: &Term,
    inner: &PropertyPath,
    object: &Term,
) -> Result<LogicNode, UnfoldError> {
    // 反向路径：交换 subject 和 object
    // ?a ^:knows ?b  等价于 ?b :knows ?a
    self.unfold_path(object, inner, subject)
}
```

**关键算法 - 选择路径展开**:
```rust
fn unfold_alternative(
    &mut self,
    subject: &Term,
    alts: &[PropertyPath],
    object: &Term,
) -> Result<LogicNode, UnfoldError> {
    let mut branches = Vec::new();
    
    for path in alts {
        // 每个分支独立展开
        let branch = self.unfold_path(subject, path, object)?;
        branches.push(branch);
    }
    
    Ok(LogicNode::Union(branches))
}
```

### 3.2 路径到映射的解析 `src/rewriter/path_mapping_resolver.rs`

**职责**: 将路径中的谓词解析为具体的表/列映射

```rust
/// 路径映射解析结果
pub struct PathMapping {
    /// 表名
    pub table_name: String,
    /// 主题列（映射到 RDF subject）
    pub subject_col: String,
    /// 对象列（映射到 RDF object）
    pub object_col: String,
    /// 谓词 URI
    pub predicate: String,
    /// 表别名
    pub alias: String,
}

pub struct PathMappingResolver<'a> {
    mapping_store: &'a MappingStore,
}

impl<'a> PathMappingResolver<'a> {
    /// 解析单个谓词的映射
    pub fn resolve_predicate(
        &self,
        predicate: &str,
        alias: &str,
    ) -> Result<PathMapping, ResolveError> {
        let mapping = self.mapping_store
            .mappings
            .get(predicate)
            .ok_or_else(|| ResolveError::MappingNotFound(predicate.to_string()))?;
        
        Ok(PathMapping {
            table_name: mapping.table_name.clone(),
            subject_col: mapping.subject_col.clone(),
            object_col: mapping.object_col.clone(),
            predicate: predicate.to_string(),
            alias: alias.to_string(),
        })
    }
}
```

### 3.3 JOIN 条件生成器 `src/sql/path_join_generator.rs`

**职责**: 为序列路径生成 JOIN 条件

```rust
pub struct PathJoinGenerator;

impl PathJoinGenerator {
    /// 生成两个路径段之间的 JOIN 条件
    pub fn generate_join_condition(
        left_mapping: &PathMapping,
        right_mapping: &PathMapping,
    ) -> String {
        // 情况 1: 同一表自连接（如 manager/manager）
        if left_mapping.table_name == right_mapping.table_name {
            // 使用左段的 object_col = 右段的 subject_col
            format!(
                "{}.{} = {}.{}",
                left_mapping.alias, left_mapping.object_col,
                right_mapping.alias, right_mapping.subject_col
            )
        } else {
            // 情况 2: 不同表连接（如 worksIn/locatedIn）
            // 推断 FK 关系或直接使用 object->subject 映射
            format!(
                "{}.{} = {}.{}",
                left_mapping.alias, left_mapping.object_col,
                right_mapping.alias, right_mapping.subject_col
            )
        }
    }
}
```

---

## 4. 数据流与处理流程

### 4.1 完整处理流程

```
SPARQL Query
    ↓
┌─────────────────────────────────────┐
│  Parser (已有)                        │
│  - 解析属性路径为 PropertyPath IR     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  IRConverter (已有)                 │
│  - 创建 LogicNode::Path              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  [S9-P0] PathUnfolder (新增)          │
│  - 展开 Path 为 Join/Union           │
│  - 解析谓词映射                      │
│  - 生成中间变量                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  UnfoldingPass (已有)               │
│  - 处理剩余的 IntensionalData       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Optimizer (已有)                   │
│  - 自连接消除                        │
│  - 谓词下推                          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  FlatSQLGenerator (已有)            │
│  - 生成最终 SQL                      │
└─────────────────────────────────────┘
```

### 4.2 展开详细流程示例

**输入 SPARQL**:
```sparql
SELECT ?managerName
WHERE {
  ?emp :manager/:name ?managerName .
  ?emp :department :Engineering .
}
```

**Step 1: IRConverter 输出**:
```rust
LogicNode::Join {
    children: vec![
        LogicNode::Path {
            subject: Term::Variable("emp"),
            path: PropertyPath::Sequence(vec![
                PropertyPath::Predicate("http://example.org/manager"),
                PropertyPath::Predicate("http://example.org/name"),
            ]),
            object: Term::Variable("managerName"),
        },
        LogicNode::IntensionalData {
            predicate: "http://example.org/department",
            args: vec![Term::Variable("emp"), Term::Constant("Engineering")],
        },
    ],
    condition: None,
    join_type: JoinType::Inner,
}
```

**Step 2: PathUnfolder 展开 Path**:
```rust
// 展开后的 Join 结构
LogicNode::Join {
    children: vec![
        // 路径展开结果
        LogicNode::Join {
            children: vec![
                // 第一个 :manager
                LogicNode::ExtensionalData {
                    table_name: "employees",
                    alias: "employees_path0_1",
                    column_mapping: {
                        "emp".to_string() => "employee_id".to_string(),
                        "manager_id_intermediate".to_string() => "manager_id".to_string(),
                    },
                    metadata: ...,
                },
                // 第二个 :name
                LogicNode::ExtensionalData {
                    table_name: "employees",
                    alias: "employees_path1_1",
                    column_mapping: {
                        "manager_id_intermediate".to_string() => "employee_id".to_string(),
                        "managerName".to_string() => "name".to_string(),
                    },
                    metadata: ...,
                },
            ],
            condition: Some(Expr::Function {
                name: "EQ".to_string(),
                args: vec![
                    Expr::Term(Term::Variable("employees_path0_1.manager_id")),
                    Expr::Term(Term::Variable("employees_path1_1.employee_id")),
                ],
            }),
            join_type: JoinType::Inner,
        },
        // 其他子节点保持不变
        LogicNode::IntensionalData { ... },
    ],
    condition: None,
    join_type: JoinType::Inner,
}
```

**Step 3: UnfoldingPass 处理剩余 IntensionalData**:
```rust
// :department 谓词展开
LogicNode::ExtensionalData {
    table_name: "employees",
    alias: "employees_dept",
    column_mapping: {
        "emp".to_string() => "employee_id".to_string(),
    },
    // 附加 Filter: department = 'Engineering'
}
```

**Step 4: 最终 SQL**:
```sql
SELECT t2.name AS managerName
FROM employees t0  -- 路径第一段
JOIN employees t1 ON t0.manager_id = t1.employee_id  -- 路径第二段
JOIN employees t2 ON t0.employee_id = t2.employee_id  -- :department 展开
WHERE t2.department = 'Engineering'
```

---

## 5. 错误处理

### 5.1 错误类型定义

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum PathUnfoldError {
    #[error("Mapping not found for predicate: {0}")]
    MappingNotFound(String),
    
    #[error("Empty property path sequence")]
    EmptyPath,
    
    #[error("Unsupported path type: {0}")]
    UnsupportedPath(String),
    
    #[error("Failed to resolve FK relationship between {from_table} and {to_table}")]
    ForeignKeyResolutionFailed {
        from_table: String,
        to_table: String,
    },
    
    #[error("Circular path detected: {0}")]
    CircularPath(String),
    
    #[error("Path nesting too deep: {depth}")]
    PathTooDeep { depth: usize },
}
```

### 5.2 错误处理策略

| 场景 | 处理方式 | 说明 |
|------|----------|------|
| 谓词无映射 | 返回 `MappingNotFound` 错误 | 配置问题，需修复映射 |
| 空序列路径 | 返回 `EmptyPath` 错误 | 语法错误 |
| 循环路径 | 返回 `CircularPath` 错误 | 如 `:knows+` 可能导致无限递归 |
| 过深嵌套 | 返回 `PathTooDeep` 错误 | 限制最大深度（如 10）防止栈溢出 |
| FK 关系不明 | 使用默认 object→subject 连接 | 警告日志，尝试通用连接 |

---

## 6. 测试策略

### 6.1 单元测试

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_unfold_inverse_path() {
        // ^:manager 应展开为交换 subject/object 的扫描
        let path = PropertyPath::Inverse(Box::new(
            PropertyPath::Predicate("http://example.org/manager".to_string())
        ));
        
        let result = unfolder.unfold_path(
            &Term::Variable("manager".to_string()),
            &path,
            &Term::Variable("emp".to_string()),
        ).unwrap();
        
        // 验证展开结果与正向路径交换参数相同
        assert!(matches!(result, LogicNode::ExtensionalData { .. }));
    }
    
    #[test]
    fn test_unfold_sequence_path() {
        // :manager/:name 应展开为两个表的 Join
        let path = PropertyPath::Sequence(vec![
            PropertyPath::Predicate("http://example.org/manager".to_string()),
            PropertyPath::Predicate("http://example.org/name".to_string()),
        ]);
        
        let result = unfolder.unfold_path(...).unwrap();
        
        // 验证产生 Join 节点
        assert!(matches!(result, LogicNode::Join { .. }));
    }
    
    #[test]
    fn test_unfold_alternative_path() {
        // :email|:phone 应展开为 Union
        let path = PropertyPath::Alternative(vec![
            PropertyPath::Predicate("http://example.org/email".to_string()),
            PropertyPath::Predicate("http://example.org/phone".to_string()),
        ]);
        
        let result = unfolder.unfold_path(...).unwrap();
        
        // 验证产生 Union 节点
        assert!(matches!(result, LogicNode::Union(_)));
    }
}
```

### 6.2 集成测试

```rust
// tests/integration/property_path_obda_test.rs

#[test]
fn test_obda_inverse_path_sql() {
    let sparql = r#"
        SELECT ?subordinate
        WHERE { ?subordinate ^:manager ?manager }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    
    // 验证 SQL 包含反向 JOIN 条件
    assert!(sql.contains("JOIN"));
    assert!(sql.contains("manager_id"));
    assert!(sql.contains("employee_id"));
}

#[test]
fn test_obda_sequence_path_sql() {
    let sparql = r#"
        SELECT ?country
        WHERE { ?emp :worksIn/:locatedIn ?country }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    
    // 验证 SQL 包含多表 JOIN
    assert!(sql.contains("employees"));
    assert!(sql.contains("departments"));
    assert!(sql.contains("locations"));
}

#[test]
fn test_obda_alternative_path_sql() {
    let sparql = r#"
        SELECT ?contact
        WHERE { ?emp :email|:phone ?contact }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    
    // 验证 SQL 包含 UNION
    assert!(sql.contains("UNION"));
}
```

---

## 7. 实现计划

### 7.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/rewriter/path_unfolder.rs` | 新建 | 核心路径展开逻辑 |
| `src/rewriter/path_mapping_resolver.rs` | 新建 | 路径到映射解析 |
| `src/sql/path_join_generator.rs` | 新建 | JOIN 条件生成 |
| `src/rewriter/mod.rs` | 修改 | 导出新增模块 |
| `src/rewriter/unfolding.rs` | 修改 | 集成 PathUnfolder |
| `src/ir/node.rs` | 无修改 | 已有 PropertyPath 定义 |
| `src/parser/property_path_parser.rs` | 无修改 | 已有完整解析器 |

### 7.2 开发顺序

1. **Step 1**: 实现 `PathMappingResolver` - 基础映射解析
2. **Step 2**: 实现 `PathUnfolder::unfold_predicate` - 单谓词展开
3. **Step 3**: 实现 `PathUnfolder::unfold_inverse` - 反向路径
4. **Step 4**: 实现 `PathUnfolder::unfold_sequence` + `PathJoinGenerator` - 序列路径
5. **Step 5**: 实现 `PathUnfolder::unfold_alternative` - 选择路径
6. **Step 6**: 集成到 UnfoldingPass
7. **Step 7**: 编写测试用例

---

## 8. 性能考虑

### 8.1 优化策略

| 优化点 | 策略 | 预期效果 |
|--------|------|----------|
| 路径缓存 | 缓存 predicate → PathMapping 解析结果 | 减少重复查找 |
| 别名复用 | 相同表路径复用已存在的别名 | 减少表扫描 |
| 早期剪枝 | 在展开时应用常量约束 | 减少 JOIN 数据量 |
| 自连接消除 | 复用现有优化器规则 | 消除冗余 JOIN |

### 8.2 复杂度分析

- **时间复杂度**: O(n) n = 路径中谓词数量
- **空间复杂度**: O(n) 产生 n 个 ExtensionalData 节点

---

## 9. 依赖与接口

### 9.1 依赖模块

```
path_unfolder.rs
    ├── ir::node::{LogicNode, PropertyPath, JoinType}
    ├── ir::expr::Term
    ├── mapping::MappingStore
    ├── metadata::TableMetadata
    └── rewriter::path_mapping_resolver::PathMappingResolver
```

### 9.2 对外接口

```rust
/// 路径展开接口（供 UnfoldingPass 调用）
pub fn unfold_property_path(
    path_node: &LogicNode::Path,
    mapping_store: &MappingStore,
    metadata_cache: &HashMap<String, Arc<TableMetadata>>,
) -> Result<LogicNode, PathUnfoldError>;
```

---

**文档结束**
