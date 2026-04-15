# Sprint2 改造计划（执行版）

## 🎯 目标
- 对齐 Ontop 关键能力：映射展开、语义重写、RDF 结果语义、方言感知 SQL、端到端稳定性
- 将当前“可运行骨架”提升为“可发布版本”

## P0（必须完成）

### 1) 映射展开与语义重写主链路
- [x] 在查询主流程中显式接入 `UNFOLD_MAPPINGS` 阶段
- [x] 引入最小可用 `TBOX_REWRITING`（先覆盖 subclass/subproperty 基础规则）
- [x] 为展开/重写失败提供可诊断错误分类（沿用现有 translate 错误路径并补充分层阶段）

**验收**:
- [ ] 至少 20 条映射展开用例通过（含 join/union/filter 组合）
- [ ] 语义重写前后结果与基准数据集对齐

进展（2026-03-28）:
- 已实现显式 `MappingUnfolder` 与 `TBoxRewriter`，并在 `OntopEngine::translate` 主链路接入。
- 已新增 3 个基础测试（subClassOf / subPropertyOf / intensional->extensional unfolding）并通过。

### 2) IRConverter 语义升级
- [x] 从“flag 驱动”改为“图模式驱动”构建 IR（BGP/FILTER/OPTIONAL/UNION）
- [x] 去除固定表/列启发式映射，改为基于映射规则绑定变量
- [x] 补齐嵌套 UNION/OPTIONAL 组合场景

**验收**:
- [ ] 复杂查询（OPTIONAL+FILTER+UNION）不降级为占位 IR
- [ ] 关键回归查询 SQL 可解释且稳定

进展（2026-03-28）:
- ParserV2 已增加图模式抽取结构（`main_patterns/optional_patterns/union_patterns/filter_expressions`）。
- IRConverter 已按图模式生成 `Construction/Join/Union/Filter` 组合，不再仅依赖布尔 flag 占位。
- IRBuilder 已接入 mapping index，IRI 谓词在命中 mapping rule 时走 `IntensionalData -> Unfolding` 的映射驱动绑定路径。

### 3) 结果语义与 HTTP 输出
- [x] 返回标准 SPARQL Results JSON（`head.vars` + RDF term binding）
- [x] 实现端到端 chunked 响应（非“内部分批 + 一次性输出”）
- [x] 支持 ASK 结果格式

**验收**:
- [ ] SELECT/ASK 结果通过协议兼容测试
- [ ] 大结果集场景下内存曲线稳定、无崩溃

进展（2026-03-28）:
- 已在 listener 侧补充 SPARQL 结果格式化函数（RDF term 结构）与 ASK 布尔响应逻辑，并新增对应单测。
- 已在响应层启用 chunked 传输头策略（`with_chunked_threshold(0)`）与标准 SPARQL content-type。
- 已将“查询执行到网络输出”改为逐批直写 chunk（手工 chunk framing + batch fetch）。
- 运行态验证说明：当前环境下 PostgreSQL 服务重启需 sudo 密码，旧 worker 进程可能仍在使用旧库；代码级与单测验证已完成。

## P1（应完成）

### 4) SQL 生成增强（方言与约束）
- [ ] 引入 SQL 方言层（先覆盖 PostgreSQL，保留扩展点）
- [ ] 在生成阶段应用空值/类型约束规则
- [ ] 完善别名与 join 条件推导边界

**验收**:
- [ ] 典型查询 SQL 可在 `EXPLAIN` 下稳定执行
- [ ] 边界场景（空值、类型转换）有回归测试

### 5) 优化器补强
- [ ] 增加 projection normalize / unused column prune
- [ ] 增加 union lifting 与等价节点合并规则
- [ ] 形成可配置优化 pipeline（含开关和统计）

**验收**:
- [ ] 同一查询在优化开关下结果等价
- [ ] 复杂查询平均耗时较 Sprint1 基线下降（目标 ≥20%）

## P2（可选但建议）

### 6) 可观测性与运维闭环
- [ ] 指标补齐：展开耗时、优化阶段耗时、SQL 长度、结果行数
- [ ] 补齐部署、回滚、故障排查文档
- [ ] 提供 Sprint2 验收报告模板

**验收**:
- [ ] 指标可用于定位慢查询与失败点
- [ ] 运维文档可独立执行一次演练

## 📋 统一测试与质量门槛
- [ ] 单元 + 集成 + 回归测试分层跑通
- [ ] 关键路径用例进入 CI 默认集
- [ ] 覆盖率达到团队约定阈值（建议先到 80%，再冲刺 90%+）
- [ ] 压测报告包含：吞吐、P95、错误率、峰值内存

## ✅ Sprint2 关闭标准
- [ ] P0 全部完成并通过验收
- [ ] P1 至少完成 70%
- [ ] 无 P0/P1 级阻塞缺陷
- [ ] 形成可复现的测试与性能报告
