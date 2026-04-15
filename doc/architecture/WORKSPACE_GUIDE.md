# RS Ontop Core 工作空间指南

> **版本**: 0.1.0  
> **更新日期**: 2026-03-29  
> **项目**: PostgreSQL RDF 映射与 SPARQL 查询引擎

---

## 1. 项目概述

RS Ontop Core 是一个基于 Rust 和 pgrx 的 PostgreSQL 扩展，提供：
- **RDF 映射**: 将关系数据映射为 RDF 图
- **SPARQL 查询**: 支持 SPARQL 1.1 查询语言
- **虚拟知识图谱**: 实时查询关系数据，无需物化 RDF 数据

---

## 2. 目录结构

```
rs_ontop_core/
├── .cargo/              # Cargo 配置
├── tools/               # 工具脚本
├── doc/                 # 项目文档
│   ├── architecture/    # 架构文档
│   ├── sprint1/         # Sprint1 文档
│   └── sprint2/         # Sprint2 文档
├── scripts/             # 构建/验证脚本
├── src/                 # 源代码
│   ├── benchmark/       # 性能基准测试
│   ├── bin/             # 二进制入口
│   ├── codegen/         # SQL 代码生成
│   ├── ir/              # 中间表示 (IR)
│   ├── listener/        # HTTP/SPARQL 服务端
│   ├── mapping/         # RDF 映射管理
│   ├── metadata/        # 数据库元数据
│   ├── optimizer/       # 查询优化器
│   ├── parser/          # SPARQL 解析器
│   ├── sql/             # SQL 生成器
│   └── ...
├── tests/               # 测试套件
│   ├── doc/             # 测试相关文档
│   ├── integration/     # 集成测试
│   ├── output/          # 测试输出文件
│   ├── script/          # 测试脚本 (Python/Shell/SQL)
│   ├── sprint1/         # Sprint1 单元测试
│   └── sprint2/         # Sprint2 单元测试
├── Cargo.toml           # 项目配置
└── rs_ontop_core.control # PostgreSQL 扩展控制文件
```

---

## 3. 核心模块说明

### 3.1 解析器 (Parser)
- **文件**: `src/parser/`
- **功能**: SPARQL 查询解析
- **关键组件**:
  - `sparql_parser_v2.rs`: 主解析器，使用 spargebra
  - `ir_converter.rs`: 将解析结果转换为 IR

### 3.2 中间表示 (IR)
- **文件**: `src/ir/`
- **功能**: 内部查询表示
- **关键类型**: `LogicNode` - 逻辑计划节点

### 3.3 优化器 (Optimizer)
- **文件**: `src/optimizer/`
- **功能**: 查询优化
- **关键规则**:
  - `unfolding.rs`: 映射展开 (Intensional → Extensional)
  - `predicate_pushdown.rs`: 谓词下推

### 3.4 SQL 生成器
- **文件**: `src/sql/`
- **功能**: 将 IR 转换为可执行 SQL
- **关键组件**:
  - `flat_generator.rs`: 扁平 SQL 生成器

### 3.5 HTTP 服务
- **文件**: `src/listener/`
- **功能**: SPARQL HTTP Endpoint
- **关键组件**:
  - `robust.rs`: 主服务端实现
  - `database/streaming_client.rs`: 流式查询执行

---

## 4. 测试组织

### 4.1 Sprint1 测试 (`tests/sprint1/`)
基础功能单元测试：
- `ir_tests.rs`: IR 构造测试
- `parser_v2_tests.rs`: SPARQL 解析测试
- `sql_flat_generator_tests.rs`: SQL 生成测试

### 4.2 Sprint2 测试 (`tests/sprint2/`)
高级功能测试：
- `complex_sparql_tests.rs`: 复杂 SPARQL 查询
- `sprint2_p0_rewrite_tests.rs`: 重写规则测试
- `sparql_accuracy_tests.rs`: 查询准确性验证

### 4.3 集成测试 (`tests/integration/`)
端到端测试：
- `postgresql_integration_test.rs`: PostgreSQL 连接测试
- `complex_sparql_suite.rs`: 50 个复杂场景测试套件
- `sql_execution_tests.rs`: SQL 执行验证
- `sql_result_accuracy_tests.rs`: 结果准确性
- `bulk_verify.rs`: 批量验证
- `performance_benchmarks.rs`: 性能基准
- `stress_tests.rs`: 压力测试

### 4.4 测试脚本 (`tests/script/`)
- `sparql_test_suite.py`: Python 测试套件
- `sparql_result_validation.py`: 结果验证脚本
- `generate_100k_data.sql`: 测试数据生成
- `setup_rdf_mappings.sql`: RDF 映射初始化

### 4.5 Python 结果比对测试 (`tests/python/`)
**新一代测试框架**，用于验证 SPARQL 翻译的正确性：

| 组件 | 说明 |
|------|------|
| `framework.py` | 测试框架基类，提供结果比对逻辑 |
| `run_all_tests.py` | 批量运行所有测试用例 |
| `test_cases/` | 测试用例目录，每个文件一个独立测试 |
| `tests/output/` | 测试报告输出目录（自动创建，JSON/Markdown 格式） |

**测试原理**：
- `sparql_query()`: 构造 SPARQL → 调用 `translate_sparql()` 生成 SQL → 执行 SQL
- `sql_query()`: 构造基准 SQL（黄金标准，不依赖翻译）
- 框架自动比对两个查询的结果（行数、列名、数据内容）

**快速开始**：
```bash
cd tests/python
pip install psycopg2-binary

# 运行单个测试
python test_cases/test_basic_join.py

# 运行所有测试
python run_all_tests.py --password your_password --report
```

---

## 5. 开发工作流

### 5.1 编译
```bash
# 标准编译
cargo build

# 测试编译
cargo test --no-run

# 发布构建
cargo build --release
```

### 5.2 测试
```bash
# Rust 单元测试
cargo test

# 运行特定测试
cargo test test_complex_30

# 运行集成测试 (需要 PostgreSQL)
cargo test --test postgresql_integration_test

# Python 结果比对测试
cd tests/python
python run_all_tests.py --password your_password --report
```

### 5.3 扩展安装 (pgrx)
```bash
# 安装到 PostgreSQL
cargo pgrx install

# 运行嵌入式 PostgreSQL
cargo pgrx run
```

---

## 6. 关键依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| pgrx | 0.11 | PostgreSQL 扩展框架 |
| spargebra | 0.3 | SPARQL 解析 |
| tokio | 1.0 | 异步运行时 |
| serde | 1.0 | 序列化 |
| thiserror | 1.0 | 错误处理 |

---

## 7. 配置说明

### 7.1 Cargo.toml 特性
- `default = ["pg16"]` - 默认 PostgreSQL 16
- `pg12`/`pg13`/`pg14`/`pg15`/`pg16` - 特定版本支持
- `with-embed` - 嵌入式模式

### 7.2 环境变量
- `PGHOST` - PostgreSQL 主机
- `PGPORT` - PostgreSQL 端口
- `PGDATABASE` - 数据库名

---

## 8. 文档索引

### 8.1 架构文档 (`doc/architecture/`)
- `architecture.md` - 总体架构
- `ontop.md` - Ontop 系统概述
- `RDF_MAPPING_ARCHITECTURE.md` - RDF 映射架构
- `sparql-solution.md` - SPARQL 解决方案

### 8.2 Sprint 文档
- `doc/sprint1/` - Sprint1 设计文档
- `doc/sprint2/` - Sprint2 设计文档

### 8.3 测试文档 (`tests/doc/`)
- `CODE_CHECK_REPORT.md` - 代码检查报告
- `CODE_FIX_PLAN.md` - 修复计划
- `CODING_STANDARDS.md` - 编码规范
- `TEST_ENVIRONMENT.md` - 测试环境配置

---

## 9. 常用命令

| 命令 | 说明 |
|------|------|
| `cargo clean` | 清理构建目录 |
| `cargo check` | 快速检查 |
| `cargo clippy` | 静态分析 |
| `cargo fmt` | 代码格式化 |
| `cargo doc` | 生成文档 |
| `cargo test` | 运行测试 |
| `cargo test test_complex_30` | 运行特定测试 |

---

## 10. 注意事项

1. **pgrx 依赖**: 需要 PostgreSQL 开发库
2. **异步代码**: 使用 Tokio 运行时
3. **内存管理**: 遵循 pgrx MemoryContext 规则
4. **错误处理**: 使用 `thiserror` 和 `anyhow`
5. **SQL 生成**: IR 必须经过 `UnfoldingPass` 才能生成 SQL

---

## 11. 最近更新

- 2026-03-29: 修复 `find_logical_op` 括号内逻辑操作符匹配问题
- 2026-03-29: 整理测试目录结构 (sprint1, sprint2, integration)
- 2026-03-29: 创建 tests/output, tests/script, tests/doc 目录

---

**维护者**: RS Ontop Core Team  
**仓库**: rs_ontop_core
