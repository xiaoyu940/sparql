# Sprint 9 P2 设计文档：高级功能与查询缓存

> **文档版本**: 1.0  
> **创建日期**: 2026-04-02  
> **阶段**: P2 (低优先级)  
> **目标**: 实现路径修饰符、日期时间函数和查询缓存机制

---

## 1. 概述

### 1.1 背景与目标

Sprint 9 P2 聚焦于提升系统的完整性和性能：

1. **路径修饰符** - 在 P0 基础上扩展 `*`, `+`, `?` 修饰符的完整实现
2. **日期时间函数** - 支持 SPARQL 时间函数，增强时间维度查询能力
3. **查询缓存** - 引入缓存层，避免重复解析和 SQL 生成

### 1.2 与 P0/P1 的关系

```
Sprint 9 P0: 基础路径支持 (Inverse, Sequence, Alternative)
       ↓
Sprint 9 P1: 函数扩展与优化器
       ↓
Sprint 9 P2: 高级路径修饰 + 日期时间 + 缓存
       ↓
┌────────────────────────────────────────────┐
│  Path Modifiers (* + ?)                    │
│  - 在 P0 展开基础上添加递归 CTE 支持        │
│  - 处理传递闭包                            │
├────────────────────────────────────────────┤
│  DateTime Functions                        │
│  - 解析：ir_converter.rs                    │
│  - SQL生成：flat_generator.rs              │
├────────────────────────────────────────────┤
│  Query Cache                               │
│  - 新模块：cache/query_cache.rs            │
│  - 集成：engine/translate 入口             │
└────────────────────────────────────────────┘
```

---

## 2. 路径修饰符完整实现

### 2.1 功能范围

| 修饰符 | SPARQL 语法 | 语义 | 实现复杂度 |
|--------|-------------|------|-----------|
| `*` | `p*` | 零次或多次（Kleene 星） | 高（递归 CTE） |
| `+` | `p+` | 一次或多次 | 中（递归 CTE） |
| `?` | `p?` | 零次或一次（可选） | 低（LEFT JOIN） |

**注意**: P0 已实现路径结构的展开（Inverse/Sequence/Alternative），P2 补充修饰符的完整语义。

### 2.2 设计决策

**决策 1: 修饰符处理策略**
- `?` (可选): 转换为 LEFT JOIN，允许 NULL
- `*` / `+`: 在 SQL 生成阶段生成递归 CTE
- 与其他路径组合时，修饰符内部优先展开

**决策 2: 递归 CTE 限制**
- 最大递归深度: 10（防止无限递归）
- 循环检测: 通过访问节点集合检测
- 性能保护: 大结果集时触发流式处理

### 2.3 IR 表示

路径修饰符已在 `src/ir/node.rs` 中定义：

```rust
#[derive(Debug, Clone, PartialEq)]
pub enum PropertyPath {
    // [S9-P2] 零次或多次: p*
    Star(Box<PropertyPath>),
    // [S9-P2] 一次或多次: p+
    Plus(Box<PropertyPath>),
    // [S9-P2] 零次或一次: p?
    Optional(Box<PropertyPath>),
    
    // [S9-P0] 已定义
    Inverse(Box<PropertyPath>),
    Sequence(Vec<PropertyPath>),
    Alternative(Vec<PropertyPath>),
    Negated(Vec<String>),
    Predicate(String),
}
```

### 2.4 修饰符展开策略

#### 2.4.1 `?` (Optional) - LEFT JOIN 实现

```rust
// 在 PathUnfolder 中处理 Optional
fn unfold_optional(
    &mut self,
    subject: &Term,
    inner: &PropertyPath,
    object: &Term,
) -> Result<LogicNode, UnfoldError> {
    // 1. 展开内部路径
    let inner_unfolded = self.unfold_path(subject, inner, object)?;
    
    // 2. 包装为 LEFT JOIN，允许 NULL
    // 创建虚拟的 "空值提供者" 节点
    let empty_node = LogicNode::Values {
        variables: vec![/* 路径中使用的变量 */],
        rows: vec![vec![Term::Constant("NULL".to_string())]],
    };
    
    // 3. 使用 UNION 实现可选语义
    // p? = p UNION (subject 自身，当 p 无匹配时)
    Ok(LogicNode::Union(vec![
        inner_unfolded,
        LogicNode::Construction {
            projected_vars: vec![/* subject 变量映射 */],
            bindings: /* 创建 subject 到自身的映射 */,
            child: Box::new(self.create_single_row_node(subject)),
        },
    ]))
}
```

**SQL 生成示例**:
```sql
-- ?emp :manager? ?mgr
-- 展开为 LEFT JOIN
SELECT t0.employee_id,
       COALESCE(t1.manager_id, t0.employee_id) AS mgr_id
FROM employees t0
LEFT JOIN employees t1 ON t0.employee_id = t1.employee_id
```

#### 2.4.2 `*` (Star) 和 `+` (Plus) - 递归 CTE 实现

对于需要递归传递闭包的路径（如 `:knows*`), P2 在 SQL 生成阶段处理：

```rust
// src/sql/recursive_path_generator.rs
pub struct RecursivePathGenerator;

impl RecursivePathGenerator {
    /// 为 * 和 + 生成递归 CTE
    pub fn generate_recursive_cte(
        base_table: &str,
        subject_col: &str,
        object_col: &str,
        is_plus: bool, // true = p+, false = p*
    ) -> String {
        let anchor = if is_plus {
            // p+: 锚点是直接匹配 (depth=1)
            format!(
                "SELECT {subject_col} AS start_node, {object_col} AS end_node, 1 AS depth, 
                        ARRAY[{subject_col}] AS path_nodes
                 FROM {base_table}
                 WHERE {object_col} IS NOT NULL",
            )
        } else {
            // p*: 锚点包含起点自身 (depth=0)
            format!(
                "SELECT {subject_col} AS start_node, {subject_col} AS end_node, 0 AS depth,
                        ARRAY[{subject_col}] AS path_nodes
                 FROM {base_table}
                 UNION ALL
                 SELECT {subject_col}, {object_col}, 1, ARRAY[{subject_col}]
                 FROM {base_table}
                 WHERE {object_col} IS NOT NULL",
            )
        };
        
        let recursive = format!(
            "SELECT t.start_node, b.{object_col}, t.depth + 1,
                    t.path_nodes || b.{subject_col}
             FROM path_cte t
             JOIN {base_table} b ON t.end_node = b.{subject_col}
             WHERE t.depth < 10
               AND NOT b.{object_col} = ANY(t.path_nodes)  -- 防循环"
        );
        
        format!(
            "WITH RECURSIVE path_cte AS (
                {anchor}
                UNION ALL
                {recursive}
            )",
        )
    }
}
```

**SQL 生成示例**:
```sql
-- ?a :knows* ?b (找到所有直接和间接认识的人)
WITH RECURSIVE path_cte AS (
    -- 锚点：每个人认识他们自己（深度 0）
    SELECT employee_id AS start_node, employee_id AS end_node, 0 AS depth,
           ARRAY[employee_id] AS visited
    FROM employees
    UNION ALL
    -- 锚点：直接认识关系（深度 1）
    SELECT e1.employee_id, e2.employee_id, 1, ARRAY[e1.employee_id]
    FROM employees e1
    JOIN employees e2 ON e1.manager_id = e2.employee_id
    
    UNION ALL
    
    -- 递归：认识的人的认识
    SELECT t.start_node, e.employee_id, t.depth + 1,
           t.visited || e.employee_id
    FROM path_cte t
    JOIN employees e ON t.end_node = e.employee_id
    WHERE t.depth < 10
      AND NOT e.employee_id = ANY(t.visited)  -- 避免循环
)
SELECT start_node, end_node
FROM path_cte
WHERE depth > 0  -- p+ 排除 depth=0
```

### 2.5 组合路径处理

复杂路径需要分层处理：

```
(:knows/:manager)*
    ↓ 分解
Sequence([knows, manager]) wrapped in Star
    ↓ 处理
Star(Sequence([knows, manager]))
    ↓ 展开
递归 CTE 中包含两表 Join
```

```rust
fn unfold_complex_modified_path(
    &mut self,
    subject: &Term,
    path: &PropertyPath,
    object: &Term,
) -> Result<LogicNode, UnfoldError> {
    match path {
        PropertyPath::Star(inner) => {
            // 1. 先展开内部路径为子计划
            let inner_plan = self.unfold_for_recursive(subject, inner, object)?;
            
            // 2. 包装为可递归执行的子查询
            Ok(LogicNode::RecursiveSubquery {
                base_plan: Box::new(inner_plan.clone()),
                recursive_plan: Box::new(inner_plan),
                subject: subject.clone(),
                object: object.clone(),
                min_depth: 0,
                max_depth: 10,
            })
        }
        PropertyPath::Plus(inner) => {
            let inner_plan = self.unfold_for_recursive(subject, inner, object)?;
            Ok(LogicNode::RecursiveSubquery {
                base_plan: Box::new(inner_plan.clone()),
                recursive_plan: Box::new(inner_plan),
                subject: subject.clone(),
                object: object.clone(),
                min_depth: 1,
                max_depth: 10,
            })
        }
        _ => self.unfold_path(subject, path, object)
    }
}
```

---

## 3. 日期时间函数设计

### 3.1 功能范围

| 函数 | SPARQL 标准 | SQL 映射 | 说明 |
|------|-------------|----------|------|
| `NOW()` | ✓ | `CURRENT_TIMESTAMP` | 当前日期时间 |
| `YEAR()` | ✓ | `EXTRACT(YEAR FROM ...)` | 提取年份 |
| `MONTH()` | ✓ | `EXTRACT(MONTH FROM ...)` | 提取月份 |
| `DAY()` | ✓ | `EXTRACT(DAY FROM ...)` | 提取日期 |
| `HOURS()` | ✓ | `EXTRACT(HOUR FROM ...)` | 提取小时 |
| `MINUTES()` | ✓ | `EXTRACT(MINUTE FROM ...)` | 提取分钟 |
| `SECONDS()` | ✓ | `EXTRACT(SECOND FROM ...)` | 提取秒 |
| `TIMEZONE()` | ✓ | 自定义实现 | 提取时区 |
| `TZ()` | ✓ | 自定义实现 | 提取时区缩写 |

### 3.2 IR 表示

日期时间函数作为标准 `Expr::Function`:

```rust
// NOW() - 无参数
Expr::Function {
    name: "NOW".to_string(),
    args: vec![],
}

// YEAR(?date) - 单参数
Expr::Function {
    name: "YEAR".to_string(),
    args: vec![
        Expr::Term(Term::Variable("date".to_string()))
    ],
}
```

### 3.3 解析器扩展

在 `src/parser/ir_converter.rs` 中添加：

```rust
impl IRConverter {
    /// 解析日期时间函数
    fn parse_datetime_expr(func_name: &str, args_str: &str) -> Option<Expr> {
        let upper = func_name.to_uppercase();
        
        match upper.as_str() {
            "NOW" => {
                if args_str.trim().is_empty() {
                    Some(Expr::Function {
                        name: "NOW".to_string(),
                        args: vec![],
                    })
                } else {
                    log::error!("NOW() takes no arguments");
                    None
                }
            }
            "YEAR" | "MONTH" | "DAY" | "HOURS" | "MINUTES" | "SECONDS" => {
                let args = Self::split_function_args(args_str);
                if args.len() != 1 {
                    log::error!("{}() requires exactly 1 argument", func_name);
                    return None;
                }
                
                let arg = Self::parse_filter_expr(args[0].trim())?;
                Some(Expr::Function {
                    name: upper,
                    args: vec![arg],
                })
            }
            _ => None,
        }
    }
}
```

### 3.4 SQL 生成

在 `src/sql/flat_generator.rs` 中添加：

```rust
// 在 translate_expression 的 match 中添加:
"NOW" => {
    Ok("CURRENT_TIMESTAMP".to_string())
}

"YEAR" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(YEAR FROM {})", args_sql[0]))
}

"MONTH" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(MONTH FROM {})", args_sql[0]))
}

"DAY" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(DAY FROM {})", args_sql[0]))
}

"HOURS" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(HOUR FROM {})", args_sql[0]))
}

"MINUTES" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(MINUTE FROM {})", args_sql[0]))
}

"SECONDS" if args_sql.len() == 1 => {
    Ok(format!("EXTRACT(SECOND FROM {})", args_sql[0]))
}
```

### 3.5 使用示例

**SPARQL 查询**:
```sparql
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?emp ?hireYear
WHERE {
  ?emp :hireDate ?date .
  BIND(YEAR(?date) AS ?hireYear)
  FILTER(?hireYear > 2020)
}
```

**生成 SQL**:
```sql
SELECT t0.employee_id,
       EXTRACT(YEAR FROM t0.hire_date) AS hire_year
FROM employees t0
WHERE EXTRACT(YEAR FROM t0.hire_date) > 2020
```

**时间比较查询**:
```sparql
SELECT ?event
WHERE {
  ?event :timestamp ?ts .
  FILTER(?ts > NOW() - "P7D"^^xsd:duration)
}
```

---

## 4. 查询缓存设计

### 4.1 设计目标

| 目标 | 说明 |
|------|------|
| 减少重复解析 | 缓存 SPARQL → IR 结果 |
| 避免重复优化 | 缓存 IR → Optimized IR |
| 加速 SQL 生成 | 缓存 IR → SQL 映射 |
| 结果集缓存 | 可选：缓存 SQL 执行结果（带 TTL） |

### 4.2 缓存架构

```
┌─────────────────────────────────────────────────────────────┐
│                      QueryCacheManager                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  ParseCache     │  │  OptimizeCache  │  │  SQLCache    │ │
│  │  (SPARQL→IR)    │  │  (IR→OptIR)     │  │  (IR→SQL)    │ │
│  │                 │  │                 │  │              │ │
│  │  Key: SPARQL    │  │  Key: IR hash   │  │  Key: IR hash│ │
│  │  Val: IR        │  │  Val: OptIR     │  │  Val: SQL    │ │
│  │  TTL: 1 hour    │  │  TTL: 30 min    │  │  TTL: 30 min │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                    │
│  │  ResultCache    │  │  PlanCache      │                    │
│  │  (SQL→Results)  │  │  (SPARQL→SQL)    │                    │
│  │                 │  │                 │                    │
│  │  Key: SQL hash  │  │  Key: SPARQL    │                    │
│  │  Val: Results   │  │  Val: SQL       │                    │
│  │  TTL: 5 min     │  │  TTL: 1 hour    │                    │
│  │  Max: 1000 rows │  │                 │                    │
│  └─────────────────┘  └─────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 模块设计

**文件**: `src/cache/query_cache.rs`

```rust
use std::collections::HashMap;
use std::time::{Duration, Instant};
use std::sync::{Arc, RwLock};
use lru::LruCache;

/// 缓存配置
#[derive(Debug, Clone)]
pub struct CacheConfig {
    /// 解析缓存大小
    pub parse_cache_size: usize,
    /// 优化缓存大小
    pub optimize_cache_size: usize,
    /// SQL 缓存大小
    pub sql_cache_size: usize,
    /// 结果缓存大小
    pub result_cache_size: usize,
    /// 默认 TTL
    pub default_ttl: Duration,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            parse_cache_size: 1000,
            optimize_cache_size: 500,
            sql_cache_size: 500,
            result_cache_size: 200,
            default_ttl: Duration::from_secs(1800), // 30 分钟
        }
    }
}

/// 带 TTL 的缓存条目
struct CacheEntry<V> {
    value: V,
    created_at: Instant,
    ttl: Duration,
}

impl<V> CacheEntry<V> {
    fn is_expired(&self) -> bool {
        self.created_at.elapsed() > self.ttl
    }
}

/// 查询缓存
pub struct QueryCache {
    /// SPARQL 解析缓存: SPARQL string -> IR
    parse_cache: RwLock<LruCache<String, LogicNode>>,
    parse_cache_ttl: Duration,
    
    /// 优化缓存: IR hash -> Optimized IR
    optimize_cache: RwLock<LruCache<u64, LogicNode>>,
    optimize_cache_ttl: Duration,
    
    /// SQL 生成缓存: IR hash -> SQL
    sql_cache: RwLock<LruCache<u64, String>>,
    sql_cache_ttl: Duration,
    
    /// 结果缓存: SQL hash -> QueryResult
    result_cache: RwLock<LruCache<u64, QueryResult>>,
    result_cache_ttl: Duration,
    
    /// 统计信息
    stats: RwLock<CacheStats>,
}

#[derive(Debug, Default)]
pub struct CacheStats {
    pub parse_hits: u64,
    pub parse_misses: u64,
    pub optimize_hits: u64,
    pub optimize_misses: u64,
    pub sql_hits: u64,
    pub sql_misses: u64,
    pub result_hits: u64,
    pub result_misses: u64,
}

impl QueryCache {
    pub fn new(config: CacheConfig) -> Self {
        Self {
            parse_cache: RwLock::new(LruCache::new(config.parse_cache_size)),
            parse_cache_ttl: config.default_ttl,
            optimize_cache: RwLock::new(LruCache::new(config.optimize_cache_size)),
            optimize_cache_ttl: config.default_ttl,
            sql_cache: RwLock::new(LruCache::new(config.sql_cache_size)),
            sql_cache_ttl: config.default_ttl,
            result_cache: RwLock::new(LruCache::new(config.result_cache_size)),
            result_cache_ttl: Duration::from_secs(300), // 结果缓存 5 分钟
            stats: RwLock::new(CacheStats::default()),
        }
    }
    
    /// 获取解析缓存
    pub fn get_parse_result(&self, sparql: &str) -> Option<LogicNode> {
        let mut cache = self.parse_cache.write().unwrap();
        let result = cache.get(sparql).cloned();
        
        let mut stats = self.stats.write().unwrap();
        if result.is_some() {
            stats.parse_hits += 1;
        } else {
            stats.parse_misses += 1;
        }
        
        result
    }
    
    /// 设置解析缓存
    pub fn set_parse_result(&self, sparql: &str, ir: LogicNode) {
        let mut cache = self.parse_cache.write().unwrap();
        cache.put(sparql.to_string(), ir);
    }
    
    /// 获取 SQL 缓存
    pub fn get_sql(&self, ir: &LogicNode) -> Option<String> {
        let hash = Self::compute_ir_hash(ir);
        let mut cache = self.sql_cache.write().unwrap();
        let result = cache.get(&hash).cloned();
        
        let mut stats = self.stats.write().unwrap();
        if result.is_some() {
            stats.sql_hits += 1;
        } else {
            stats.sql_misses += 1;
        }
        
        result
    }
    
    /// 设置 SQL 缓存
    pub fn set_sql(&self, ir: &LogicNode, sql: String) {
        let hash = Self::compute_ir_hash(ir);
        let mut cache = self.sql_cache.write().unwrap();
        cache.put(hash, sql);
    }
    
    /// 计算 IR 哈希值
    fn compute_ir_hash(ir: &LogicNode) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        // 序列化 IR 并哈希
        let serialized = serde_json::to_string(ir).unwrap_or_default();
        serialized.hash(&mut hasher);
        hasher.finish()
    }
    
    /// 获取缓存统计
    pub fn get_stats(&self) -> CacheStats {
        self.stats.read().unwrap().clone()
    }
    
    /// 清空所有缓存
    pub fn clear_all(&self) {
        self.parse_cache.write().unwrap().clear();
        self.optimize_cache.write().unwrap().clear();
        self.sql_cache.write().unwrap().clear();
        self.result_cache.write().unwrap().clear();
    }
    
    /// 使特定 SPARQL 查询缓存失效
    pub fn invalidate(&self, sparql: &str) {
        self.parse_cache.write().unwrap().pop(sparql);
        // 级联使相关缓存失效...
    }
}
```

### 4.4 缓存集成

**在 Engine 中集成缓存**:

```rust
// src/engine.rs
pub struct OntopEngine {
    mapping_store: Arc<MappingStore>,
    metadata_cache: Arc<HashMap<String, TableMetadata>>,
    query_cache: Arc<QueryCache>,  // [S9-P2] 新增
}

impl OntopEngine {
    /// 带缓存的 SPARQL → SQL 转换
    pub fn translate(&self, sparql: &str) -> Result<String, TranslateError> {
        // 1. 检查 SQL 缓存 (SPARQL 可直接查 SQL 缓存，跳过中间步骤)
        if let Some(sql) = self.query_cache.get_sql_by_sparql(sparql) {
            log::debug!("Cache hit for SPARQL query");
            return Ok(sql);
        }
        
        // 2. 检查解析缓存
        let ir = if let Some(cached_ir) = self.query_cache.get_parse_result(sparql) {
            cached_ir
        } else {
            let parsed = self.parse_sparql(sparql)?;
            let ir = self.convert_to_ir(parsed)?;
            self.query_cache.set_parse_result(sparql, ir.clone());
            ir
        };
        
        // 3. 检查 SQL 生成缓存
        let sql = if let Some(cached_sql) = self.query_cache.get_sql(&ir) {
            cached_sql
        } else {
            let optimized = self.optimize(ir.clone())?;
            let sql = self.generate_sql(&optimized)?;
            self.query_cache.set_sql(&ir, sql.clone());
            sql
        };
        
        Ok(sql)
    }
}
```

### 4.5 缓存失效策略

| 场景 | 策略 |
|------|------|
| 映射变更 | 清空所有缓存 |
| Schema 变更 | 清空解析和优化缓存 |
| 手动刷新 | 提供 `refresh_cache()` API |
| TTL 过期 | LRU 自动淘汰 |
| 内存压力 | 配置最大缓存大小，超限时淘汰 |

```rust
/// 映射变更时的缓存刷新
impl OntopEngine {
    pub fn refresh_mappings(&mut self, new_mappings: MappingStore) {
        // 1. 更新映射
        self.mapping_store = Arc::new(new_mappings);
        
        // 2. 清空依赖缓存
        self.query_cache.clear_all();
        
        log::info!("Mappings refreshed, cache cleared");
    }
}
```

---

## 5. 测试策略

### 5.1 路径修饰符测试

```rust
#[test]
fn test_star_path_sql_generation() {
    let sparql = r#"
        SELECT ?friend
        WHERE { ?emp :knows* ?friend }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("WITH RECURSIVE"));
    assert!(sql.contains("UNION ALL"));
    assert!(sql.contains("depth < 10"));
}

#[test]
fn test_optional_path_sql_generation() {
    let sparql = r#"
        SELECT ?manager
        WHERE { ?emp :manager? ?manager }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("LEFT JOIN") || sql.contains("COALESCE"));
}
```

### 5.2 日期时间函数测试

```rust
#[test]
fn test_now_function() {
    let sparql = "SELECT (NOW() AS ?now) WHERE {}";
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("CURRENT_TIMESTAMP"));
}

#[test]
fn test_year_extraction() {
    let sparql = r#"
        SELECT (YEAR(?date) AS ?year)
        WHERE { ?emp :hireDate ?date }
    "#;
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("EXTRACT(YEAR FROM"));
}
```

### 5.3 缓存测试

```rust
#[test]
fn test_parse_cache() {
    let cache = QueryCache::new(CacheConfig::default());
    let sparql = "SELECT ?s WHERE { ?s a :Person }";
    let ir = create_test_ir();
    
    // 首次 miss
    assert!(cache.get_parse_result(sparql).is_none());
    
    // 设置缓存
    cache.set_parse_result(sparql, ir.clone());
    
    // 再次 hit
    assert!(cache.get_parse_result(sparql).is_some());
    
    let stats = cache.get_stats();
    assert_eq!(stats.parse_hits, 1);
    assert_eq!(stats.parse_misses, 1);
}
```

---

## 6. 实现计划

### 6.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/rewriter/path_unfolder.rs` | 修改 | 添加修饰符展开 |
| `src/sql/recursive_path_generator.rs` | 新建 | 递归 CTE 生成 |
| `src/parser/ir_converter.rs` | 修改 | 添加日期时间函数解析 |
| `src/sql/flat_generator.rs` | 修改 | 添加日期时间函数 SQL 生成 |
| `src/cache/query_cache.rs` | 新建 | 查询缓存实现 |
| `src/cache/mod.rs` | 新建 | 缓存模块入口 |
| `src/engine.rs` | 修改 | 集成查询缓存 |
| `Cargo.toml` | 修改 | 添加 `lru` 依赖 |

### 6.2 依赖添加

```toml
# Cargo.toml
[dependencies]
# 现有依赖...
lru = "0.12"  # LRU 缓存实现
```

### 6.3 开发顺序

1. **Step 1**: 实现日期时间函数解析与 SQL 生成（最简单）
2. **Step 2**: 实现 `?` (Optional) 路径修饰符
3. **Step 3**: 实现 `*` 和 `+` 路径修饰符（递归 CTE）
4. **Step 4**: 实现 QueryCache 基础结构
5. **Step 5**: 在 Engine 中集成缓存
6. **Step 6**: 添加缓存统计和监控

---

## 7. 性能考虑

### 7.1 缓存性能目标

| 场景 | 目标延迟 |
|------|----------|
| 缓存命中 SPARQL → SQL | < 1ms |
| 缓存 miss SPARQL → SQL | < 50ms（复杂查询） |
| 缓存内存占用 | < 100MB |

### 7.2 递归路径性能

| 路径类型 | 最大深度 | 预期响应时间 |
|----------|----------|--------------|
| `*` / `+` | 10 | 取决于数据规模和连接密度 |
| `?` | N/A | 与普通 JOIN 相同 |

### 7.3 监控指标

```rust
pub struct CacheMetrics {
    /// 命中率
    pub hit_rate: f64,
    /// 平均缓存条目存活时间
    pub avg_ttl: Duration,
    /// 每秒查询数
    pub qps: f64,
    /// 内存使用量 (字节)
    pub memory_usage: usize,
}
```

---

**文档结束**
