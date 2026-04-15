这份详尽的 `requirement.md` 文档在原有基础上进行了深度重构。它不再仅仅是一个代码结构说明，而是围绕 **OBDA (基于本体的数据访问)** 的核心逻辑——即如何利用关系型数据库的约束（PK/FK/NotNull）来“消除”图查询带来的性能损耗。

---

# rs-ontop-core 开发需求文档 (Requirement)

## 1. 业务目标与核心逻辑
`rs-ontop-core` 的目标是实现一个 **Virtual RDF 引擎**。其核心逻辑不是将数据转为三元组，而是通过 **符号替换 (Unfolding)** 和 **关系代数优化 (Optimization)**，将 SPARQL 实时转换为高性能的 PostgreSQL 语句。

### 核心指标
* **零数据搬运**：数据始终保留在 PostgreSQL 中。
* **推理性能**：重写过程（从 SPARQL 到 SQL）的延迟应小于 **1ms**。
* **生成的 SQL 质量**：对于典型的星型路径查询，生成的 SQL 必须消除冗余的自联接（Self-Join）。

---

## 2. 详细模块需求

### 模块 A: `parser` (前端适配器)
**职责**：将外部 SPARQL 抽象语法树转换为内部逻辑算子树 (IQ Tree)。
* **输入**：`oxisqrql::algebra::GraphPattern`。
* **功能点**：
    * **变量提取**：准确识别 SPARQL 中的投影变量与 BGP (基本图模式) 变量。
    * **算子映射**：将 `OPTIONAL` 映射为 `LeftJoin`，`UNION` 映射为 `Union` 算子。
    * **过滤器提取**：将 `FILTER` 语句转化为内部的 `Expr` 表达式。

### 模块 B: `mapping` (映射与 URI 引擎)
**职责**：管理本体概念与物理数据库表的绑定关系。
* **数据结构**：
    * **URI 模板**：支持 `http://user/{id}` 格式，实现数据库主键与 RDF 资源标识符的转换。
    * **类型映射**：支持将 SQL 类型（如 `TIMESTAMP`, `INTEGER`）对齐到 RDF XSD 类型。
* **方法**：
    * `unfold(predicate)`：查找 R2RML 定义，返回该谓词对应的 SQL 源码或物理表名。

### 模块 C: `optimizer` (重写引擎 - 核心)
**职责**：执行基于规则的迭代优化，这是复刻 Ontop 能力的关键。
* **核心组件：Substitution Manager (变量替换器)**：
    * 管理变量与物理列的绑定（如 `?s -> users.user_id`）。
    * 实现 **MGU (最一般统一算子)**，确保在 Join 时变量逻辑一致。
* **优化 Pass 规则清单**：
    1.  **自联接消除 (Self-Join Elimination)**：检测到两个 `TableScan` 来自同一张表且连接条件为主键时，合并为单次扫描。
    2.  **外键消除 (FK-based Elimination)**：若 Join 仅用于检查存在性（且不读取被关联表的非键列），利用外键约束直接删除该 Join。
    3.  **谓词下推 (Predicate Pushdown)**：将 `Filter` 尽可能移动至 `TableScan` 节点，形成 SQL 的 `WHERE` 子句。
    4.  **并集提升 (Union Lifting)**：将底层的 `Union` 算子向上层移动，简化 Join 逻辑。

### 模块 D: `codegen` (SQL 序列化器)
**职责**：针对 PostgreSQL 生成最终 SQL。
* **功能点**：
    * **子查询扁平化 (Flattening)**：尽可能消除不必要的嵌套 `SELECT`，生成扁平的 `JOIN` 语句。
    * **别名管理**：自动生成不冲突的表别名（如 `t1`, `t2`）。
    * **方言适配**：利用 PostgreSQL 特有的操作符进行优化。

---

## 3. 关键数据流 (Data Flow)



1.  **解析期**：`SPARQL` -> `Initial IQ Tree`（包含未展开的谓词）。
2.  **展开期**：通过 `Mapping` 和 `Substitution`，将谓词替换为 `TableScan`（物理表）。
3.  **优化期 (固定点迭代)**：重复运行所有优化 Pass，直到 IQ Tree 的结构不再发生变化。
4.  **生成期**：遍历最终树，输出 `PostgreSQL` 兼容的 SQL 字符串。

---

## 4. 阶段性开发计划 (Roadmap)

| 阶段 | 目标 | 关键产出 |
| :--- | :--- | :--- |
| **Phase 1** | 骨架搭建 | 定义 `LogicNode` 枚举、`Expr` 表达式及基础的 SQL 拼接逻辑。 |
| **Phase 2** | 符号重写 (Soul) | 实现 **Substitution Manager** 和 **自联接消除** 规则。 |
| **Phase 3** | 约束优化 | 引入 `DbMetadata`，利用主外键进行 **Join 消除** 和 **Left-to-Inner Join** 转换。 |
| **Phase 4** | 插件集成 | 使用 `pgrx` 将引擎打包为 PostgreSQL 扩展，支持直接执行 SPARQL 函数。 |

---
## 5.本体元数据查询
@prefix : <http://example.org/hr#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

### 1. 类层次关系 (Hierarchy)
:Employee rdf:type owl:Class .
:Manager rdfs:subClassOf :Employee .  # 经理是员工的一种继承关系

### 2. 数据属性与约束 (Data Properties)
:empId rdf:type owl:DatatypeProperty , owl:FunctionalProperty ; # 函数属性：一个员工只有一个ID
       rdfs:domain :Employee ;
       rdfs:range xsd:integer .

### 3. 对象属性与对象关系 (Object Properties)
:worksIn rdf:type owl:ObjectProperty ;
         rdfs:domain :Employee ;      # 关系的起点是员工
         rdfs:range :Department .     # 关系的终点是部门

:hasManager rdf:type owl:ObjectProperty ;
            owl:inverseOf :manages ;  # 反向关系：A的经理是B，等同于B管理A
            rdfs:domain :Employee ;
            rdfs:range :Manager .



###5.1. 为什么它是标准的？
这个例子严格遵循了 W3C 的核心规范：
* **RDF/Turtle 语法**：使用 `@prefix` 定义命名空间，使用 `;` 分隔同一主语的多个谓词，符合 **RDF 1.1 Turtle** 规范。
* **OWL 2 语义**：使用了 `owl:Class`、`owl:DatatypeProperty` 和 `owl:ObjectProperty`。这是 **OWL 2 Web Ontology Language** 的标准组件，用于区分“属性的值是字面量（如字符串）”还是“属性的值是另一个资源（如员工）”。
* **RDFS 基础**：使用 `rdfs:domain` 和 `rdfs:range`。这是 **RDF Schema** 规范中定义的词汇，用于声明属性的逻辑约束。


###5.2. 本体关系的“元数据”表现形式
你之前问到本体关系如何表现，在标准规范中，它们主要通过以下三种逻辑关系呈现：

#### A. 分类关系 (Taxonomy)
这是最基础的关系，表现为树状结构。
* **规范词汇**：`rdfs:subClassOf`。
* **业务意义**：如果 A 是 B 的子类，那么所有属于 A 的实例在逻辑上都自动属于 B。


#### B. 关联关系 (Association)
表现为图中节点之间的边。
* **规范词汇**：`owl:ObjectProperty`。
* **业务意义**：它定义了两个类之间的语义连接，例如 `:Employee` 通过 `:hasManager` 关联到另一个 `:Employee`。

#### C. 约束与特征 (Constraints/Characteristics)
这是你的 `rs-ontop-core` 进行 **Join 消除** 的关键元数据。
* **规范词汇**：`owl:FunctionalProperty`。
* **逻辑含义**：这意味着对于任何给定的个体，该属性只能有一个唯一的值。

---

###5.3. 本体关系的元数据总结表

| 关系维度 | W3C 规范词汇 | 在你的案例（TC-01）中如何体现？ |
| :--- | :--- | :--- |
| **层级** | `rdfs:subClassOf` | 经理也是员工，查询员工时自动包含经理。 |
| **范围** | `rdfs:domain / range` | 只要有 `firstName`，主语就一定是员工。 |
| **特性** | `owl:FunctionalProperty` | **核心：** 员工 ID 是唯一的，这是合并 SQL 表的关键。 |
| **反向** | `owl:inverseOf` | “管理”的反向是“被管理”，只需定义一次映射。 |


既然我们已经对齐了本体（Ontology）的基础定义，下面我通过一个具体的**业务场景例子**，展示本体如何表现类与类、属性与类之间的复杂关系，以及它如何指导你的 `rs-ontop-core` 进行 SQL 优化。

#### 5.3.1. 业务场景：公司组织架构
假设我们要表现“员工”、“经理”以及“部门”之间的关系。

---

####5.3.2. 本体定义（Turtle 格式）
这段代码不仅定义了实体，还定义了**逻辑约束**：

```turtle
@prefix : <http://example.org/hr#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

### 1. 类层次关系 (Hierarchy)
:Employee rdf:type owl:Class .
:Manager rdfs:subClassOf :Employee .  # 经理是员工的一种继承关系

### 2. 数据属性与约束 (Data Properties)
:empId rdf:type owl:DatatypeProperty , owl:FunctionalProperty ; # 函数属性：一个员工只有一个ID
       rdfs:domain :Employee ;
       rdfs:range xsd:integer .

### 3. 对象属性与对象关系 (Object Properties)
:worksIn rdf:type owl:ObjectProperty ;
         rdfs:domain :Employee ;      # 关系的起点是员工
         rdfs:range :Department .     # 关系的终点是部门

:hasManager rdf:type owl:ObjectProperty ;
            owl:inverseOf :manages ;  # 反向关系：A的经理是B，等同于B管理A
            rdfs:domain :Employee ;
            rdfs:range :Manager .
```

---

### 5.4 这些关系如何表现“本体之间的联系”？

在你的 100 条案例测试中，本体关系通过以下三种方式转化成 SQL 逻辑：

#### A. 通过 `rdfs:subClassOf` 实现隐式查询
* **SPARQL**: `?s a :Employee`
* **本体关系**: 经理（`:Manager`）是员工的子类。
* **SQL 表现**: 你的核心引擎会自动生成一个 `UNION`，不仅查询 `employees` 表，还会查询 `managers` 表（如果它们在数据库中是分开存储的话）。

#### B. 通过 `owl:FunctionalProperty` 实现 **Join 消除** (TC-01 核心)
* **SPARQL**: `{ ?s :firstName ?f ; :empId ?id }`
* **本体关系**: `:empId` 是 `FunctionalProperty`（唯一性约束）。
* **SQL 表现**: 优化器知道对于同一个 `?s`，`firstName` 和 `empId` 必然来自同一行数据。它会将原本可能的两个子查询合并为：
    `SELECT first_name, emp_id FROM employees WHERE ...`

#### C. 通过 `owl:inverseOf` 实现语义等价
* **SPARQL**: `?manager :manages ?emp`
* **本体关系**: `:manages` 是 `:hasManager` 的反向属性。
* **SQL 表现**: 如果你的映射文件只定义了 `:hasManager` 对应 `employees.manager_id` 列，引擎会自动转换查询方向，让你通过“被管理者”的表找到“管理者”，而不需要你在映射里重复写两遍逻辑。

---

### 5.5. 总结表：关系类型与 SQL 映射

| 本体关系类型 | 表现方式 | 对 `rs-ontop-core` 的意义 |
| :--- | :--- | :--- |
| **分类 (Taxonomy)** | `subClassOf` | 决定了是否需要 `UNION` 多个表 |
| **关联 (Association)** | `ObjectProperty` | 决定了 SQL 中的 `JOIN` 路径 |
| **约束 (Constraint)** | `FunctionalProperty` | **Join 消除** 的逻辑开关 |
| **等价 (Equivalence)** | `equivalentClass` | 允许不同 URI 指向同一张物理表 |

---

### 💡 下一步建议
在你的 `src/lib.rs` 中，为了处理这些关系，你需要一个**元数据缓存**。

**你想让我为你写一个简单的 `OntologyIndex` 结构体吗？** 它可以存储这些 `subClassOf` 和 `FunctionalProperty` 标记，这样当你的 `spargebra` 解析出属性时，就能立刻判断是否可以进行 Join 消除。
---

## 6. 验收标准
1.  **正确性**：生成的 SQL 执行结果必须与标准 RDF 三元组查询语义一致。
2.  **简洁性**：对于查询同一张表多个字段的 SPARQL，生成的 SQL 不得包含针对该表的多次 Self-Join。
3.  **鲁棒性**：能够处理深层嵌套的 `OPTIONAL` 和复杂的 `FILTER` 逻辑。

---

这份文档现在明确了 **Substitution Manager** 的核心地位，并详细列出了基于 **PostgreSQL 约束** 的优化规则，这正是实现高性能 Ontop 重写器的关键路径。

**下一步建议：**
功能点,描述,重要程度
URI 反向解析,将输入的 URI 常量直接转化为 SQL 过滤条件,⭐⭐⭐⭐⭐
TBox 推理,支持基于本体继承关系的查询自动扩展,⭐⭐⭐⭐
函数转换映射,支持 SPARQL 内置函数（String/Math/Date）到 PG 的转换,⭐⭐⭐⭐
三值逻辑对齐,处理 SQL NULL 与 RDF 存在性之间的细微差别,⭐⭐⭐
