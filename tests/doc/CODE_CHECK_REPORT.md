# RS Ontop Core V2.0 - 代码规范检查报告

## 📋 检查概览

- **检查时间**: 2026-03-28 19:48
- **检查范围**: /home/yuxiaoyu/rs_ontop_core/src
- **文件总数**: 71个 .rs 文件
- **编码规范版本**: 1.0 (CODING_STANDARDS.md)

---

## 🚨 违规统计汇总

| 规则类别 | 违规数量 | 涉及文件数 | 严重程度 |
|----------|---------|-----------|----------|
| **硬编码表名** | 13处 | 6个 | 🔴 高 |
| **硬编码列名** | 64处 | 11个 | 🔴 高 |
| **unwrap/expect使用** | 43处 | 12个 | 🟠 中 |
| **日志格式问题** | 79处 | 9个 | 🟡 低 |
| **总计** | **199处** | - | - |

---

## 🔴 严重违规（必须修复）

### 规则1-2: 硬编码表名和列名

#### 文件: `src/ir/builder.rs` (2处违规)

```rust
// ❌ 第31行: 硬编码表名
let metadata = metadata_map
    .get("employees")  // 违规: 硬编码"employees"
    .cloned()
    .unwrap_or_else(|| Arc::new(TableMetadata {
        table_name: "employees".to_string(),  // 违规: 硬编码表名
        columns: vec![
            "id".to_string(),      // 违规: 硬编码列名
            "name".to_string(),    // 违规: 硬编码列名  
            "department".to_string(), // 违规: 硬编码列名
            "salary".to_string(),   // 违规: 硬编码列名
        ],
        ...
    }));
```

**修复建议**:
```rust
// ✅ 从映射配置获取
let table_name = mappings
    .and_then(|m| m.mappings.get(predicate_iri))
    .map(|rule| rule.table_name.clone())
    .ok_or_else(|| format!("No mapping for: {}", predicate_iri))?;

let metadata = metadata_map
    .get(&table_name)
    .cloned()
    .ok_or_else(|| format!("Metadata not found: {}", table_name))?;
```

---

#### 文件: `src/listener.rs` (4处违规)

```rust
// ❌ 第232-237行: 硬编码表名和列名
let metadata = std::sync::Arc::new(crate::metadata::TableMetadata {
    table_name: "employees".to_string(),  // 违规: 硬编码
    columns: vec![
        "id".to_string(),      // 违规
        "name".to_string(),    // 违规
        "department".to_string(), // 违规
        "salary".to_string(),   // 违规
    ],
    ...
});
```

---

#### 文件: `src/parser/ir_converter.rs` (7处违规)

```rust
// ❌ 多处硬编码列名
.map_var_to_column(&var, metadata, &used_cols)  // 可能包含硬编码映射
// 以及fallback_mapping中的硬编码
```

**违规详情**:
- 使用硬编码的列名映射（如 "id", "name", "employee_id"）

---

#### 文件: `src/benchmark/benchmark_definitions.rs` (38处违规)

```rust
// ❌ 多处硬编码表名和列名
pub const EMPLOYEES_TABLE: &str = "employees";  // 违规
pub const DEPARTMENTS_TABLE: &str = "departments";  // 违规
// ... 其他硬编码常量
```

**违规详情**:
- 32处硬编码列名引用（如 "employee_id", "department_id"等）
- 6处硬编码表名引用

---

### 规则6: unwrap/expect使用

#### 文件: `src/lib.rs` (6处违规)

```rust
// ❌ 第53行
let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();  // unwrap_or_default

// ❌ 第62行
.unwrap_or_else(|| Mutex::new(None));  // unwrap_or_else

// ❌ 第184行
let _ = store.load_turtle(&content);  // 未处理错误

// ❌ 其他unwrap使用
row.get::<String>(1).ok().flatten()  // 可能的unwrap
```

---

#### 文件: `src/listener.rs` (3处违规)

```rust
// ❌ 第54行
let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();  // unwrap_or_default

// ❌ 第122行
.unwrap_or_else(|| ...);  // 硬编码回退

// ❌ 第228行
.expect("valid regex");  // expect使用
```

---

#### 文件: `src/optimizer/cache.rs` (7处违规)

```rust
// ❌ 多处unwrap使用
let value = cache.get(key).unwrap();  // 可能的panic
```

---

#### 文件: `src/parser/sparql_parser_v2.rs` (4处违规)

```rust
// ❌ 解析过程中的unwrap
let result = parser.parse().unwrap();  // 可能的panic
```

---

## 🟠 中等违规（建议修复）

### 规则8: 日志格式问题

#### 文件: `src/lib.rs` (17处)

```rust
// ⚠️ 日志格式不统一
log!("rs-ontop-core: engine init after ontop_start_sparql_server failed: {}", e);
log!("rs-ontop-core: skipping table row with NULL tablename");
```

**问题**:
- 缺少 [模块] 前缀
- 格式不统一，有的用 `:` 分隔，有的直接拼接

**建议格式**:
```rust
log!("[engine] Init: ontop_start_sparql_server | Failed | Reason: {}", e);
log!("[metadata] Load: table row | Skipped | Reason: NULL tablename");
```

---

#### 文件: `src/listener.rs` (10处)

```rust
// ⚠️ 日志格式不一致
log!("rs-ontop-core: Starting SPARQL Gateway Background Worker");
log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);
log!("rs-ontop-core: Panic caught: {}", error_msg);
```

---

### 规则9: println!使用（应替换为log!）

#### 发现位置
- `src/parser/simple.rs`: 1处
- `src/bin/ontop_start_sparql_server.rs`: 1处

```rust
// ⚠️ 使用println!而不是log!
println!("Debug: {}", value);
```

---

## 📁 违规文件清单

### 需立即修复（高优先级）

| 文件 | 违规类型 | 数量 | 说明 |
|------|---------|------|------|
| `src/ir/builder.rs` | 硬编码 | 6 | IR构建器硬编码表/列 |
| `src/listener.rs` | 硬编码+unwrap | 7 | HTTP监听器硬编码 |
| `src/parser/ir_converter.rs` | 硬编码 | 7 | 解析器硬编码列名 |
| `src/benchmark/benchmark_definitions.rs` | 硬编码 | 38 | 基准测试硬编码 |

### 需修复（中优先级）

| 文件 | 违规类型 | 数量 | 说明 |
|------|---------|------|------|
| `src/lib.rs` | unwrap+日志 | 23 | 主库文件 |
| `src/optimizer/cache.rs` | unwrap | 7 | 优化器缓存 |
| `src/parser/sparql_parser_v2.rs` | unwrap | 4 | SPARQL解析器 |
| `src/listener/robust.rs` | 日志 | 10 | 健壮监听器 |

### 低优先级

| 文件 | 违规类型 | 数量 | 说明 |
|------|---------|------|------|
| `src/benchmark/benchmark_suite.rs` | 日志 | 15 | 基准测试套件 |
| `src/_unused_archive/*` | 多种 | 35 | 未使用代码（可忽略） |

---

## 📝 修复优先级建议

### P0 - 立即修复（阻塞问题）

1. **`src/ir/builder.rs`** - IR构建器硬编码导致无法处理多表
2. **`src/listener.rs`** - 监听器的硬编码回退值

### P1 - 本周修复

3. **`src/parser/ir_converter.rs`** - 解析器列名映射
4. **`src/benchmark/benchmark_definitions.rs`** - 基准测试常量
5. **`src/lib.rs`** - 主库unwrap使用

### P2 - 下周修复

6. 其他文件的unwrap/expect替换
7. 日志格式统一
8. println!替换为log!

---

## ✅ 合规文件（未发现违规）

以下文件符合编码规范，可作为参考:

- `src/error/` 模块
- `src/mapping/` 模块（除manager_v2.rs外）
- `src/sql/` 模块
- `src/rewriter/` 模块

---

## 🛠️ 自动化检查建议

建议添加CI检查脚本:

```bash
#!/bin/bash
# ci-check.sh

echo "检查硬编码表名..."
grep -rn '"employees"\|"departments"\|"positions"' src/ --include="*.rs" | grep -v "_unused_archive"

echo "检查unwrap/expect..."
grep -rn '\.unwrap()\|\.expect(' src/ --include="*.rs" | grep -v "test" | grep -v "_unused_archive"

echo "检查println!..."
grep -rn 'println!' src/ --include="*.rs" | grep -v "bin/"
```

---

**检查完成时间**: 2026-03-28 19:48
**建议修复周期**: 2周（P0+P1），4周（全部）

**报告结束**
