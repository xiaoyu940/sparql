这份 `architecture.md` 文件是基于 Ontop 的核心理论（OBDA）并结合 Rust 的工程特性（代数数据类型、所有权、模式匹配）重新设计的完整架构说明。

---

# rs-ontop-core 系统架构设计 (Architecture)

## 1. 概述 (Overview)
`rs-ontop-core` 是一个高性能的 **基于本体的数据访问 (OBDA)** 引擎。它不通过搬运数据生成三元组，而是通过**虚拟化**技术，将 SPARQL 查询实时重写为针对 PostgreSQL 优化的 SQL。其核心目标是复刻 Ontop 的 SQL 优化能力，并利用 Rust 提供极低的推理延迟。

---

## 2. 系统分层架构 (Layered Architecture)



### 2.1 接入层 (Parser Layer)
* **职责**：解析输入并生成初始逻辑计划。
* **核心组件**：基于 `oxisqrql` 的适配器。
* **输出**：包含 `IntensionalData`（本体谓词占位符）的初始 `LogicNode` 树。

### 2.2 语义展开层 (Unfolding Layer)
* **职责**：执行“图”到“关系”的映射转换。
* **核心组件**：`SubstitutionManager`（变量替换管理器）。
* **逻辑**：根据 R2RML 映射，将本体类/属性替换为物理表和列。

### 2.3 优化层 (Optimizer Layer)
* **职责**：执行多轮次算子重写。
* **核心逻辑**：基于规则的优化 (RBO)，高度依赖 PostgreSQL 的约束（PK/FK）。
* **主要规则**：自联接消除 (Self-Join Elimination)、谓词下推 (Pushdown)、并集提升 (Union Lifting)。

### 2.4 生成层 (Codegen Layer)
* **职责**：将优化后的物理算子树序列化为 SQL 字符串。
* **特色**：子查询扁平化处理，确保生成符合人类阅读习惯的高效 SQL。

---

## 3. 核心模块与中间表示 (Core Modules & IR)

### 3.1 算子定义 (IQ Operators)
采用 Rust 的 `enum` 定义 **中间查询 (Intermediate Query, IQ)** 算子：

```rust
pub enum LogicNode {
    /// 投影、别名与计算列
    Construction {
        projected_vars: Vec<String>,
        bindings: HashMap<String, Expr>,
        child: Box<LogicNode>,
    },
    /// N 叉连接算子，便于进行 Join 重排
    Join {
        children: Vec<LogicNode>,
        condition: Option<Expr>,
        join_type: JoinType,
    },
    /// 物理表扫描，携带数据库约束信息
    ExtensionalData {
        table: String,
        columns: HashMap<String, String>, // 变量 -> 物理列
        metadata: Arc<TableMetadata>,     // 包含 PK/FK/NotNull
    },
    /// 尚未展开的逻辑谓词节点
    IntensionalData {
        predicate: String,
        args: Vec<Term>,
    },
    Filter {
        expression: Expr,
        child: Box<LogicNode>,
    },
    Union(Vec<LogicNode>),
}
```

### 3.2 变量替换系统 (Substitution System)
这是实现自联接消除的数学基础。通过维护 `Variable -> Column` 的绑定，识别不同三元组是否指向同一物理行。



---

## 4. 优化 pass 序列 (Optimization Passes)

引擎按顺序执行以下 Pass 以达到最优解：

1.  **Unfolding Pass**: 基于 `MappingStore` 递归替换 `IntensionalData`。
2.  **Structural Optimization**:
    * **Join Linearization**: 将深层嵌套的 Join 转换为扁平的列表结构。
    * **Self-Join Elimination**: 匹配相同表名且主键对齐的节点进行物理合并。
3.  **Semantic Optimization**:
    * **Redundant Join Elimination**: 利用外键 (FK) 约束，若不涉及非键列则删除该 Join。
    * **Left-to-Inner Join**: 结合 `NOT NULL` 约束将左连接安全转化为内连接。
4.  **Predicate Pushdown**: 将 `Filter` 条件尽可能压入 `TableScan` 节点，形成 SQL 的 `WHERE` 子句。

---

## 5. 项目目录规划 (Crate Structure)

```text
见doc/architecture/WORKSPACE_GUIDE.md
```

---

## 6. 技术优势 (Rust Advantage)
* **强类型枚举策略**：利用 Rust 的模式匹配，优化逻辑比 Java 实现更直观、更易维护。
* **无 GC 延迟**：对于作为 PostgreSQL 插件运行的场景，Rust 提供的微秒级重写延迟能够保证极高的吞吐量。
* **内存布局优化**：通过 `Arc` 共享元数据，避免在每个算子节点中重复存储庞大的表结构信息。

---

这份架构文档现在包含了 Ontop 的核心灵魂（变量替换、约束优化）以及 Rust 的工程实现路径。
