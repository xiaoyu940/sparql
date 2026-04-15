# Sprint 3 集成测试执行流程与原理说明

本文档记录了 `rs-ontop-core` 在 Sprint 3 阶段实现的 SPARQL-to-SQL 转换核心流程，以便后续维护与验证。

---

## 1. 测试环境准备 (Setup)
所有的集成测试（位于本目录下）统一通过 `sprint3_integration.rs` 入口运行。测试依赖于一个模拟的元数据环境：
- **Mock Metadata**: 在 `mod.rs` 中定义，提供了 `test_table` 表及其列（`s, p, o, dept, salary, label, p1, p2, p3`）的映射信息。
- **Mock Schema**: 默认假设三元组模式 `(?s ?p ?o)` 直接对应数据库表中的同名列。

## 2. 核心转换流程 (Execution Pipeline)

### 第一步：SPARQL 解析 (SparqlParserV2)
- **输入**: 原始 SPARQL 1.1 查询字符串。
- **预处理**: 使用 `expand_sparql_shorthand` 展开 `;` 和 `,` 等简写语法。
- **正则提取**: 通过增强型的正则匹配（支持 `|`、`/` 属性路径和 `(...)` 括号）提取三元组模式 `TriplePattern`。
- **结构化输出**: 生成 `ParsedQuery` 结构，包含主题模式、FILTER 条目、聚合函数定义和子查询。

### 第二步：中间表示转换 (IRConverter)
转换器的核心任务是将 SPARQL 逻辑映射为逻辑计划树 (`LogicNode`)：
- **属性路径分解**: 
  - `convert_property_path` 使用状态感知的 `find_logical_op` 识别操作符。
  - `AlternativePath (|)` 转换为 `LogicNode::Union`。
  - `SequencePath (/)` 转换为 `LogicNode::Join`，并自动生成唯一的中间变量（Blank Nodes）来桥接连接。
- **变量映射**: 
  - 通过 `map_var_to_column` 将 SPARQL 变量映射到数据库真实列。
  - **唯一常量化**: 对常量三元组段（如固定谓词）生成带有 UUID 后缀的虚拟映射，防止 Join 过程中的别名冲突。
- **子查询集成**: 递归调用转换逻辑，并通过 `Join` 节点将子查询结果无缝集成到主查询中。

### 第三步：SQL 片段生成与扁平化 (FlatSQLGenerator)
- **Alias 管理**: 使用 `AliasManager` 确保所有子查询、表名和变量在生成的 SQL 中都有唯一的别名（如 `uni_1`, `col_s`）。
- **Join 自动推断**: 生成器会扫描不同子树中的共享变量，自动添加 `INNER JOIN ... ON` 连接条件。
- **Union 扁平化**: 将 `LogicNode::Union` 转换为 `SELECT * FROM (...) UNION ALL (...)` 的子查询形式。
- **表达式翻译**: 完成聚合函数（`COUNT(*)`, `SUM`, `AVG`）和 `FILTER` 操作符到 SQL 标准语法的映射。

## 3. 执行测试的指令 (Running Tests)

使用以下命令运行 Sprint 3 完整的集成测试：
```bash
# 运行所有 Sprint 3 集成测试
cargo test --test sprint3_integration

# 查看详细的 SQL 生成过程（推荐在调试时使用）
cargo test --test sprint3_integration -- --nocapture
```

## 4. 关键改进 (Key Improvements)
- **状态感知检测器**: 成功解决了 IRI 边界符 `<` `>` 被误认为比较操作符的问题。
- **斜杠递归防御**: 解决了 IRI 内部斜杠（如 `http://`）导致的属性路径无限递归问题。
- **嵌套路径支持**: 实现了对带括号的复杂属性路径如 `(<p1>|<p2>)/<p3>` 的完整支持。

---
*Created at: 2026-03-29*
