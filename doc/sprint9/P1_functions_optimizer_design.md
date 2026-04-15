# Sprint 9 P1 设计文档：函数扩展与查询优化器增强

> **文档版本**: 1.0  
> **创建日期**: 2026-04-02  
> **阶段**: P1 (中等优先级)  
> **目标**: 扩展 SPARQL 函数支持与查询优化能力

---

## 1. 概述

### 1.1 背景与目标

Sprint 9 P1 聚焦于三个核心能力的增强：

1. **BIND 条件函数** - 支持 `IF()` 和 `COALESCE()`，实现 SPARQL 查询中的条件逻辑
2. **GeoSPARQL 度量函数** - 扩展空间查询能力，支持距离计算、缓冲区分析
3. **查询优化器增强** - 引入基于统计信息的成本模型和索引推荐

### 1.2 与现有架构的关系

```
┌─────────────────────────────────────────────────────────────┐
│                     现有架构 (Sprint 8)                      │
├─────────────────────────────────────────────────────────────┤
│  FILTER 解析 ──→ ir_converter::parse_filter_expr()         │
│  函数翻译    ──→ flat_generator::translate_expression()    │
│  基础优化    ──→ optimizer::basic_optimizer.rs               │
└─────────────────────────────────────────────────────────────┘
                              ↓ 扩展
┌─────────────────────────────────────────────────────────────┐
│                  Sprint 9 P1 新增模块                        │
├─────────────────────────────────────────────────────────────┤
│  条件函数解析 ──→ ir_converter::parse_conditional_expr()    │
│  度量函数翻译 ──→ flat_generator::translate_geo_metric()    │
│  成本优化器   ──→ optimizer::cost_based_optimizer.rs         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. BIND 条件函数设计

### 2.1 功能范围

| 函数 | 语法 | SQL 映射 | 说明 |
|------|------|----------|------|
| `IF` | `IF(condition, true_val, false_val)` | `CASE WHEN` | 条件判断 |
| `COALESCE` | `COALESCE(val1, val2, ...)` | `COALESCE` | 返回第一个非 NULL 值 |

### 2.2 IR 表示

条件函数作为 `Expr::Function` 的扩展，无需新增 IR 类型：

```rust
// 已有定义在 src/ir/expr.rs
pub enum Expr {
    // ... 其他变体
    Function {
        name: String,  // "IF" / "COALESCE"
        args: Vec<Expr>,
    },
}
```

**IF 表达式示例**:
```rust
Expr::Function {
    name: "IF".to_string(),
    args: vec![
        Expr::Compare {  // condition
            left: Box::new(Expr::Term(Term::Variable("salary".to_string()))),
            op: ComparisonOp::Gt,
            right: Box::new(Expr::Term(Term::Literal { 
                value: "50000".to_string(),
                datatype: Some("xsd:integer".to_string()),
                language: None,
            })),
        },
        Expr::Term(Term::Literal {  // true value
            value: "High".to_string(),
            datatype: Some("xsd:string".to_string()),
            language: None,
        }),
        Expr::Term(Term::Literal {  // false value
            value: "Normal".to_string(),
            datatype: Some("xsd:string".to_string()),
            language: None,
        }),
    ],
}
```

### 2.3 解析器扩展

在 `src/parser/ir_converter.rs` 中添加条件函数解析：

```rust
impl IRConverter {
    /// 扩展 parse_filter_expr 支持条件函数
    fn parse_conditional_expr(expr: &str) -> Option<Expr> {
        let trimmed = expr.trim();
        let upper = trimmed.to_uppercase();
        
        // 解析 IF(expr1, expr2, expr3)
        if upper.starts_with("IF(") {
            return Self::parse_if_expr(trimmed);
        }
        
        // 解析 COALESCE(expr1, expr2, ...)
        if upper.starts_with("COALESCE(") {
            return Self::parse_coalesce_expr(trimmed);
        }
        
        None
    }
    
    /// 解析 IF 表达式
    fn parse_if_expr(expr: &str) -> Option<Expr> {
        // IF 格式: IF(condition, then_expr, else_expr)
        let content = &expr[3..expr.len()-1]; // 移除 "IF(" 和 ")"
        let args = Self::split_function_args(content);
        
        if args.len() != 3 {
            log::error!("IF() requires exactly 3 arguments, got {}", args.len());
            return None;
        }
        
        let condition = Self::parse_filter_expr(args[0].trim())?;
        let true_expr = Self::parse_filter_expr(args[1].trim())?;
        let false_expr = Self::parse_filter_expr(args[2].trim())?;
        
        Some(Expr::Function {
            name: "IF".to_string(),
            args: vec![condition, true_expr, false_expr],
        })
    }
    
    /// 解析 COALESCE 表达式
    fn parse_coalesce_expr(expr: &str) -> Option<Expr> {
        // COALESCE 格式: COALESCE(expr1, expr2, ...)
        let content = &expr[10..expr.len()-1]; // 移除 "COALESCE(" 和 ")"
        let args = Self::split_function_args(content);
        
        if args.is_empty() {
            log::error!("COALESCE() requires at least 1 argument");
            return None;
        }
        
        let parsed_args: Vec<Expr> = args
            .iter()
            .filter_map(|arg| Self::parse_filter_expr(arg.trim()))
            .collect();
        
        if parsed_args.is_empty() {
            return None;
        }
        
        Some(Expr::Function {
            name: "COALESCE".to_string(),
            args: parsed_args,
        })
    }
}
```

### 2.4 SQL 生成

在 `src/sql/flat_generator.rs` 的 `translate_expression` 中添加：

```rust
// 在 match name.to_uppercase().as_str() 中添加:
"IF" if args_sql.len() == 3 => {
    // SPARQL: IF(condition, true_val, false_val)
    // SQL: CASE WHEN condition THEN true_val ELSE false_val END
    Ok(format!(
        "CASE WHEN {} THEN {} ELSE {} END",
        args_sql[0], args_sql[1], args_sql[2]
    ))
}

"COALESCE" if !args_sql.is_empty() => {
    // SPARQL: COALESCE(val1, val2, ...)
    // SQL: COALESCE(val1, val2, ...)
    Ok(format!("COALESCE({})", args_sql.join(", ")))
}
```

### 2.5 使用示例

**SPARQL 查询**:
```sparql
PREFIX ex: <http://example.org/>

SELECT ?name ?salaryLevel
WHERE {
  ?emp ex:name ?name ;
       ex:salary ?salary .
  BIND(IF(?salary > 50000, "High", "Normal") AS ?salaryLevel)
}
```

**生成 SQL**:
```sql
SELECT t0.name,
       CASE WHEN t0.salary > 50000 THEN 'High' ELSE 'Normal' END AS salary_level
FROM employees t0
```

---

## 3. GeoSPARQL 度量函数设计

### 3.1 功能范围

| 函数 | GeoSPARQL 标准 | PostGIS 映射 | 说明 |
|------|---------------|--------------|------|
| `geof:distance` | SF | `ST_Distance` | 两点间距离 |
| `geof:buffer` | SF | `ST_Buffer` | 创建缓冲区几何 |

**注意**: Sprint 8 已实现拓扑关系函数（`sfWithin`, `sfContains` 等），P1 补充度量函数。

### 3.2 IR 表示

与现有 GeoSPARQL 函数一致，使用 `Expr::Function`:

```rust
Expr::Function {
    name: "GEOF:DISTANCE".to_string(),
    args: vec![
        Expr::Term(Term::Variable("wkt1".to_string())),
        Expr::Term(Term::Variable("wkt2".to_string())),
        // 可选: 单位参数
        Expr::Term(Term::Literal {
            value: "urn:ogc:def:uom:EPSG:: metre".to_string(),
            datatype: Some("xsd:anyURI".to_string()),
            language: None,
        }),
    ],
}
```

### 3.3 解析器扩展

```rust
impl IRConverter {
    /// 扩展 parse_filter_expr 支持 GeoSPARQL 度量函数
    fn parse_geo_metric_expr(func_name: &str, args_str: &str) -> Option<Expr> {
        let args = Self::split_function_args(args_str);
        let parsed_args: Vec<Expr> = args
            .iter()
            .filter_map(|arg| Self::parse_filter_expr(arg.trim()))
            .collect();
        
        match func_name.to_uppercase().as_str() {
            "GEOF:DISTANCE" | "DISTANCE" => {
                if parsed_args.len() >= 2 {
                    Some(Expr::Function {
                        name: "GEOF:DISTANCE".to_string(),
                        args: parsed_args,
                    })
                } else {
                    log::error!("geof:distance requires at least 2 arguments");
                    None
                }
            }
            "GEOF:BUFFER" | "BUFFER" => {
                if parsed_args.len() >= 2 {
                    Some(Expr::Function {
                        name: "GEOF:BUFFER".to_string(),
                        args: parsed_args,
                    })
                } else {
                    log::error!("geof:buffer requires at least 2 arguments");
                    None
                }
            }
            _ => None,
        }
    }
}
```

### 3.4 SQL 生成

```rust
// 在 flat_generator.rs translate_expression 中添加:
"GEOF:DISTANCE" | "DISTANCE" if args_sql.len() >= 2 => {
    // geof:distance(geom1, geom2, [units])
    // ST_Distance(ST_GeomFromText(geom1, 4326), ST_GeomFromText(geom2, 4326))
    let units = if args_sql.len() >= 3 {
        // 处理单位参数，默认为米
        "4326".to_string()
    } else {
        "4326".to_string() // WGS 84
    };
    
    Ok(format!(
        "ST_Distance(ST_GeomFromText({}, {}), ST_GeomFromText({}, {}))",
        args_sql[0], units, args_sql[1], units
    ))
}

"GEOF:BUFFER" | "BUFFER" if args_sql.len() >= 2 => {
    // geof:buffer(geom, radius, [units])
    // ST_Buffer(ST_GeomFromText(geom, 4326), radius)
    let radius = &args_sql[1];
    let units = if args_sql.len() >= 3 {
        // 根据单位转换半径
        "4326".to_string()
    } else {
        "4326".to_string()
    };
    
    Ok(format!(
        "ST_Buffer(ST_GeomFromText({}, {}), {})",
        args_sql[0], units, radius
    ))
}
```

### 3.5 使用示例

**SPARQL 查询**:
```sparql
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>

SELECT ?store ?dist
WHERE {
  ?store geo:lat ?lat ;
         geo:long ?long .
  BIND(CONCAT("POINT(", ?long, " ", ?lat, ")") AS ?storeWkt)
  BIND("POINT(116.4074 39.9042)"^^geo:wktLiteral AS ?beijingWkt)
  BIND(geof:distance(?storeWkt, ?beijingWkt) AS ?dist)
  FILTER(?dist < 10000)
}
ORDER BY ?dist
```

**生成 SQL**:
```sql
SELECT t0.store_id,
       ST_Distance(
         ST_GeomFromText(CONCAT('POINT(', t0.longitude, ' ', t0.latitude, ')'), 4326),
         ST_GeomFromText('POINT(116.4074 39.9042)', 4326)
       ) AS dist
FROM stores t0
WHERE ST_Distance(
  ST_GeomFromText(CONCAT('POINT(', t0.longitude, ' ', t0.latitude, ')'), 4326),
  ST_GeomFromText('POINT(116.4074 39.9042)', 4326)
) < 10000
ORDER BY dist
```

---

## 4. 查询优化器增强

### 4.1 目标与范围

当前优化器仅实现基于规则的优化（RBO），P1 引入基于成本的优化（CBO）基础：

| 能力 | 说明 | 优先级 |
|------|------|--------|
| 统计信息收集 | 从 PostgreSQL `pg_stats` / `pg_class` 收集 | P1 |
| 成本模型 | 基于行数和操作成本的估算 | P1 |
| 索引推荐 | 基于查询模式推荐缺失索引 | P1 |
| 连接顺序优化 | 基于成本的 Join 重排 | P1-3 |

### 4.2 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                  QueryOptimizer (Enhanced)                   │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│ │StatsCollector│  │  CostModel   │  │IndexAdvisor  │        │
│ │              │  │              │  │              │        │
│ │• pg_stats    │  │• row estimates│  │• missing idx │        │
│ │• pg_class    │  │• op costs    │  │• benefit est │        │
│ └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│        │                 │                  │               │
│        └─────────────────┼──────────────────┘               │
│                          ▼                                 │
│        ┌────────────────────────────────┐                  │
│        │    OptimizationPass 序列        │                  │
│        │  1. PredicatePushdown            │                  │
│        │  2. CostBasedJoinReorder (新增)  │                  │
│        │  3. IndexSelection (新增)         │                  │
│        └────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 统计信息收集器

**文件**: `src/optimizer/stats_collector.rs`

```rust
use std::collections::HashMap;
use std::sync::Arc;
use pgrx::prelude::*;

/// 表统计信息
#[derive(Debug, Clone)]
pub struct TableStats {
    pub table_name: String,
    /// 近似行数 (from pg_class.reltuples)
    pub estimated_rows: f64,
    /// 列统计信息
    pub column_stats: HashMap<String, ColumnStats>,
    /// 现有索引
    pub indexes: Vec<IndexInfo>,
}

/// 列统计信息
#[derive(Debug, Clone)]
pub struct ColumnStats {
    pub column_name: String,
    /// 不同值数量 (n_distinct)
    pub distinct_count: f64,
    /// NULL 值比例
    pub null_frac: f64,
    /// 直方图边界 (用于范围查询选择性估算)
    pub histogram_bounds: Option<Vec<String>>,
    /// MCV (Most Common Values) 及其频率
    pub most_common_vals: Option<Vec<String>>,
    pub most_common_freqs: Option<Vec<f64>>,
}

/// 索引信息
#[derive(Debug, Clone)]
pub struct IndexInfo {
    pub index_name: String,
    pub columns: Vec<String>,
    pub is_unique: bool,
}

/// 统计信息收集器
pub struct StatsCollector;

impl StatsCollector {
    /// 收集指定表的统计信息
    pub fn collect_table_stats(table_name: &str) -> Result<TableStats, StatsError> {
        Spi::connect(|client| {
            // 1. 获取表行数
            let row_query = format!(
                "SELECT reltuples::bigint FROM pg_class WHERE relname = '{}'",
                table_name
            );
            let estimated_rows = client
                .select(&row_query, None, None)?
                .first()
                .get::<i64>(1)?
                .unwrap_or(0) as f64;
            
            // 2. 获取列统计信息
            let col_query = format!(
                "SELECT attname, n_distinct, null_frac, 
                        histogram_bounds::text, 
                        most_common_vals::text,
                        most_common_freqs::text
                 FROM pg_stats 
                 WHERE tablename = '{}'",
                table_name
            );
            
            let mut column_stats = HashMap::new();
            for row in client.select(&col_query, None, None)? {
                let col_name: String = row.get(1)?.unwrap_or_default();
                let stats = ColumnStats {
                    column_name: col_name.clone(),
                    distinct_count: row.get(2)?.unwrap_or(-1.0),
                    null_frac: row.get(3)?.unwrap_or(0.0),
                    histogram_bounds: row.get(4)?,
                    most_common_vals: row.get(5)?,
                    most_common_freqs: row.get::<String>(6)?
                        .map(|s| s.trim_matches('{').trim_matches('}')
                            .split(',')
                            .filter_map(|v| v.parse().ok())
                            .collect()),
                };
                column_stats.insert(col_name, stats);
            }
            
            // 3. 获取索引信息
            let idx_query = format!(
                "SELECT indexname, indexdef 
                 FROM pg_indexes 
                 WHERE tablename = '{}'",
                table_name
            );
            
            let mut indexes = Vec::new();
            for row in client.select(&idx_query, None, None)? {
                let idx_name: String = row.get(1)?.unwrap_or_default();
                let idx_def: String = row.get(2)?.unwrap_or_default();
                // 解析索引定义提取列名
                let columns = Self::parse_index_columns(&idx_def);
                indexes.push(IndexInfo {
                    index_name: idx_name,
                    columns,
                    is_unique: idx_def.contains("UNIQUE"),
                });
            }
            
            Ok(TableStats {
                table_name: table_name.to_string(),
                estimated_rows,
                column_stats,
                indexes,
            })
        })
    }
}
```

### 4.4 成本模型

**文件**: `src/optimizer/cost_model.rs`

```rust
/// 操作成本常量（基于 PostgreSQL 默认成本参数）
pub const COST_SEQ_PAGE: f64 = 1.0;      // 顺序页读取成本
pub const COST_RANDOM_PAGE: f64 = 4.0;   // 随机页读取成本
pub const COST_CPU_TUPLE: f64 = 0.01;    // 处理每个元组的 CPU 成本
pub const COST_CPU_INDEX: f64 = 0.005;   // 索引处理的 CPU 成本
pub const COST_CPU_OP: f64 = 0.0025;     // 操作或函数调用成本

/// 计划节点成本估算
#[derive(Debug, Clone, Default)]
pub struct CostEstimate {
    /// 启动成本（产生第一行前的成本）
    pub startup_cost: f64,
    /// 总成本（产生所有行的成本）
    pub total_cost: f64,
    /// 估算输出行数
    pub rows: f64,
    /// 估算平均行宽（字节）
    pub width: usize,
}

pub struct CostModel;

impl CostModel {
    /// 估算表扫描成本
    pub fn estimate_seq_scan(table_stats: &TableStats) -> CostEstimate {
        let rows = table_stats.estimated_rows;
        // 估算页数 (假设平均行宽 200 字节，页大小 8KB)
        let pages = (rows * 200.0 / 8192.0).ceil();
        
        let total_cost = 
            pages * COST_SEQ_PAGE +      // I/O 成本
            rows * COST_CPU_TUPLE;       // CPU 成本
        
        CostEstimate {
            startup_cost: 0.0,
            total_cost,
            rows,
            width: 200,
        }
    }
    
    /// 估算索引扫描成本
    pub fn estimate_index_scan(
        table_stats: &TableStats,
        index: &IndexInfo,
        selectivity: f64,
    ) -> CostEstimate {
        let total_rows = table_stats.estimated_rows;
        let matching_rows = (total_rows * selectivity).max(1.0);
        
        // 估算索引页数 (简化模型)
        let index_pages = (total_rows * 0.1).ceil();
        let table_pages = (matching_rows * 200.0 / 8192.0).ceil();
        
        let total_cost =
            index_pages * COST_RANDOM_PAGE * 0.5 +  // 索引遍历
            table_pages * COST_RANDOM_PAGE +         // 表随机访问
            matching_rows * COST_CPU_TUPLE;
        
        CostEstimate {
            startup_cost: index_pages * COST_RANDOM_PAGE * 0.5,
            total_cost,
            rows: matching_rows,
            width: 200,
        }
    }
    
    /// 估算 Nested Loop Join 成本
    pub fn estimate_nested_loop_join(
        outer: &CostEstimate,
        inner: &CostEstimate,
    ) -> CostEstimate {
        let rows = outer.rows * inner.rows;
        let total_cost = 
            outer.startup_cost + 
            outer.total_cost +
            outer.rows * inner.total_cost;
        
        CostEstimate {
            startup_cost: outer.startup_cost + inner.startup_cost,
            total_cost,
            rows,
            width: outer.width + inner.width,
        }
    }
    
    /// 估算 Hash Join 成本
    pub fn estimate_hash_join(
        outer: &CostEstimate,
        inner: &CostEstimate,
    ) -> CostEstimate {
        // 假设内表较小，构建哈希表
        let rows = (outer.rows * inner.rows / inner.rows.max(1.0)).min(outer.rows);
        let hash_cost = inner.rows * COST_CPU_TUPLE * 2.0; // 构建哈希表
        
        let total_cost = 
            outer.startup_cost + 
            inner.startup_cost +
            hash_cost +
            outer.total_cost +
            inner.total_cost;
        
        CostEstimate {
            startup_cost: outer.startup_cost + inner.startup_cost + hash_cost,
            total_cost,
            rows,
            width: outer.width + inner.width,
        }
    }
}
```

### 4.5 索引推荐器

**文件**: `src/optimizer/index_advisor.rs`

```rust
use crate::ir::node::LogicNode;

/// 索引推荐建议
#[derive(Debug, Clone)]
pub struct IndexRecommendation {
    pub table_name: String,
    pub columns: Vec<String>,
    pub estimated_benefit: f64,
    pub reason: String,
}

pub struct IndexAdvisor;

impl IndexAdvisor {
    /// 分析查询计划，推荐缺失索引
    pub fn analyze_plan(plan: &LogicNode) -> Vec<IndexRecommendation> {
        let mut recommendations = Vec::new();
        let mut filter_columns: HashMap<String, Vec<String>> = HashMap::new();
        let mut join_columns: HashMap<String, Vec<String>> = HashMap::new();
        
        Self::collect_index_candidates(plan, &mut filter_columns, &mut join_columns);
        
        // 分析 Filter 条件中的列
        for (table, columns) in filter_columns {
            if columns.len() >= 1 {
                // 推荐单列或复合索引
                let benefit = Self::estimate_filter_benefit(&table, &columns);
                recommendations.push(IndexRecommendation {
                    table_name: table.clone(),
                    columns: columns.clone(),
                    estimated_benefit: benefit,
                    reason: format!("Frequently filtered columns: {:?}", columns),
                });
            }
        }
        
        // 分析 Join 条件中的列
        for (table, columns) in join_columns {
            for col in columns {
                let benefit = Self::estimate_join_benefit(&table, &col);
                recommendations.push(IndexRecommendation {
                    table_name: table.clone(),
                    columns: vec![col.clone()],
                    estimated_benefit: benefit,
                    reason: format!("Frequently joined on column: {}", col),
                });
            }
        }
        
        // 按收益排序
        recommendations.sort_by(|a, b| {
            b.estimated_benefit.partial_cmp(&a.estimated_benefit).unwrap()
        });
        
        recommendations
    }
    
    fn collect_index_candidates(
        node: &LogicNode,
        filter_cols: &mut HashMap<String, Vec<String>>,
        join_cols: &mut HashMap<String, Vec<String>>,
    ) {
        match node {
            LogicNode::Filter { expression, child } => {
                Self::extract_filter_columns(expression, filter_cols);
                Self::collect_index_candidates(child, filter_cols, join_cols);
            }
            LogicNode::Join { children, condition, .. } => {
                if let Some(expr) = condition {
                    Self::extract_join_columns(expr, join_cols);
                }
                for child in children {
                    Self::collect_index_candidates(child, filter_cols, join_cols);
                }
            }
            LogicNode::ExtensionalData { table_name, column_mapping, .. } => {
                // 记录表别名到实际表名的映射
            }
            _ => {
                // 递归处理其他节点
            }
        }
    }
}
```

### 4.6 成本驱动的 Join 重排

**文件**: `src/optimizer/join_reorder.rs`

```rust
/// Join 顺序优化器
pub struct JoinReorderOptimizer {
    cost_model: CostModel,
    stats_cache: HashMap<String, TableStats>,
}

impl JoinReorderOptimizer {
    /// 基于动态规划的最优 Join 顺序查找
    /// 使用类似 PostgreSQL 的 DP 算法
    pub fn optimize_join_order(&self, joins: Vec<LogicNode>) -> LogicNode {
        if joins.len() <= 2 {
            // 二元或更少 Join 无需优化
            return self.build_left_deep_tree(joins);
        }
        
        // 收集所有参与 Join 的表
        let relations: Vec<JoinRelation> = joins
            .iter()
            .map(|n| self.extract_relation(n))
            .collect();
        
        // DP: 状态 = 已连接的表集合位掩码
        let n = relations.len();
        let mut dp: HashMap<u64, JoinState> = HashMap::new();
        
        // 初始化：单个表的状态
        for (i, rel) in relations.iter().enumerate() {
            let mask = 1u64 << i;
            let cost = self.estimate_base_cost(rel);
            dp.insert(mask, JoinState {
                plan: rel.clone().into_plan(),
                cost,
                rows: rel.estimated_rows,
            });
        }
        
        // DP 迭代：从小到大构建连接
        for size in 2..=n {
            for mask in Self::all_subsets_of_size(n, size) {
                let mut best_state = None;
                
                // 尝试所有可能的分割方式
                for sub_mask in Self::proper_subsets(mask) {
                    let other_mask = mask ^ sub_mask;
                    
                    if let (Some(left), Some(right)) = (dp.get(&sub_mask), dp.get(&other_mask)) {
                        let join_cost = self.estimate_join_cost(left, right);
                        let total_cost = left.cost + right.cost + join_cost;
                        
                        if best_state.as_ref().map_or(true, |s: &JoinState| total_cost < s.cost) {
                            best_state = Some(JoinState {
                                plan: self.create_join_node(&left.plan, &right.plan),
                                cost: total_cost,
                                rows: self.estimate_join_rows(left.rows, right.rows),
                            });
                        }
                    }
                }
                
                if let Some(state) = best_state {
                    dp.insert(mask, state);
                }
            }
        }
        
        // 返回最优计划
        let full_mask = (1u64 << n) - 1;
        dp.get(&full_mask)
            .map(|s| s.plan.clone())
            .unwrap_or_else(|| self.build_left_deep_tree(joins))
    }
}
```

---

## 5. 测试策略

### 5.1 条件函数测试

```rust
#[test]
fn test_if_function_translation() {
    let sparql = r#"
        SELECT (IF(?salary > 50000, "High", "Normal") AS ?level)
        WHERE { ?emp :salary ?salary }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("CASE WHEN"));
    assert!(sql.contains("THEN"));
    assert!(sql.contains("ELSE"));
}

#[test]
fn test_coalesce_function_translation() {
    let sparql = r#"
        SELECT (COALESCE(?mobile, ?home, "N/A") AS ?phone)
        WHERE { ?emp :mobile ?mobile ; :home ?home }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("COALESCE"));
}
```

### 5.2 GeoSPARQL 度量函数测试

```rust
#[test]
fn test_geof_distance_translation() {
    let sparql = r#"
        SELECT (geof:distance(?wkt1, ?wkt2) AS ?dist)
        WHERE { ?a :location ?wkt1 . ?b :location ?wkt2 }
    "#;
    
    let sql = engine.translate(sparql).unwrap();
    assert!(sql.contains("ST_Distance"));
    assert!(sql.contains("ST_GeomFromText"));
}
```

### 5.3 优化器测试

```rust
#[test]
fn test_cost_based_join_reorder() {
    // 测试 3 表 Join 时选择了最优顺序
    let plan = optimizer.optimize(/* 3-way join */);
    
    // 验证小表在前（作为驱动表）
    let first_table = get_first_table(&plan);
    assert_eq!(first_table, "small_table");
}
```

---

## 6. 实现计划

### 6.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/parser/ir_converter.rs` | 修改 | 添加 IF/COALESCE 解析 |
| `src/sql/flat_generator.rs` | 修改 | 添加条件/度量函数 SQL 生成 |
| `src/optimizer/stats_collector.rs` | 新建 | PostgreSQL 统计信息采集 |
| `src/optimizer/cost_model.rs` | 新建 | 成本估算模型 |
| `src/optimizer/index_advisor.rs` | 新建 | 索引推荐 |
| `src/optimizer/join_reorder.rs` | 新建 | Join 顺序优化 |
| `src/optimizer/mod.rs` | 修改 | 导出新增模块 |

### 6.2 开发顺序

1. **Step 1**: 实现条件函数解析 (IF, COALESCE)
2. **Step 2**: 实现条件函数 SQL 生成
3. **Step 3**: 实现 GeoSPARQL 度量函数解析与生成
4. **Step 4**: 实现 StatsCollector 统计信息采集
5. **Step 5**: 实现 CostModel 成本模型
6. **Step 6**: 实现 IndexAdvisor 索引推荐
7. **Step 7**: 实现 JoinReorderOptimizer (可选增强)

---

**文档结束**
