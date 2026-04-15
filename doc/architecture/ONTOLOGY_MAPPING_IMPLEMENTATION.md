# RS Ontop Core 本体映射实现说明

## 1. 文档目的

本文档说明 `rs_ontop_core` 当前“本体 + 映射”在代码中的实现方式，覆盖：

- 本体与映射的数据结构
- 映射加载与引擎刷新流程
- 查询执行时的重写链路
- 对外观测接口
- 当前已知限制与改进方向

---

## 2. 核心数据结构

实现文件：`src/mapping.rs`

### 2.1 `MappingStore`

`MappingStore` 是运行时统一容器，包含三部分：

- `classes: HashMap<String, OntologyClass>`
- `properties: HashMap<String, OntologyProperty>`
- `mappings: HashMap<String, Vec<MappingRule>>`

其中 `mappings` 使用 `Vec<MappingRule>`，表示同一个谓词允许多个映射规则。

### 2.2 语义对象

- `OntologyClass`：类 IRI、标签、注释、父类
- `OntologyProperty`：属性 IRI、类型（Object/Datatype）、domain/range、父属性、inverseOf、functional 标记
- `MappingRule`：谓词到物理表映射
  - `predicate`
  - `table_name`
  - `subject_template`
  - `position_to_column`（位置 -> 列名，常见为 object 位置 1）

---

## 3. 映射加载流程

### 3.1 主路径：从数据库加载 R2RML

实现文件：

- `src/lib.rs` -> `refresh_engine_from_spi`
- `src/mapping/r2rml_loader.rs` -> `R2RmlLoader::load_from_database`
- `src/mapping/r2rml_parser.rs` -> `parse_r2rml` / `to_internal_mapping`

流程：

1. `ontop_refresh()` 进入 SPI 事务。
2. `refresh_engine_from_spi` 调用 `R2RmlLoader::load_from_database(client)`。
3. Loader 从 `public.ontop_r2rml_mappings` 读取 `ttl_content`。
4. 逐条 TTL 解析为 `R2RmlTriplesMap`，再转换为 `MappingRule`。
5. 合并到 `MappingStore`，构造 `OntopEngine` 并写入全局 `ENGINE`。

### 3.2 本体 Turtle 导入

实现入口：`ontop_load_ontology_turtle(ttl: &str)`（`src/lib.rs`）

流程：

1. 用 `MappingStore::load_turtle` 做语法解析与基本本体抽取。
2. 将原始 TTL 写入 `ontop_ontology_snapshots`。
3. 调用 `ontop_refresh()` 重建引擎。

---

## 4. 查询时映射与本体如何生效

### 4.1 总体管线

实现文件：`src/lib.rs` -> `OntopEngine::translate`

主流程：

1. SPARQL 解析：`SparqlParserV2::parse`
2. IR 构建：`IRBuilder::build_with_mappings(..., Some(&mappings))`
3. 映射展开：`MappingUnfolder::unfold`
4. TBox 重写：`TBoxRewriter::rewrite`
5. 优化器 passes
6. SQL 生成：`FlatSQLGenerator::new_with_mappings(...).generate`

### 4.2 映射展开（ABox/物理层）

`MappingUnfolder` 当前是对 `UnfoldingPass` 的封装，负责把逻辑谓词展开到可执行的关系表达（表/列）。

### 4.3 TBox 重写（语义层）

实现文件：`src/rewriter/tbox_rewriter.rs`

当前覆盖：

- `rdfs:subClassOf`
- `rdfs:subPropertyOf`

策略：

- 对 `IntensionalData` 节点收集谓词自身及父类/父属性；
- 若有多个候选，重写为 `Union` 分支。

---

## 5. 元数据与映射协同

实现文件：`src/lib.rs` -> `fetch_pg_metadata_with_client`

引擎刷新时同时抓取数据库元数据（列信息等），与 `MappingStore` 一起构建 `OntopEngine`。
查询重写时，IR 构建和 SQL 生成都同时依赖：

- 映射规则（逻辑谓词 -> 物理表列）
- 表元数据（列存在性、后续优化依据）

---

## 6. 对外可观测接口

### 6.1 `ontop_inspect_ontology()`

实现文件：`src/lib.rs`

从 `ENGINE.mappings.classes/properties` 组装 JSON-LD 输出，用于 `/ontology` 路径展示本体结构。

### 6.2 `ontop_translate()` / `ontop_query()`

分别用于：

- 观察 SPARQL 到 SQL 的翻译结果
- 执行翻译后的 SQL 并返回结果

两者都依赖当前 `ENGINE` 中的 `MappingStore`。

---

## 7. 当前限制

1. TBox 重写覆盖仍偏基础，目前主要是父类/父属性展开。
2. R2RML 转内部规则时，部分语义（例如 class assertion object 常量）在现有 `MappingRule` 结构里表达能力有限。
3. 引擎刷新失败时会回退空映射，行为可用但语义能力下降。
4. 多进程 worker 模式下，`ENGINE` 为进程内副本，刷新一致性需要版本机制保障。

---

## 8. 建议演进方向

1. 扩展 `MappingRule` 表达能力（常量 object、subject/object term map 更完整建模）。
2. 提升 TBox 重写覆盖（inverse、domain/range 约束参与重写等）。
3. 增加映射加载与重写链路的结构化指标（加载耗时、命中规则数、重写分支数）。
4. 为多 worker 引入“映射版本号 + 懒刷新”机制，缩小进程间不一致窗口。

---

## 9. 关键代码索引

- `src/mapping.rs`
- `src/mapping/r2rml_loader.rs`
- `src/mapping/r2rml_parser.rs`
- `src/lib.rs`（`refresh_engine_from_spi`, `OntopEngine::translate`, `ontop_load_ontology_turtle`, `ontop_inspect_ontology`）
- `src/ir/builder.rs`
- `src/rewriter/mapping_unfolder.rs`
- `src/rewriter/tbox_rewriter.rs`

