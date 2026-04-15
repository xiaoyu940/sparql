# Sprint 9 设计文档索引

> **版本**: 1.0  
> **创建日期**: 2026-04-02  
> **目录**: `/home/yuxiaoyu/rs_ontop_core/doc/sprint9/`

---

## 文档清单

| 文档 | 优先级 | 内容概述 | 文件大小 |
|------|--------|----------|----------|
| [P0_property_path_design.md](./P0_property_path_design.md) | P0 (最高) | Property Path OBDA 展开设计：反向/序列/选择路径 | 20KB |
| [P1_functions_optimizer_design.md](./P1_functions_optimizer_design.md) | P1 (中) | BIND条件函数、GeoSPARQL度量函数、查询优化器增强 | 30KB |
| [P2_advanced_features_cache_design.md](./P2_advanced_features_cache_design.md) | P2 (低) | 路径修饰符、日期时间函数、查询缓存机制 | 26KB |
| [PYTHON_TEST_PLAN.md](./PYTHON_TEST_PLAN.md) | - | Python 测试框架集成测试计划 | 15KB |
| [DESIGN_REVIEW_REPORT.md](./DESIGN_REVIEW_REPORT.md) | - | 设计文档评审报告 | 10KB |
| [pseudocode.md](./pseudocode.md) | - | 伪代码参考（Sprint 8 已实现 + Sprint 9 计划标记） | 22KB |

---

## Python 测试用例清单

### P0 - Property Path 测试

| 测试文件 | 测试内容 |
|----------|----------|
| [test_sprint9_p0_inverse_001.py](../../tests/python/test_cases/test_sprint9_p0_inverse_001.py) | 反向路径 (^p): Manager自连接, Department跨表 |
| [test_sprint9_p0_sequence_001.py](../../tests/python/test_cases/test_sprint9_p0_sequence_001.py) | 序列路径 (p1/p2): 自连接序列, 跨表序列, 带Filter, 四步序列 |
| [test_sprint9_p0_alternative_001.py](../../tests/python/test_cases/test_sprint9_p0_alternative_001.py) | 选择路径 (p1\|p2): Email\|Phone, 多谓词选择, 跨表选择 |
| [test_sprint9_p0_complex_001.py](../../tests/python/test_cases/test_sprint9_p0_complex_001.py) | 组合路径: 反向+序列, 序列+选择, 嵌套序列 |

### P1 - 函数扩展测试

| 测试文件 | 测试内容 |
|----------|----------|
| [test_sprint9_p1_bind_001.py](../../tests/python/test_cases/test_sprint9_p1_bind_001.py) | BIND条件函数: IF基础, IF嵌套, IF逻辑表达式, COALESCE多参数, COALESCE两参数 |
| [test_sprint9_p1_geosparql_metric_001.py](../../tests/python/test_cases/test_sprint9_p1_geosparql_metric_001.py) | GeoSPARQL度量: geof:distance, geof:buffer, 动态点距离, 带单位缓冲区 |

### P2 - 高级功能测试

| 测试文件 | 测试内容 |
|----------|----------|
| [test_sprint9_p2_path_modifiers_001.py](../../tests/python/test_cases/test_sprint9_p2_path_modifiers_001.py) | 路径修饰符: ? (Optional), * (Star递归CTE), + (Plus递归CTE), 嵌套修饰符 |
| [test_sprint9_p2_datetime_001.py](../../tests/python/test_cases/test_sprint9_p2_datetime_001.py) | 日期时间函数: NOW, YEAR/MONTH/DAY, HOURS/MINUTES/SECONDS, TIMEZONE/TZ, 日期运算 |

---

## 快速导航

### 开发者入口

**如果你刚开始 Sprint 9，请按以下顺序阅读：**

1. **架构背景**: [pseudocode.md](./pseudocode.md) - 了解当前系统状态和 Sprint 9 标记
2. **P0 核心设计**: [P0_property_path_design.md](./P0_property_path_design.md) - 最高优先级功能
3. **测试策略**: [PYTHON_TEST_PLAN.md](./PYTHON_TEST_PLAN.md) - 了解测试用例结构

### 实现者入口

**如果你要开始编码实现：**

- **P0 路径展开**: 阅读 [P0_property_path_design.md](./P0_property_path_design.md) 第3节"模块设计"
- **P1 函数扩展**: 阅读 [P1_functions_optimizer_design.md](./P1_functions_optimizer_design.md) 第2-3节
- **P2 缓存实现**: 阅读 [P2_advanced_features_cache_design.md](./P2_advanced_features_cache_design.md) 第4节

### 测试者入口

**如果你要写测试用例：**

- **测试框架**: [PYTHON_TEST_PLAN.md](./PYTHON_TEST_PLAN.md) - 完整测试计划
- **示例代码**: [P0 测试示例](./PYTHON_TEST_PLAN.md#2-p0-测试用例---property-path)

---

## 关键决策摘要

### P0: Property Path OBDA 展开

| 决策 | 内容 |
|------|------|
| 展开时机 | Unfolding Pass 中展开，将 Path 转为 Join/Union/ExtensionalData |
| 反向路径 | 交换 subject/object，复用现有展开逻辑 |
| 序列路径 | 生成 N 元 Join 链，每步分配独立别名 |
| 选择路径 | 生成 Union 节点，每个分支独立展开 |
| 核心模块 | `PathUnfolder`, `PathMappingResolver`, `PathJoinGenerator` |

### P1: 函数扩展与优化器

| 功能 | SQL 映射 | 关键文件 |
|------|----------|----------|
| IF() | `CASE WHEN ... THEN ... ELSE ... END` | `ir_converter.rs`, `flat_generator.rs` |
| COALESCE() | `COALESCE(...)` | 同上 |
| geof:distance | `ST_Distance(ST_GeomFromText(...))` | `flat_generator.rs` |
| geof:buffer | `ST_Buffer(ST_GeomFromText(...))` | 同上 |
| 成本模型 | `pg_stats` + 自定义估算 | `stats_collector.rs`, `cost_model.rs` |

### P2: 高级功能

| 功能 | 实现策略 |
|------|----------|
| `?` (Optional) | LEFT JOIN + COALESCE |
| `*` (Kleene Star) | 递归 CTE (max_depth=10) |
| `+` (Kleene Plus) | 递归 CTE (min_depth=1) |
| NOW() | `CURRENT_TIMESTAMP` |
| YEAR/MONTH/DAY() | `EXTRACT(... FROM ...)` |
| 查询缓存 | 4层 LRU + TTL 缓存 |

---

## 实现顺序建议

### 阶段 1: P0 核心 (Week 1)

```
Day 1-2: PathMappingResolver + 单谓词展开
Day 3: Inverse 路径展开
Day 4-5: Sequence 路径展开 + Join 条件生成
Weekend: Alternative 路径展开 + 测试
```

### 阶段 2: P1 功能 (Week 2)

```
Day 1: IF/COALESCE 解析 + SQL 生成
Day 2: geof:distance/buffer SQL 生成
Day 3-4: StatsCollector + CostModel
Day 5: IndexAdvisor
Weekend: 优化器集成测试
```

### 阶段 3: P2 增强 (Week 3)

```
Day 1: ? (Optional) 路径修饰符
Day 2-3: * / + 递归 CTE 实现
Day 4: 日期时间函数
Day 5: 查询缓存基础
Weekend: 性能测试 + 调优
```

---

## 相关代码位置

| 模块 | 文件路径 |
|------|----------|
| PropertyPath IR | `src/ir/node.rs` |
| 路径解析器 | `src/parser/property_path_parser.rs` |
| IR 转换器 | `src/parser/ir_converter.rs` |
| SQL 生成器 | `src/sql/flat_generator.rs` |
| 递归路径 SQL | `src/sql/path_sql_generator.rs` |
| 展开 Pass | `src/rewriter/unfolding.rs` |
| Python 测试框架 | `tests/python/framework.py` |
| 测试用例目录 | `tests/python/test_cases/` |

---

## 依赖项

### Rust 依赖（Cargo.toml）

```toml
[dependencies]
# 现有依赖...
lru = "0.12"  # P2 缓存模块需要
```

### Python 依赖

```bash
pip install psycopg2-binary
```

---

## 术语表

| 术语 | 说明 |
|------|------|
| OBDA | Ontology-Based Data Access，基于本体的数据访问 |
| Property Path | SPARQL 属性路径，用于导航 RDF 图 |
| Unfolding | 将本体谓词展开为关系表查询的过程 |
| RBO | Rule-Based Optimization，基于规则的优化 |
| CBO | Cost-Based Optimization，基于成本的优化 |
| CTE | Common Table Expression，公用表表达式（SQL） |
| LRU | Least Recently Used，最近最少使用缓存淘汰策略 |
| TTL | Time To Live，缓存存活时间 |

---

**维护者**: RS Ontop Core Team  
**最后更新**: 2026-04-02
