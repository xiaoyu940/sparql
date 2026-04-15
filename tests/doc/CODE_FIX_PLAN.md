# RS Ontop Core V2.0 - 代码规范修复方案

## 📋 文档信息

- **创建日期**: 2026-03-28
- **关联报告**: CODE_CHECK_REPORT.md
- **修复周期建议**: 2周（高优先级）+ 2周（中低优先级）

---

## 🎯 修复策略

### 总体原则

1. **先修复阻塞问题** - 影响功能的核心硬编码
2. **保持向后兼容** - 修复不破坏现有API
3. **逐步验证** - 每个文件修复后立即测试
4. **文档同步** - 修复后更新相关文档

### 修复顺序

```
Phase 1 (Week 1): 核心硬编码修复
├── src/ir/builder.rs         [P0] - IR构建器硬编码
├── src/listener.rs           [P0] - HTTP监听器硬编码
└── 测试验证

Phase 2 (Week 2): 解析器硬编码修复  
├── src/parser/ir_converter.rs [P1] - 解析器列名映射
├── src/benchmark/...         [P1] - 基准测试常量
└── 集成测试

Phase 3 (Week 3): 错误处理修复
├── src/lib.rs                [P2] - unwrap/expect替换
├── src/optimizer/cache.rs    [P2] - 缓存unwrap
└── 稳定性测试

Phase 4 (Week 4): 日志和细节优化
├── 日志格式统一
├── println!替换
└── 最终验收测试
```

---

## 🔴 Phase 1: 核心硬编码修复（P0）

### 文件1: src/ir/builder.rs

**问题**: IR构建器硬编码`"employees"`表名和列名，导致无法处理多表查询

#### 修复步骤1.1: 修改函数签名

**修复前**:
```rust
pub fn build_with_mappings(
    &self,
    parsed: &ParsedQuery,
    metadata_map: &HashMap<String, Arc<TableMetadata>>,
    mappings: Option<&MappingStore>,
) -> Result<LogicNode, OntopError> {
    let metadata = metadata_map
        .get("employees")  // ❌ 硬编码
        .cloned()
        .or_else(|| metadata_map.values().next().cloned())
        .unwrap_or_else(|| Arc::new(TableMetadata {
            table_name: "employees".to_string(),  // ❌ 硬编码
            columns: vec![
                "id".to_string(),      // ❌ 硬编码
                "name".to_string(),    // ❌ 硬编码
                "department".to_string(), // ❌ 硬编码
                "salary".to_string(),   // ❌ 硬编码
            ],
            primary_keys: vec!["id".to_string()],  // ❌ 硬编码
            foreign_keys: vec![],
            unique_constraints: vec![],
            check_constraints: vec![],
            not_null_columns: vec!["id".to_string()],  // ❌ 硬编码
        }));

    Ok(IRConverter::convert_with_mappings(parsed, metadata, mappings))
}
```

**修复后**:
```rust
pub fn build_with_mappings(
    &self,
    parsed: &ParsedQuery,
    metadata_map: &HashMap<String, Arc<TableMetadata>>,
    mappings: Option<&MappingStore>,
) -> Result<LogicNode, OntopError> {
    // 从parsed查询中提取所有谓词
    let predicates = Self::extract_predicates(parsed);
    
    // 尝试从映射配置中找到主表
    let primary_table = Self::resolve_primary_table(
        &predicates, 
        mappings, 
        metadata_map
    )?;
    
    Ok(IRConverter::convert_with_mappings(
        parsed, 
        primary_table, 
        mappings
    ))
}

/// 从查询中提取所有谓词IRI
fn extract_predicates(parsed: &ParsedQuery) -> Vec<String> {
    let mut predicates = Vec::new();
    
    // 从主模式提取
    for pattern in &parsed.main_patterns {
        if !pattern.predicate.starts_with('?') {
            let iri = pattern.predicate
                .trim_start_matches('<')
                .trim_end_matches('>')
                .to_string();
            predicates.push(iri);
        }
    }
    
    predicates
}

/// 根据谓词解析主表元数据
fn resolve_primary_table(
    predicates: &[String],
    mappings: Option<&MappingStore>,
    metadata_map: &HashMap<String, Arc<TableMetadata>>,
) -> Result<Arc<TableMetadata>, OntopError> {
    // 1. 尝试从映射配置中找到表名
    if let Some(store) = mappings {
        for pred in predicates {
            if let Some(rule) = store.mappings.get(pred) {
                let table_name = &rule.table_name;
                if let Some(metadata) = metadata_map.get(table_name) {
                    log!("[ir_builder] Resolved table '{}' from predicate '{}'", 
                         table_name, pred);
                    return Ok(Arc::clone(metadata));
                }
            }
        }
    }
    
    // 2. 回退：使用metadata_map中的第一个表
    if let Some((name, metadata)) = metadata_map.iter().next() {
        log!("[ir_builder] No mapping found, using first table '{}'", name);
        return Ok(Arc::clone(metadata));
    }
    
    // 3. 错误：没有可用的表元数据
    Err(OntopError::MissingMetadata(
        "No table metadata available. Please check database connection and mappings.".to_string()
    ))
}
```

#### 修复步骤1.2: 添加辅助函数到文件末尾

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_resolve_primary_table_from_mapping() {
        // 准备测试数据
        let mut mappings = MappingStore::new();
        mappings.insert_mapping(MappingRule {
            predicate: "http://example.org/employee_id".to_string(),
            table_name: "employees".to_string(),
            subject_template: Some("http://example.org/employee/{employee_id}".to_string()),
            position_to_column: [(1, "employee_id".to_string())].into(),
        });
        
        let mut metadata_map = HashMap::new();
        metadata_map.insert(
            "employees".to_string(),
            Arc::new(TableMetadata {
                table_name: "employees".to_string(),
                columns: vec!["employee_id".to_string(), "first_name".to_string()],
                primary_keys: vec!["employee_id".to_string()],
                foreign_keys: vec![],
                unique_constraints: vec![],
                check_constraints: vec![],
                not_null_columns: vec!["employee_id".to_string()],
            })
        );
        
        // 执行测试
        let predicates = vec!["http://example.org/employee_id".to_string()];
        let result = IRBuilder::resolve_primary_table(
            &predicates,
            Some(&mappings),
            &metadata_map
        );
        
        // 验证
        assert!(result.is_ok());
        assert_eq!(result.unwrap().table_name, "employees");
    }
}
```

---

### 文件2: src/listener.rs

**问题**: HTTP监听器硬编码表结构定义

#### 修复步骤2.1: 移除硬编码的build_logic_plan函数

**修复前**:
```rust
#[allow(dead_code)]
fn build_logic_plan(sparql_query: &str) -> Result<LogicNode, String> {
    log!("rs-ontop-core: Building logic plan for SPARQL: {}", sparql_query);

    let parser = SparqlParserV2::default();
    let parsed = parser
        .parse(sparql_query)
        .map_err(|e| format!("SPARQL parse failed: {}", e))?;

    let metadata = std::sync::Arc::new(crate::metadata::TableMetadata {
        table_name: "employees".to_string(),  // ❌ 硬编码
        columns: vec![
            "id".to_string(),      // ❌ 硬编码
            "name".to_string(),    // ❌ 硬编码
            "department".to_string(), // ❌ 硬编码
            "salary".to_string(),   // ❌ 硬编码
        ],
        primary_keys: vec!["id".to_string()],  // ❌ 硬编码
        foreign_keys: vec![],
        unique_constraints: vec![],
        check_constraints: vec![],
        not_null_columns: vec!["id".to_string()],  // ❌ 硬编码
    });

    let mut metadata_map = std::collections::HashMap::new();
    metadata_map.insert("employees".to_string(), metadata);

    IRBuilder::new()
        .build(&parsed, &metadata_map)
        .map_err(|e| format!("IR build failed: {}", e))
}
```

**修复后**:
```rust
/// 从全局ENGINE获取元数据构建逻辑计划
#[allow(dead_code)]
fn build_logic_plan(sparql_query: &str) -> Result<LogicNode, String> {
    log!("[listener] Logic plan build: Started | SPARQL length: {}", sparql_query.len());

    let parser = SparqlParserV2::default();
    let parsed = parser
        .parse(sparql_query)
        .map_err(|e| format!("SPARQL parse failed: {}", e))?;

    // 从全局ENGINE获取元数据和映射
    let guard = ENGINE
        .lock()
        .map_err(|e| format!("Engine lock failed: {}", e))?;
    
    let engine = guard.as_ref().ok_or_else(|| {
        "Engine not initialized. Please run SELECT ontop_start_sparql_server();".to_string()
    })?;

    // 使用引擎中的元数据和映射
    let builder = IRBuilder::new();
    builder
        .build_with_mappings(
            &parsed, 
            &engine.metadata, 
            Some(&engine.mappings)
        )
        .map_err(|e| format!("IR build failed: {}", e))
}
```

#### 修复步骤2.2: 修复unwrap_or_default

**修复前** (第53行):
```rust
let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();  // ❌
```

**修复后**:
```rust
let json_str = serde_json::to_string(&json_ld.0)
    .map_err(|e| {
        log!("[listener] JSON serialize: Failed | Error: {}", e);
        format!("JSON serialization failed: {}", e)
    })?;
```

#### 修复步骤2.3: 修复expect

**修复前** (第228行):
```rust
let re = regex::Regex::new(r"\?(\w+)").expect("valid regex");  // ❌
```

**修复后**:
```rust
let re = regex::Regex::new(r"\?(\w+)")
    .map_err(|e| format!("Invalid regex pattern: {}", e))?;
```

---

## 🟠 Phase 2: 解析器硬编码修复（P1）

### 文件3: src/parser/ir_converter.rs

**问题**: 解析器使用硬编码的列名回退映射

#### 修复步骤3.1: 修改fallback_mapping函数

**修复前**:
```rust
fn fallback_mapping(metadata: &TableMetadata) -> HashMap<String, String> {
    let mut out = HashMap::new();
    // ❌ 硬编码列名映射
    out.insert("id".to_string(), "id".to_string());
    out.insert("name".to_string(), "name".to_string());
    out
}
```

**修复后**:
```rust
fn fallback_mapping(metadata: &TableMetadata) -> HashMap<String, String> {
    let mut out = HashMap::new();
    // ✅ 使用metadata中的实际列名
    for col in &metadata.columns {
        out.insert(col.clone(), col.clone());
    }
    
    if out.is_empty() {
        log!("[ir_converter] Fallback mapping: Empty columns for table '{}'", 
             metadata.table_name);
    }
    
    out
}
```

#### 修复步骤3.2: 修改map_var_to_column函数

**修复前**:
```rust
fn map_var_to_column(
    var: &str, 
    metadata: &TableMetadata, 
    used_cols: &HashSet<String>
) -> String {
    // ❌ 简单的硬编码映射
    match var {
        "id" => "id".to_string(),
        "name" => "name".to_string(),
        _ => format!("col_{}", var),
    }
}
```

**修复后**:
```rust
fn map_var_to_column(
    var: &str, 
    metadata: &TableMetadata, 
    used_cols: &HashSet<String>,
    mappings: Option<&MappingStore>,
) -> Option<String> {
    // 1. 尝试从映射配置找到对应的列
    if let Some(store) = mappings {
        // 构造可能的谓词IRI
        let possible_predicates = vec![
            format!("http://example.org/{}", var),
            format!("http://example.org/{}_id", var),
        ];
        
        for pred in &possible_predicates {
            if let Some(rule) = store.mappings.get(pred) {
                let col = rule.object_col.clone();
                if !used_cols.contains(&col) {
                    return Some(col);
                }
            }
        }
    }
    
    // 2. 从metadata.columns中查找匹配的列
    for col in &metadata.columns {
        if !used_cols.contains(col) && 
           (col.eq_ignore_ascii_case(var) || 
            col.contains(var) || 
            var.contains(col)) {
            return Some(col.clone());
        }
    }
    
    // 3. 没有找到匹配的列
    log!("[ir_converter] Column mapping: var '{}' | No match in table '{}'",
         var, metadata.table_name);
    None
}
```

---

### 文件4: src/benchmark/benchmark_definitions.rs

**问题**: 基准测试定义文件包含大量硬编码常量

#### 修复方案: 将硬编码常量改为配置加载

**修复前**:
```rust
pub const EMPLOYEES_TABLE: &str = "employees";  // ❌
pub const DEPARTMENTS_TABLE: &str = "departments";  // ❌
pub const EMPLOYEE_ID_COL: &str = "employee_id";  // ❌
// ... 更多硬编码
```

**修复后**:
```rust
use crate::mapping::MappingStore;
use crate::metadata::TableMetadata;
use std::collections::HashMap;

/// 基准测试配置 - 从数据库加载
pub struct BenchmarkConfig {
    pub mappings: HashMap<String, String>,  // predicate -> table_name
    pub columns: HashMap<String, Vec<String>>, // table_name -> columns
}

impl BenchmarkConfig {
    /// 从数据库加载配置
    pub fn load_from_db(client: &mut SpiClient) -> Result<Self, String> {
        let mut mappings = HashMap::new();
        let mut columns: HashMap<String, Vec<String>> = HashMap::new();
        
        // 加载映射配置
        let mapping_rows = client.select(
            "SELECT predicate, table_name FROM ontop_mappings",
            None, None
        ).map_err(|e| format!("Failed to load mappings: {}", e))?;
        
        for row in mapping_rows {
            if let (Ok(Some(pred)), Ok(Some(table))) = 
                (row.get::<String>(1), row.get::<String>(2)) {
                mappings.insert(pred, table);
            }
        }
        
        // 加载列信息
        let col_rows = client.select(
            "SELECT table_name, column_name 
             FROM information_schema.columns 
             WHERE table_schema = 'public'",
            None, None
        ).map_err(|e| format!("Failed to load columns: {}", e))?;
        
        for row in col_rows {
            if let (Ok(Some(table)), Ok(Some(col))) = 
                (row.get::<String>(1), row.get::<String>(2)) {
                columns.entry(table).or_insert_with(Vec::new).push(col);
            }
        }
        
        Ok(BenchmarkConfig { mappings, columns })
    }
    
    /// 获取表名
    pub fn get_table_for_predicate(&self, predicate: &str) -> Option<&String> {
        self.mappings.get(predicate)
    }
    
    /// 获取列名
    pub fn get_columns_for_table(&self, table: &str) -> &[String] {
        self.columns.get(table).map(|v| v.as_slice()).unwrap_or(&[])
    }
}
```

---

## 🟡 Phase 3: 错误处理修复（P2）

### 文件5: src/lib.rs

#### 修复步骤5.1: 替换unwrap_or_default

**修复前**:
```rust
let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();
```

**修复后**:
```rust
let json_str = match serde_json::to_string(&json_ld.0) {
    Ok(s) => s,
    Err(e) => {
        log!("[lib] JSON serialization: Failed | Error: {}", e);
        return Err(OntopError::SerializationError(e.to_string()));
    }
};
```

#### 修复步骤5.2: 修复unwrap_or_else

**修复前**:
```rust
let engine = guard.as_ref().unwrap_or_else(|| Mutex::new(None));  // ❌
```

**修复后**:
```rust
let engine = guard.as_ref().ok_or_else(|| {
    OntopError::EngineNotInitialized(
        "Engine lock poisoned. Restart required.".to_string()
    )
})?;
```

---

### 文件6: src/optimizer/cache.rs

#### 修复步骤6.1: 使用安全访问替代unwrap

**修复前**:
```rust
let value = cache.get(key).unwrap();  // ❌ 可能panic
```

**修复后**:
```rust
let value = cache.get(key)
    .ok_or_else(|| OptimizerError::CacheMiss(key.to_string()))?;
```

---

## 🔵 Phase 4: 日志格式统一（P3）

### 统一日志格式脚本

```bash
#!/bin/bash
# fix_logs.sh - 批量替换日志格式

# 替换旧的日志前缀
sed -i 's/log!("rs-ontop-core:/log!("[core]/g' src/lib.rs
sed -i 's/log!("rs-ontop-core SPARQL/log!("[listener]/g' src/listener.rs

# 统一格式: [模块] 操作: 对象 | 状态 | 详情
# 这需要手动审查每个日志语句
```

### 日志格式转换示例

**修复前**:
```rust
log!("rs-ontop-core: engine init after ontop_start_sparql_server failed: {}", e);
log!("rs-ontop-core: skipping table row with NULL tablename");
```

**修复后**:
```rust
log!("[engine] Init: ontop_start_sparql_server | Failed | Error: {}", e);
log!("[metadata] Load: table row | Skipped | Reason: NULL tablename");
```

---

## ✅ 修复验证方法

### 单元测试验证

```rust
#[test]
fn test_no_hardcoded_table_names() {
    // 确保没有硬编码的表名
    let code = include_str!("../src/ir/builder.rs");
    assert!(!code.contains("\"employees\""), "Found hardcoded 'employees'");
    assert!(!code.contains("\"departments\""), "Found hardcoded 'departments'");
}

#[test]
fn test_no_unwrap_in_production_code() {
    // 检查关键路径没有unwrap
    let code = include_str!("../src/lib.rs");
    let lines: Vec<_> = code.lines().collect();
    
    for (i, line) in lines.iter().enumerate() {
        if line.contains(".unwrap()") && !line.contains("// test") {
            panic!("Found unwrap at line {}: {}", i + 1, line);
        }
    }
}
```

### 集成测试验证

```bash
#!/bin/bash
# run_integration_tests.sh

echo "=== 测试多表查询 ==="
curl -X POST http://localhost:5820/sparql \
  -d '{"query":"SELECT * FROM departments LIMIT 1"}' \
  | grep -q "department_id" && echo "✅ departments表查询成功"

echo "=== 测试employees表查询 ==="  
curl -X POST http://localhost:5820/sparql \
  -d '{"query":"SELECT * FROM employees LIMIT 1"}' \
  | grep -q "employee_id" && echo "✅ employees表查询成功"
```

---

## 📊 修复进度追踪表

| 文件 | 违规数 | 状态 | 负责人 | 完成日期 |
|------|--------|------|--------|----------|
| src/ir/builder.rs | 6 | 🔴 待修复 | TBD | - |
| src/listener.rs | 7 | 🔴 待修复 | TBD | - |
| src/parser/ir_converter.rs | 7 | 🟠 待修复 | TBD | - |
| src/benchmark/benchmark_definitions.rs | 38 | 🟠 待修复 | TBD | - |
| src/lib.rs | 23 | 🟡 待修复 | TBD | - |
| src/optimizer/cache.rs | 7 | 🟡 待修复 | TBD | - |
| 其他文件 | 111 | 🟢 低优先级 | TBD | - |

---

## 🎯 验收标准

修复完成后，代码应满足：

- [ ] 无硬编码表名（`"employees"`, `"departments"`等）
- [ ] 无硬编码列名（`"id"`, `"name"`, `"employee_id"`等）
- [ ] 生产代码无`unwrap()`/`expect()`（测试代码允许）
- [ ] 日志格式统一为 `[模块] 操作: 对象 | 状态 | 详情`
- [ ] 所有公共API有文档注释
- [ ] 单元测试覆盖率 > 80%

---

**文档结束**
