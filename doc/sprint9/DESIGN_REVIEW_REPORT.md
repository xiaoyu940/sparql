# Sprint 9 设计文档评审报告

> **评审日期**: 2026-04-02  
> **评审范围**: P0/P1/P2 设计文档 vs 现有代码实现  
> **评审结论**: 设计合理，与现有架构兼容，可进入实现阶段

---

## 1. 总体评估

### 1.1 架构兼容性 ✓

设计文档与现有代码架构**完全兼容**：

- **IR 层**: `PropertyPath` 枚举已在 `src/ir/node.rs:162-179` 完整定义（包含 Star/Plus/Optional/Sequence/Alternative/Inverse/Negated/Predicate）
- **Path 节点**: `LogicNode::Path` 已在 `src/ir/node.rs:98-102` 定义
- **Unfolding 框架**: `UnfoldingPass` 已在 `src/optimizer/rules/unfolding.rs` 实现，可扩展支持 Path 展开
- **函数框架**: `Expr::Function` 和 `translate_expression` 已支持函数扩展

### 1.2 实现复杂度评估

| 阶段 | 预计工作量 | 风险等级 |
|------|-----------|----------|
| P0 | 中等 (3-4 天) | 低 |
| P1 | 低 (1-2 天) | 低 |
| P2 | 中等 (2-3 天) | 中 (递归 CTE) |

---

## 2. 详细评审

### 2.1 P0: Property Path 展开

#### 现状对比

| 设计文档计划 | 现有代码状态 | 差距 |
|-------------|-------------|------|
| `PathUnfolder` 模块 | ❌ 不存在，需新建 | 需要实现 |
| `PathMappingResolver` | ❌ 不存在，需新建 | 需要实现 |
| `PathJoinGenerator` | ❌ 不存在，需新建 | 需要实现 |
| `UnfoldingPass` 集成 | ⚠️ 部分存在，需扩展 | 需要添加 Path 处理分支 |

#### 关键代码位置

```rust
// 现有 UnfoldingPass 处理逻辑 (src/optimizer/rules/unfolding.rs:66-207)
// 需要添加对 LogicNode::Path 的处理：

impl OptimizerPass for UnfoldingPass {
    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            // ... 现有分支
            
            // [S9-P0] 新增：Path 节点展开
            LogicNode::Path { subject, path, object } => {
                // 调用 PathUnfolder 展开为 Join/Union
            }
        }
    }
}
```

#### 设计调整建议

1. **路径展开调用点**: 建议在 `UnfoldingPass` 中添加 Path 处理分支，而非单独 Pass
   - 原因：路径展开本质也是 Intensional → Extensional 转换
   - 与设计文档一致

2. **别名生成策略**: 设计文档中的 `{table_name}_path{step_idx}_{path_id}` 可行
   - 需确保与现有 `AliasManager` 协调

3. **Join 条件生成**: 现有 `create_join_condition` (ir_converter.rs:649) 使用 `left_table`/`right_table` 前缀
   - 路径展开应遵循相同约定

#### 验证点

- [ ] `PathUnfolder::unfold_sequence` 生成的 Join 条件与现有 Join 逻辑兼容
- [ ] 多步路径生成的表别名不冲突
- [ ] Union 展开后的 SQL 格式正确

---

### 2.2 P1: 函数扩展

#### 现状对比

| 函数 | flat_generator 状态 | 设计文档要求 | 实现难度 |
|------|-------------------|-------------|----------|
| `IF()` | ❌ 未实现 | `CASE WHEN ... THEN ... ELSE ... END` | 低 |
| `COALESCE()` | ❌ 未实现 | `COALESCE(...)` | 低 |
| `geof:distance` | ❌ 未实现 | `ST_Distance(ST_GeomFromText(...))` | 低 |
| `geof:buffer` | ❌ 未实现 | `ST_Buffer(ST_GeomFromText(...))` | 低 |
| `NOW()` | ✅ 已实现 (line 1255) | `CURRENT_TIMESTAMP` | 已完成 |

#### 现有函数处理框架 (flat_generator.rs:1199-1286)

```rust
Expr::Function { name, args } => {
    match name.to_uppercase().as_str() {
        // [S8-P2] 已有函数处理...
        "NOW" => Ok("CURRENT_TIMESTAMP".to_string()),
        "GEOF:SFWITHIN" => Ok("ST_Within(...)")
        
        // [S9-P1] 需要添加：
        // "IF" => ...
        // "COALESCE" => ...
        // "GEOF:DISTANCE" => ...
        // "GEOF:BUFFER" => ...
        
        _ => Ok(format!("{}({})", name, args_sql.join(", ")))
    }
}
```

#### 函数解析支持

`ir_converter.rs:1470-1497` 已支持通用函数解析，只需确保新函数名被正确识别：

```rust
// 现有函数解析逻辑支持 IF/COALESCE 格式
let func_regex = regex::Regex::new(r"^([A-Za-z_][A-Za-z0-9_]*:?[A-Za-z_][A-Za-z0-9_]*)\((.*)\)$").ok()?;
```

#### 实现建议

1. **IF 函数**: 直接添加 SQL 生成规则，无需修改解析器
2. **COALESCE**: 同上，已支持可变参数解析
3. **GeoSPARQL**: 与现有 SFWITHIN 等函数处理方式一致

---

### 2.3 P2: 高级功能

#### 路径修饰符

| 修饰符 | 设计策略 | 代码现状 | 评估 |
|--------|---------|---------|------|
| `?` | LEFT JOIN + COALESCE | ⚠️ 需新建 | 可行 |
| `*` | 递归 CTE | ⚠️ 需新建 | 可行，需测试性能 |
| `+` | 递归 CTE (min_depth=1) | ⚠️ 需新建 | 可行 |

#### 日期时间函数

| 函数 | SQL 映射 | 实现难度 | 备注 |
|------|---------|---------|------|
| `YEAR()` | `EXTRACT(YEAR FROM ...)` | 低 | 与 NOW() 类似 |
| `MONTH()` | `EXTRACT(MONTH FROM ...)` | 低 | 同上 |
| `DAY()` | `EXTRACT(DAY FROM ...)` | 低 | 同上 |
| `HOURS()` | `EXTRACT(HOUR FROM ...)` | 低 | 同上 |
| `MINUTES()` | `EXTRACT(MINUTE FROM ...)` | 低 | 同上 |
| `SECONDS()` | `EXTRACT(SECOND FROM ...)` | 低 | 同上 |

**实现建议**: 参照 `NOW()` 在 flat_generator.rs:1255 的实现方式

#### 查询缓存

| 组件 | 设计文档 | 代码现状 | 依赖 |
|------|---------|---------|------|
| `QueryCache` 结构 | 完整设计 | ❌ 不存在 | 需添加 `lru` crate |
| 缓存集成 | Engine 层 | ⚠️ 需修改 | 需侵入 Engine |

**依赖添加**:
```toml
[dependencies]
lru = "0.12"
```

---

## 3. 关键发现与风险

### 3.1 已确认的实现基础

1. **IR 层完备**: `PropertyPath` 和 `LogicNode::Path` 已完整定义
2. **解析器就绪**: `property_path_parser.rs` 已能解析所有路径类型
3. **函数框架就绪**: `parse_filter_expr` 和 `translate_expression` 支持扩展
4. **SQL 生成器就绪**: `FlatSQLGenerator` 架构支持新节点类型

### 3.2 需要新建的模块

| 模块 | 文件路径 | 复杂度 |
|------|---------|--------|
| `PathUnfolder` | `src/rewriter/path_unfolder.rs` | 中 |
| `PathMappingResolver` | `src/rewriter/path_mapping_resolver.rs` | 低 |
| `PathJoinGenerator` | `src/sql/path_join_generator.rs` | 低 |
| `RecursivePathGenerator` (P2) | `src/sql/recursive_path_generator.rs` | 中 |
| `QueryCache` (P2) | `src/cache/query_cache.rs` | 中 |
| `StatsCollector` (P1) | `src/optimizer/stats_collector.rs` | 中 |
| `CostModel` (P1) | `src/optimizer/cost_model.rs` | 低 |

### 3.3 集成点

1. **UnfoldingPass**: 需要添加 `LogicNode::Path` 处理分支
2. **IRConverter**: 可能需要添加属性路径到 Path 节点的转换
3. **FlatSQLGenerator**: 需要确认 Path 节点如何最终生成 SQL
4. **Engine**: P2 缓存需要修改入口函数

---

## 4. 改进建议

### 4.1 P0 路径展开优化建议

**建议 1**: 自连接消除复用
```rust
// 在 PathUnfolder 展开后，复用现有自连接消除逻辑
// 序列路径 :manager/:name 可能生成 employees JOIN employees
// 应复用 optimizer 中的自连接消除规则
```

**建议 2**: 渐进式展开
```rust
// 先实现简单路径（单表自引用），再实现跨表路径
// 优先级: Inverse > Sequence (单表) > Alternative > Sequence (跨表)
```

### 4.2 P1 函数扩展建议

**建议**: 统一函数名大小写处理
```rust
// 现有代码使用 name.to_uppercase().as_str() 匹配
// 确保 IF/COALESCE/DISTANCE/BUFFER 都注册为大写形式
```

### 4.3 P2 缓存设计建议

**建议**: 分层缓存键设计
```rust
// 使用 (SPARQL_hash, mapping_version) 作为复合键
// 避免映射变更后仍命中旧缓存
```

---

## 5. 实现顺序建议（修订）

基于代码审查，建议调整实现顺序：

### Week 1: P0 核心

```
Day 1: PathMappingResolver (解析 predicate 到表/列)
Day 2: PathUnfolder::unfold_predicate + unfold_inverse
Day 3: PathUnfolder::unfold_sequence (单表场景)
Day 4: PathUnfolder::unfold_sequence (跨表场景) + PathJoinGenerator
Day 5: PathUnfolder::unfold_alternative + UnfoldingPass 集成
```

### Week 2: P1 功能

```
Day 1: flat_generator.rs 添加 IF/COALESCE SQL 生成
Day 2: flat_generator.rs 添加 geof:distance/buffer SQL 生成
Day 3-4: StatsCollector + CostModel (可选，可延后)
Day 5: 测试与调优
```

### Week 3: P2 增强

```
Day 1-2: ? (Optional) 路径修饰符
Day 3-4: * / + 递归 CTE 实现
Day 5: 日期时间函数 + 缓存基础
```

---

## 6. 测试就绪度

Python 测试框架已就绪，测试用例可直接编写：

| 测试类型 | 框架支持 | 示例位置 |
|---------|---------|---------|
| SPARQL→SQL 翻译 | ✅ | `framework.translate_sparql()` |
| SQL 执行对比 | ✅ | `TestCaseBase.sparql_query()` vs `sql_query()` |
| 结果比对 | ✅ | `compare_results()` |

建议测试数据准备：
```sql
-- 确保 employees 表有 manager_id 列用于路径测试
ALTER TABLE employees ADD COLUMN IF NOT EXISTS manager_id INTEGER;
UPDATE employees SET manager_id = ... WHERE ...;
```

---

## 7. 结论

### 7.1 设计可行性: ✅ 通过

设计文档与现有代码架构完全兼容，无架构冲突。

### 7.2 关键成功因素

1. **P0**: PathUnfolder 与 UnfoldingPass 的集成点需仔细测试
2. **P1**: 函数 SQL 生成规则添加即可，风险低
3. **P2**: 递归 CTE 的性能和正确性需重点测试

### 7.3 建议行动

1. **立即开始 P0 实现** - 核心路径展开逻辑
2. **同步准备测试数据** - 确保有 manager_id 等测试所需列
3. **P1 可与 P0 并行** - 函数扩展独立性强

---

**评审完成，建议批准进入实现阶段。**
