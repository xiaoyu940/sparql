# RS Ontop Core V2.0 - 编码规范

## 📋 文档信息

- **文档版本**: 1.0
- **创建日期**: 2026-03-28
- **适用范围**: RS Ontop Core V2.0 所有 Rust 源码
- **目的**: 禁止硬编码，确保配置驱动的架构设计

---

## 🚫 禁止硬编码规则

### 规则 1: 禁止硬编码表名

**❌ 错误示例**:
```rust
// builder.rs 第31行 - 硬编码表名
let metadata = metadata_map
    .get("employees")  // ❌ 禁止硬编码
    .cloned()
    .unwrap_or_else(|| Arc::new(TableMetadata {
        table_name: "employees".to_string(),  // ❌ 禁止硬编码
        ...
    }));
```

**✅ 正确做法**:
```rust
// 从映射配置中动态获取表名
let table_name = mappings
    .and_then(|m| m.mappings.get(predicate_iri))
    .map(|rule| rule.table_name.clone())
    .ok_or_else(|| format!("No mapping found for predicate: {}", predicate_iri))?;

let metadata = metadata_map
    .get(&table_name)
    .cloned()
    .ok_or_else(|| format!("Table metadata not found: {}", table_name))?;
```

**原因**:
- 系统需要支持任意数量的表（当前7张，未来可能扩展）
- 表名可能在不同部署环境中不同
- 配置应该集中管理，便于维护

---

### 规则 2: 禁止硬编码列名

**❌ 错误示例**:
```rust
// builder.rs 第36行 - 硬编码列名
columns: vec![
    "id".to_string(),       // ❌ 禁止
    "name".to_string(),     // ❌ 禁止
    "department".to_string(), // ❌ 禁止
    "salary".to_string(),   // ❌ 禁止
],
```

**✅ 正确做法**:
```rust
// 从数据库的 information_schema 或映射配置动态获取
let columns: Vec<String> = client
    .select(
        &format!(
            "SELECT column_name FROM information_schema.columns WHERE table_name = '{}'",
            table_name
        ),
        None,
        None,
    )?
    .into_iter()
    .filter_map(|row| row.get::<String>(1).ok().flatten())
    .collect();

// 或从映射规则获取
let object_col = mapping_rule.object_col.clone();  // 如 "employee_id"
```

**原因**:
- 列名应该与数据库 schema 保持一致
- 不同表的列名各不相同
- 支持 schema 变更无需修改代码

---

### 规则 3: 禁止硬编码 URI/命名空间

**❌ 错误示例**:
```rust
// 硬编码完整 URI
let employee_iri = "http://example.org/Employee";
let dept_iri = "http://example.org/Department";
```

**✅ 正确做法**:
```rust
// 从配置或数据库加载
const NAMESPACE: &str = "http://example.org/";

fn build_iri(entity_type: &str) -> String {
    format!("{}{}", NAMESPACE, entity_type)
}

// 或从 ontop_ontology_snapshots 加载
let base_namespace = ontology.get_namespace();  // 从配置读取
```

**原因**:
- 命名空间可能因部署环境而异
- 便于配置化管理
- 支持多租户场景

---

### 规则 4: 禁止硬编码默认值/回退值

**❌ 错误示例**:
```rust
.unwrap_or_else(|| Arc::new(TableMetadata {
    table_name: "employees".to_string(),  // ❌ 硬编码回退
    columns: vec!["id".to_string()],       // ❌ 硬编码回退
    ...
}));
```

**✅ 正确做法**:
```rust
// 明确的错误处理，不隐式回退
.ok_or_else(|| {
    log!("Table metadata not found in mapping store: {}", table_name);
    OntopError::MissingMetadata(table_name.to_string())
})?

// 或从配置文件加载默认配置
let default_config = load_config("default_metadata.json")?;
```

**原因**:
- 隐式回退会掩盖配置问题
- 便于故障排查
- 强制配置完整性检查

---

### 规则 5: 所有配置必须来自数据库或配置文件

**✅ 允许的数据来源**:

| 数据来源 | 用途 | 示例 |
|---------|------|------|
| `ontop_mappings` 表 | RDF→SQL映射规则 | predicate, table_name, object_col |
| `ontop_ontology_snapshots` 表 | OWL本体定义 | classes, properties |
| `information_schema` | 数据库Schema | table_name, column_name |
| `ontop_config.json` | 系统配置 | namespace, endpoint_port |
| 环境变量 | 部署配置 | DATABASE_URL, LOG_LEVEL |

**❌ 禁止的数据来源**:
- 源码中的字符串字面量
- 硬编码的常量（除非是框架级别的，如 HTTP状态码）
- 注释中的示例值

---

## 📐 配置驱动架构原则

### 原则 1: 配置与代码分离

```
┌─────────────────────────────────────────┐
│              配置层 (数据库/文件)        │
├─────────────────────────────────────────┤
│  ontop_mappings          映射规则        │
│  ontop_ontology_snapshots  本体定义      │
│  ontop_config.json       系统配置        │
└──────────────────┬──────────────────────┘
                   │ 加载
                   ▼
┌─────────────────────────────────────────┐
│              运行时内存结构              │
├─────────────────────────────────────────┤
│  MappingStore.mappings    ← 从表加载    │
│  MappingStore.classes     ← 从表加载    │
│  Config.endpoint_port    ← 从文件加载   │
└──────────────────┬──────────────────────┘
                   │ 使用
                   ▼
┌─────────────────────────────────────────┐
│              业务逻辑代码                 │
├─────────────────────────────────────────┤
│  从运行时结构读取配置，不直接读表         │
│  不硬编码任何业务相关的字符串            │
└─────────────────────────────────────────┘
```

### 原则 2: 运行时配置检查

**必须实现配置验证**:
```rust
fn validate_configuration(store: &MappingStore) -> Result<(), OntopError> {
    // 检查必需的映射是否存在
    let required_predicates = vec![
        "http://example.org/employee_id",
        "http://example.org/first_name",
        // ... 从配置加载
    ];
    
    for pred in &required_predicates {
        if !store.mappings.contains_key(*pred) {
            return Err(OntopError::MissingMapping(pred.to_string()));
        }
    }
    
    Ok(())
}
```

### 原则 3: 配置热加载支持

**架构要求**:
```rust
// 配置变更时自动重新加载
pub fn refresh_mappings() -> Result<(), OntopError> {
    let new_store = load_mappings_from_db()?;
    validate_configuration(&new_store)?;
    
    // 原子替换
    let mut engine = ENGINE.lock()?;
    *engine = Some(OntopEngine::new(Arc::new(new_store), ...));
    
    Ok(())
}
```

---

## 🔍 代码审查检查清单

### 审查时必须检查的项目

- [ ] 代码中没有 `"employees"`、 `"departments"` 等业务表名硬编码
- [ ] 代码中没有 `"id"`、 `"name"`、 `"employee_id"` 等列名硬编码
- [ ] 代码中没有 `"http://example.org/"` 等完整URI硬编码
- [ ] 代码中没有 `.unwrap_or_else(|| ...)` 硬编码回退值
- [ ] 所有配置从 `ontop_mappings` 或 `ontop_ontology_snapshots` 表加载
- [ ] 所有表/列元数据从 `information_schema` 动态读取
- [ ] 配置加载失败时返回明确错误，不隐式回退到默认值

### 禁止的代码模式

```rust
// ❌ 禁止：硬编码表名
let table = "employees";

// ❌ 禁止：硬编码列名
let col = "employee_id";

// ❌ 禁止：硬编码URI
let iri = "http://example.org/Employee";

// ❌ 禁止：unwrap_or 硬编码回退
let name = value.unwrap_or("Default".to_string());

// ❌ 禁止：硬编码的HashMap初始化
let mut map = HashMap::new();
map.insert("employees", vec!["id", "name"]);  // 禁止
```

### 允许的代码模式

```rust
// ✅ 允许：从配置加载
let table = mapping.table_name;  // 从数据库读取

// ✅ 允许：从元数据获取
let col = metadata.columns.first()?;  // 动态获取

// ✅ 允许：从配置构建URI
let iri = format!("{}{}", config.namespace, entity_type);

// ✅ 允许：明确的错误处理
let name = value.ok_or_else(|| Error::MissingConfig)?;

// ✅ 允许：运行时构建的HashMap
let map = load_mappings_from_db()?;  // 从数据库加载
```

---

## 📝 违规处理

### 发现硬编码时的修复流程

1. **识别硬编码值**
   - 找到硬编码的字符串/数值
   - 确定其业务含义

2. **创建配置项**
   - 如果是表名 → 插入 `ontop_mappings` 表
   - 如果是本体定义 → 插入 `ontop_ontology_snapshots` 表
   - 如果是系统配置 → 添加到 `ontop_config.json`

3. **修改代码**
   - 替换硬编码为配置读取
   - 添加错误处理
   - 移除 unwrap_or 回退

4. **验证修复**
   - 删除硬编码值
   - 从配置加载
   - 测试功能正常

### 示例修复

**修复前 (builder.rs)**:
```rust
let metadata = metadata_map
    .get("employees")  // ❌ 硬编码
    .cloned()
    .unwrap_or_else(|| Arc::new(TableMetadata {
        table_name: "employees".to_string(),  // ❌ 硬编码
        columns: vec!["id".to_string(), ...], // ❌ 硬编码
        ...
    }));
```

**修复后**:
```rust
// 从映射配置获取表名
let table_name = mappings
    .and_then(|m| m.mappings.get(predicate_iri))
    .map(|rule| rule.table_name.clone())
    .ok_or_else(|| format!("No mapping for: {}", predicate_iri))?;

// 从元数据Map获取
let metadata = metadata_map
    .get(&table_name)
    .cloned()
    .ok_or_else(|| format!("Metadata not found: {}", table_name))?;
```

---

## 🚨 错误处理规范

### 规则 6: 禁止使用 unwrap() / expect()

**❌ 禁止示例**:
```rust
// ❌ 禁止：unwrap() 可能导致panic
let result = some_operation().unwrap();

// ❌ 禁止：expect() 同样危险
let value = map.get("key").expect("Key must exist");

// ❌ 禁止：unwrap_or 硬编码回退
let name = value.unwrap_or("default".to_string());
```

**✅ 正确做法**:
```rust
// ✅ 允许：使用 ? 传播错误
let result = some_operation()?;

// ✅ 允许：显式错误处理
let value = map.get("key")
    .ok_or_else(|| OntopError::MissingKey("key".to_string()))?;

// ✅ 允许：从配置加载默认值
let default_value = load_default_config()?;
let name = value.unwrap_or(default_value);
```

**原因**:
- 生产环境中 panic 会导致服务中断
- 显式错误便于问题定位和恢复
- 调用者应该决定是否处理错误或传播

---

### 规则 7: 错误信息必须包含上下文

**❌ 禁止示例**:
```rust
// ❌ 错误信息太模糊
Err("Failed".to_string())
Err("Error occurred".to_string())
```

**✅ 正确做法**:
```rust
// ✅ 包含具体上下文
Err(format!("Failed to load mapping for predicate: {}", predicate))
Err(format!("Table '{}' not found in metadata cache", table_name))
Err(format!("SPI query failed: {} | SQL: {}", e, sql))
```

**错误信息格式**:
```
<操作>: <具体对象> | <原因> | <上下文>

示例:
- "Mapping lookup: predicate http://example.org/employee_id | Not found in store"
- "SQL execution: SELECT * FROM employees | Column 'salary' does not exist"
- "HTTP response: client 192.168.1.1 | Connection reset"
```

---

## 📝 日志记录规范

### 规则 8: 统一日志格式

**日志级别使用**:

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| **ERROR** | 系统错误，需要立即处理 | 数据库连接失败、关键配置缺失 |
| **WARN** | 异常情况，但可以恢复 | 配置加载使用了默认值、重试次数过多 |
| **INFO** | 重要操作记录 | 服务器启动、配置重新加载、查询执行 |
| **DEBUG** | 调试信息 | 查询解析细节、优化器决策过程 |
| **TRACE** | 最详细的跟踪 | 函数进入/退出、变量值变化 |

**日志格式**:
```rust
// 格式: [模块] 操作: 对象 | 状态 | 详细信息
log!("[listener] HTTP request: {} {} | Started | From: {}", method, path, client_ip);
log!("[engine] SPARQL translation: query_id={} | Completed | SQL length: {}", id, sql.len());
log!("[mapping] Reload: {} predicates | Success | Duration: {}ms", count, duration);
```

**✅ 正确示例**:
```rust
// 服务器启动
log!("[listener] SPARQL Gateway: Starting | Port: 5820");

// 查询执行
log!("[engine] Query execution: id={} | Started | SPARQL length: {} chars", query_id, sparql.len());

// 性能指标
log!("[perf] SQL generation: {} predicates | Completed | Time: {}μs", pred_count, elapsed.as_micros());

// 错误记录
log!("[error] Mapping load: predicate {} | Failed | Reason: {}", pred, e);
```

**❌ 禁止示例**:
```rust
// ❌ 缺少上下文
log!("Done");
log!("Error occurred");

// ❌ 使用 println! 而不是 log!
println!("Debug: {}", value);
```

---

## 🧪 测试规范

### 规则 9: 所有公共API必须有单元测试

**测试命名规范**:
```rust
// 格式: test_<模块>_<函数>_<场景>
#[test]
fn test_mapping_store_load_turtle_success() { }

#[test]
fn test_mapping_store_load_turtle_invalid_syntax() { }

#[test]
fn test_engine_translate_sparql_simple_query() { }

#[test]
fn test_engine_translate_sparql_complex_join() { }
```

**测试覆盖要求**:

| 类型 | 覆盖率要求 | 说明 |
|------|-----------|------|
| 单元测试 | > 80% | 每个模块独立测试 |
| 集成测试 | 关键路径 | SPARQL→SQL 端到端测试 |
| 边界测试 | 必须包含 | 空输入、超大输入、特殊字符 |
| 性能测试 | 基准测试 | 查询执行时间、内存使用 |

**✅ 测试示例**:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mapping_rule_from_db_row() {
        // Arrange
        let row = create_test_row();
        
        // Act
        let rule = MappingRule::from_row(&row).unwrap();
        
        // Assert
        assert_eq!(rule.predicate, "http://example.org/employee_id");
        assert_eq!(rule.table_name, "employees");
        assert_eq!(rule.object_col, "employee_id");
    }

    #[test]
    fn test_mapping_rule_missing_column() {
        // Arrange: 模拟缺少必需列的行
        let row = create_invalid_row();
        
        // Act & Assert
        let result = MappingRule::from_row(&row);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Missing column"));
    }
}
```

---

## ⚡ 性能规范

### 规则 10: 避免性能陷阱

**❌ 禁止的性能问题**:

```rust
// ❌ 禁止：在循环中分配内存
for row in rows {
    let mut map = HashMap::new();  // 每次迭代都分配
    map.insert(...);
}

// ❌ 禁止：重复字符串拼接
let mut sql = String::new();
for col in columns {
    sql += &format!("{}, ", col);  // O(n²) 复杂度
}

// ❌ 禁止：不必要的克隆
let data = engine.mappings.clone();  // 克隆整个HashMap

// ❌ 禁止：阻塞操作无超时
let result = blocking_operation();  // 可能永远等待
```

**✅ 正确做法**:

```rust
// ✅ 允许：提前分配容量
let mut map = HashMap::with_capacity(rows.len());
for row in rows {
    map.insert(...);  // 复用已分配的内存
}

// ✅ 允许：使用 Join 避免 O(n²)
let sql = columns.join(", ");  // O(n)

// ✅ 允许：使用引用避免克隆
let data = &engine.mappings;  // 借用，不分配

// ✅ 允许：始终使用超时
let result = operation.timeout(Duration::from_secs(30)).await?;
```

### 规则 11: 大查询必须使用流式处理

**触发流式处理的阈值**:
- 预期返回行数 > 10,000
- 查询包含 `SELECT *` 无 LIMIT
- 查询涉及大表全表扫描（如 attendance 300万行）

**流式处理实现**:
```rust
// ✅ 正确：使用 Portal 分批获取
let portal = client.open_portal(&sql, batch_size)?;
while let Some(batch) = portal.fetch_next()? {
    for row in batch {
        yield row;  // 流式输出
    }
}

// ❌ 禁止：一次性加载所有数据
let all_rows = client.select(&sql, None, None)?;  // 可能OOM
for row in all_rows {
    process(row);
}
```

---

## 🏷️ 命名规范

### 规则 12: 统一的命名约定

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| **结构体/枚举** | PascalCase | `MappingStore`, `OntologyClass` |
| **函数/方法** | snake_case | `load_mappings()`, `translate_sparql()` |
| **变量** | snake_case | `table_name`, `predicate_iri` |
| **常量** | SCREAMING_SNAKE_CASE | `DEFAULT_BATCH_SIZE`, `MAX_QUERY_TIMEOUT` |
| **模块** | snake_case | `mapping`, `optimizer` |
| **类型别名** | PascalCase | `type QueryResult = Result<...>` |
| **生命周期** | 简短小写 | `'a`, `'ctx` |

**缩写处理**:
```rust
// ✅ 允许：常用缩写
IRBuilder    // IR = Intermediate Representation
SPARQLParser // SPARQL 是专有名词
SQLGenerator // SQL 是专有名词

// ✅ 允许：URI/IRI 在变量名中
let predicate_iri = "http://example.org/employee_id";
let subject_uri = format!("http://.../employee/{}", id);
```

---

## 🔐 并发安全规范

### 规则 13: 共享状态必须线程安全

**❌ 禁止示例**:
```rust
// ❌ 禁止：非线程安全的全局状态
static mut MAPPINGS: Option<MappingStore> = None;  // unsafe!

// ❌ 禁止：RefCell 在多线程环境
let cache = RefCell::new(HashMap::new());  // 不是 Sync
```

**✅ 正确做法**:
```rust
// ✅ 允许：使用 Mutex + Arc
static ENGINE: Lazy<Mutex<Option<OntopEngine>>> = 
    Lazy::new(|| Mutex::new(None));

// ✅ 允许：使用 RwLock 支持多读
let cache = Arc::new(RwLock::new(HashMap::new()));

// ✅ 允许：使用原子类型
let counter = AtomicU64::new(0);
```

### 规则 14: 锁的使用规范

**锁粒度原则**:
```rust
// ✅ 细粒度锁：仅保护需要的数据
{
    let cache = cache.lock()?;  // 小范围
    let value = cache.get(key).cloned();
} // 锁在这里释放
// 执行其他操作...

// ❌ 粗粒度锁：长时间持有
let cache = cache.lock()?;
let value = cache.get(key).cloned();
let result = expensive_operation(value)?;  // 长时间持有锁
```

**避免死锁**:
```rust
// ✅ 按固定顺序获取多个锁
let first = lock_a.lock()?;
let second = lock_b.lock()?;

// ❌ 不同代码路径顺序不一致会导致死锁
// 代码A: lock_a -> lock_b
// 代码B: lock_b -> lock_a  // 死锁！
```

---

## 📚 文档注释规范

### 规则 15: 公共API必须有文档注释

**文档要求**:

```rust
/// 将SPARQL查询转换为SQL
///
/// # Arguments
/// * `sparql` - SPARQL 1.1 查询字符串
/// * `mappings` - 从数据库加载的RDF映射配置
///
/// # Returns
/// * `Ok(String)` - 生成的SQL语句
/// * `Err(String)` - 转换失败的原因
///
/// # Errors
/// 可能返回的错误:
/// * 解析错误 - SPARQL语法无效
/// * 映射缺失 - 谓词没有对应的表映射
/// * SQL生成错误 - 内部逻辑错误
///
/// # Examples
/// ```
/// let sparql = "SELECT ?name WHERE {?e ex:name ?name}";
/// let sql = engine.translate(sparql)?;
/// assert!(sql.contains("SELECT"));
/// ```
pub fn translate(&self, sparql: &str) -> Result<String, String> {
    ...
}
```

**文档内容检查清单**:
- [ ] 功能描述（一句话）
- [ ] 参数说明（每个参数）
- [ ] 返回值说明
- [ ] 错误情况说明
- [ ] 使用示例（复杂函数）

---

## 🎯 架构目标

遵循本编码规范，确保系统实现以下架构目标：

1. **配置驱动** - 所有业务配置在数据库/配置文件中
2. **零硬编码** - 代码中不包含业务相关的常量
3. **动态扩展** - 新增表/列无需修改代码
4. **故障透明** - 配置问题立即报错，不隐式回退
5. **热加载** - 配置变更可实时生效

---

**文档结束**

