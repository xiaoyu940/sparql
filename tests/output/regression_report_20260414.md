# 回归测试报告（2026-04-14）

## 1. 执行范围

本轮执行了两套回归：

- `tests/sparql`（HTTP SPARQL 接口专项）
- `tests/python`（核心功能回归套件）

## 2. 环境信息

- PostgreSQL：16（WSL Ubuntu-24.04）
- SPARQL 监听端口：`5820`
- 数据库：`rs_ontop_core`
- 测试时间：2026-04-14

## 3. 结果总览

| 测试集 | 总数 | 通过 | 失败 | 通过率 |
|---|---:|---:|---:|---:|
| `tests/sparql` | 33 | 10 | 23 | 30.3% |
| `tests/python` | 92 | 92 | 0 | 100% |

## 4. 关键结论

- 核心功能回归（`tests/python`）保持稳定，未出现回归（`92/92` 全通过）。
- SPARQL 专项（`tests/sparql`）仍有较多失败，主要为两类：
  - 可控 `400`（稳定性闸门拦截高风险构造）
  - 语义不一致（如排序结果、标量子查询值差异）
- 相比早期状态，服务稳定性已提升：避免了连续 panic 导致的端口掉线连锁故障。

## 5. 失败分布（`tests/sparql`）

### 5.1 稳定性闸门拦截（HTTP 400）

典型涉及特性：

- `FILTER` 日期类型比较（typed literal）
- 复杂 `BIND` 表达式（算术、字符串函数）
- `GROUP BY` / 聚合
- `EXISTS` / `NOT EXISTS`
- `UNION` / `VALUES` / `IN` / `COALESCE` / `MINUS` / `SERVICE`

### 5.2 语义不一致

- `ORDER BY` 用例：返回行顺序与 SQL 基线不一致。
- `SubqueryScalar`：字段值映射/过滤结果与 SQL 基线不一致。

### 5.3 OPTIONAL 相关

- `OPTIONAL` 相关若干用例存在行数不一致（SPARQL=0，SQL>0）。

## 6. 产出文件

- SPARQL 回归报告：
  - `tests/sparql/sparql_test_report_20260414_101954.json`
- Python 回归报告：
  - `tests/output/test_report_20260414_102021.json`

## 7. 建议的修复优先级

1. **恢复语义能力（优先）**
   - 先恢复 `FILTER/OPTIONAL` 基础路径，减少 0 行误判。
2. **表达式与聚合能力**
   - 逐步放开并修复 `BIND`、`GROUP BY`、`EXISTS` 等构造。
3. **一致性校正**
   - 校正 `ORDER BY` 与标量子查询映射逻辑，提升与 SQL 基线一致性。
4. **每步回归验证**
   - 每恢复一类能力后，立即复跑对应子集，再跑一次 `tests/sparql` 全量。

## 8. 当前状态判定

- **可用性**：核心路径可用（Python 全量通过）。
- **完整性**：SPARQL 高级能力仍不完整，需分阶段恢复。
- **风险**：若直接放开当前拦截的高风险构造，存在触发后端异常的风险。
