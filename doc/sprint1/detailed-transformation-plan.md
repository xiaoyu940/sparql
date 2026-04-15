# RS Ontop Core V2.0 详细改造计划

基于 `sprint1.md` 的完整技术方案，本文档制定了系统性的改造实施计划。

## 🎯 改造核心目标

### 技术架构升级
1. **引入 IR 中间层** - 解耦查询意图与 SQL 生成
2. **扁平化 SQL 生成** - 消除嵌套子查询，提升 PG 优化器效率
3. **pgrx 流式处理** - 支持 Portal 游标和分块传输
4. **URI 模板化处理** - 实时 RDF Term 转换

### 性能提升目标
- 查询响应时间减少 **50%**
- 支持 **千万级** 结果集流式处理
- 并发处理能力提升 **3倍**
- 内存使用量减少 **40%**

## 🗓️ 分阶段实施路线图

### 第一阶段：IR 中间层基础 (2周)

#### Sprint 1.1: IR 节点类型定义
**时间**: 5天  
**优先级**: 🔴 关键路径

**核心任务**:
```rust
// 新增文件: src/ir/node_types.rs
pub enum IRNode {
    Scan {
        table: String,
        alias: String,
        bindings: HashMap<String, String>, // var -> column
        subject_const: Option<String>,
        pk_col: String,
    },
    Join {
        left: Box<IRNode>,
        right: Box<IRNode>,
        join_vars: Vec<String>,
    },
    Filter {
        expression: Expression,
        child: Box<IRNode>,
    },
    Project {
        vars: Vec<String>,
        child: Box<IRNode>,
    },
}
```

**实现要点**:
- 设计可序列化的 IR 节点结构
- 实现节点的 Debug 和 Clone trait
- 添加节点类型验证机制
- 编写基础单元测试

#### Sprint 1.2: IR 构建器实现
**时间**: 5天  
**优先级**: 🔴 关键路径

**核心任务**:
```rust
// 新增文件: src/ir/builder.rs
pub struct IRBuilder {
    mapping_manager: Arc<MappingManager>,
}

impl IRBuilder {
    pub fn build(&self, parsed_query: ParsedQuery) -> Result<IRNode, BuildError> {
        // 将三元组模式转换为逻辑算子树
        match parsed_query.query_type {
            QueryType::Select => self.build_select(parsed_query),
            QueryType::Construct => self.build_construct(parsed_query),
            // ...
        }
    }
}
```

**实现要点**:
- 三元组模式到 Scan 节点的转换
- JOIN 变量分析和连接树构建
- FILTER 表达式的解析和转换
- 处理 OPTIONAL 和 UNION 语义

### 第二阶段：扁平化 SQL 生成器 (2.5周)

#### Sprint 2.1: FlatSQLGenerator 核心实现
**时间**: 8天  
**优先级**: 🔴 关键路径

**核心任务**:
```rust
// 新增文件: src/sql/flat_generator.rs
pub struct FlatSQLGenerator {
    ctx: GeneratorContext,
}

#[derive(Default)]
struct GeneratorContext {
    select_items: Vec<String>,
    from_tables: Vec<String>,
    where_conditions: Vec<String>,
    alias_counter: usize,
    var_to_column: HashMap<String, String>,
}

impl FlatSQLGenerator {
    pub fn generate(&mut self, root_node: &IRNode) -> Result<String, GenerationError> {
        self.reset_context();
        self.traverse(root_node)?;
        
        // [关键改造: 拼装为扁平 SQL]
        let mut sql = "SELECT ".to_string();
        sql.push_str(&self.ctx.select_items.join(", "));
        sql.push_str(" FROM ");
        sql.push_str(&self.ctx.from_tables.join(", "));
        
        if !self.ctx.where_conditions.is_empty() {
            sql.push_str(" WHERE ");
            sql.push_str(&self.ctx.where_conditions.join(" AND "));
        }
        
        Ok(sql)
    }
}
```

**技术难点**:
- **别名碰撞避免算法** - 需要实现智能别名分配
- **JOIN 条件自动推导** - 基于变量共享分析
- **表达式翻译** - SPARQL 表达式到 SQL 表达式

#### Sprint 2.2: 别名管理算法
**时间**: 4天  
**优先级**: 🟡 重要

**基于文档末尾的问题，实现别名碰撞避免**:
```rust
// 新增文件: src/sql/alias_manager.rs
pub struct AliasManager {
    used_aliases: HashSet<String>,
    table_alias_map: HashMap<String, String>,
    alias_counter: usize,
}

impl AliasManager {
    pub fn allocate_alias(&mut self, table_name: &str) -> String {
        // 生成基础别名
        let base_alias = self.generate_base_alias(table_name);
        let mut alias = base_alias.clone();
        
        // 避免碰撞
        let mut counter = 1;
        while self.used_aliases.contains(&alias) {
            alias = format!("{}_{}", base_alias, counter);
            counter += 1;
        }
        
        self.used_aliases.insert(alias.clone());
        self.table_alias_map.insert(table_name.to_string(), alias.clone());
        alias
    }
    
    fn generate_base_alias(&self, table_name: &str) -> String {
        // 从表名提取有意义的前缀
        if let Some(caps) = Regex::new(r"([a-z]+)").unwrap().captures(table_name) {
            caps[1].chars().take(3).collect()
        } else {
            "t".to_string()
        }
    }
}
```

### 第三阶段：流式处理集成 (2.5周)

#### Sprint 3.1: pgrx Portal 集成
**时间**: 8天  
**优先级**: 🔴 关键路径

**核心任务**:
```rust
// 新增文件: src/database/streaming_client.rs
pub struct StreamingClient {
    client: SpiClient,
}

impl StreamingClient {
    pub fn execute_streaming(&self, sql: &str) -> Result<Portal, ExecutionError> {
        // [改造: 使用 SPI Portal 游标实现流式读取]
        self.client.execute("BEGIN", &[])?;
        
        let portal = self.client.open_cursor(sql)?;
        Ok(portal)
    }
}

// 新增文件: src/database/portal.rs
pub struct Portal {
    name: String,
    client: SpiClient,
}

impl Portal {
    pub fn fetch(&mut self, batch_size: i32) -> Result<Vec<Row>, FetchError> {
        // 批量获取数据
        let rows = self.client.fetch(&self.name, batch_size)?;
        Ok(rows
    }
    
    pub fn close(self) -> Result<(), CloseError> {
        self.client.close_cursor(&self.name)?;
        Ok(())
    }
}
```

**技术挑战**:
- pgrx Portal API 的正确使用
- 内存管理和垃圾回收
- 错误处理和资源清理

#### Sprint 3.2: 分块 HTTP 响应
**时间**: 4天  
**优先级**: 🟡 重要

**核心任务**:
```rust
// 新增文件: src/http/chunked_response.rs
pub struct ChunkedResponse {
    request: Request,
    headers_sent: bool,
}

impl ChunkedResponse {
    pub fn start_stream(&mut self) -> Result<(), ResponseError> {
        // 写入响应头，准备分块传输
        let response = Response::from_string("")
            .with_status_code(StatusCode(200))
            .with_header(Header::from_bytes(
                &b"Content-Type"[..],
                &b"application/sparql-results+json"[..],
            )?)
            .with_header(Header::from_bytes(
                &b"Transfer-Encoding"[..],
                &b"chunked"[..],
            )?);
        
        self.request.respond(response)?;
        self.headers_sent = true;
        Ok(())
    }
    
    pub fn write_chunk(&mut self, data: &str) -> Result<(), WriteError> {
        if !self.headers_sent {
            self.start_stream()?;
        }
        
        // 写入分块数据
        let chunk_size = format!("{:x}\r\n", data.len());
        let chunk = format!("{}{}\r\n", chunk_size, data);
        self.request.as_writer().write_all(chunk.as_bytes())?;
        Ok(())
    }
}
```

### 第四阶段：优化器和映射升级 (2周)

#### Sprint 4.1: 查询优化器重构
**时间**: 5天  
**优先级**: 🟡 重要

**核心任务**:
```rust
// 新增文件: src/optimizer/redundant_elimination.rs
pub struct RedundantJoinElimination;

impl OptimizationRule for RedundantJoinElimination {
    fn apply(&self, plan: IRNode) -> IRNode {
        // [新增: 冗余连接消除]
        // 如果两个 Scan 指向同一张表且 Subject 相同，合并为一个 Scan
        match plan {
            IRNode::Join { left, right, join_vars } => {
                if let (IRNode::Scan { table: left_table, subject_const: Some(left_subject), .. },
                        IRNode::Scan { table: right_table, subject_const: Some(right_subject), .. }) = (&*left, &*right) {
                    if left_table == right_table && left_subject == right_subject {
                        // 合并扫描
                        *left
                    } else {
                        plan
                    }
                } else {
                    plan
                }
            },
            _ => plan
        }
    }
}
```

#### Sprint 4.2: 映射管理器升级
**时间**: 5天  
**优先级**: 🟡 重要

**核心任务**:
```rust
// 改造文件: src/mapping/manager.rs
impl MappingManager {
    pub fn find_mapping(&self, predicate: &str) -> Result<Mapping, MappingError> {
        let mut mapping = self.mappings.get(predicate)
            .ok_or(MappingError::NotFound(predicate.to_string()))?
            .clone();
        
        // [新增: 记录表的主键和索引信息]
        mapping.metadata = self.fetch_pg_metadata(&mapping.table_name)?;
        Ok(mapping)
    }
    
    fn fetch_pg_metadata(&self, table_name: &str) -> Result<TableMetadata, FetchError> {
        // 查询 PostgreSQL 系统表获取元数据
        let sql = r#"
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = $1
            ORDER BY ordinal_position
        "#;
        
        // 执行查询并构建元数据
        // ...
    }
}
```

### 第五阶段：结果处理器改造 (1.5周)

#### Sprint 5.1: URI 模板化处理
**时间**: 4天  
**优先级**: 🟡 重要

**核心任务**:
```rust
// 改造文件: src/processor/result_processor.rs
impl ResultProcessor {
    pub fn to_json_fragment(&self, rows: Vec<Row>) -> Result<String, ProcessingError> {
        // [改造: 实时将数据库原始值根据本体模板转换为 RDF Term]
        let mut bindings = Vec::new();
        
        for row in rows {
            let mut binding = HashMap::new();
            
            for (col_name, col_value) in row.columns {
                let template = self.get_template_for_col(&col_name);
                let rdf_val = if let Some(template) = template {
                    // 例子: ID 1 -> <http://example.org/item/1>
                    self.apply_uri_template(&template, &col_value)?
                } else {
                    self.format_as_literal(&col_value)?
                };
                
                binding.insert(col_name, rdf_val);
            }
            
            bindings.push(binding);
        }
        
        self.serialize_to_json_batch(bindings)
    }
    
    fn apply_uri_template(&self, template: &str, value: &str) -> Result<RDFTerm, TemplateError> {
        // 实现 URI 模板替换
        // 例如: "http://example.org/item/{id}" -> "http://example.org/item/1"
        let result = template.replace("{id}", value);
        Ok(RDFTerm::URI(result))
    }
}
```

### 第六阶段：集成测试和部署 (2周)

#### Sprint 6.1: 全面测试
**时间**: 5天  
**优先级**: 🔴 关键路径

**测试范围**:
- IR 构建正确性测试
- SQL 生成语义等价性测试
- 流式处理性能测试
- 并发压力测试
- 内存泄漏检测

#### Sprint 6.2: 生产部署准备
**时间**: 5天  
**优先级**: 🟡 重要

**部署任务**:
- 配置文件更新
- 监控指标集成
- 回滚方案准备
- 文档更新

## 🚨 关键风险和缓解策略

### 高风险项目

#### 1. pgrx Portal 流式处理
**风险**: 
- pgrx Portal API 使用不当导致连接泄漏
- 内存管理问题导致后台进程崩溃

**缓解策略**:
- 严格的资源生命周期管理
- 连接池和超时机制
- 详细的错误处理和日志
- 准备同步处理回退方案

#### 2. 扁平化 SQL 生成
**风险**:
- 生成的 SQL 语义不等价
- 复杂 JOIN 场景处理不当

**缓解策略**:
- 语义等价性验证测试
- 渐进式替换，保留原生成器
- 详细的 SQL 验证机制

#### 3. 别名碰撞避免算法
**风险**:
- 复杂查询中别名冲突
- 性能开销过大

**缓解策略**:
- 高效的哈希表实现
- 算法复杂度分析
- 压力测试验证

### 中风险项目

#### 1. IR 中间层性能
**风险**:
- IR 构建和遍历开销
- 内存占用增加

**缓解策略**:
- 零拷贝设计
- 内存池管理
- 性能基准测试

## 📊 成功指标和验收标准

### 功能指标
- [ ] 100% 现有 SPARQL 查询类型支持
- [ ] 语义等价性测试通过率 100%
- [ ] 单元测试覆盖率 ≥ 95%

### 性能指标
- [ ] 查询响应时间减少 ≥ 50%
- [ ] 支持 1000万+ 结果集流式处理
- [ ] 并发处理能力提升 ≥ 3倍
- [ ] 内存使用量减少 ≥ 40%

### 稳定性指标
- [ ] 99.9% 服务可用性
- [ ] 0 个服务崩溃事件
- [ ] 平均故障恢复时间 < 30秒

## 🛠️ 技术债务清理计划

### 需要删除的代码 (按优先级)

#### 🔴 高优先级删除
1. **PostgreSQLGenerator.generate_join_node**
   - 文件: `src/sql/postgresql_generator.rs`
   - 原因: 嵌套子查询导致 PG Planner 内存溢出
   - 替代: FlatSQLGenerator

2. **handle_sparql_request 中的 client.select()**
   - 文件: `src/listener/mod.rs`
   - 原因: 同步阻塞，无法处理海量结果集
   - 替代: 流式 Portal 处理

3. **ontop_query 直接字符串拼接**
   - 文件: `src/engine/ontop_query.rs`
   - 原因: SQL 注入风险
   - 替代: IR 中间层

#### 🟡 中优先级重构
1. **现有解析器模块**
   - 文件: `src/parser/`
   - 原因: 不支持 IR 构建
   - 替代: 新版解析器

2. **旧优化器**
   - 文件: `src/optimizer/`
   - 原因: 基于 SQL 字符串操作
   - 替代: 基于 IR 的优化器

## 🚀 部署策略

### 蓝绿部署方案
1. **新环境部署** - 独立部署 V2.0
2. **数据同步验证** - 确保数据一致性
3. **流量逐步切换** - 10% → 50% → 100%
4. **监控和回滚** - 实时监控，快速回滚

### 灰度发布策略
1. **内部测试** - 开发和测试环境验证
2. **小范围试点** - 5% 用户流量
3. **逐步扩大** - 20% → 50% → 100%
4. **全量发布** - 完全切换到 V2.0

## 📚 文档和知识转移

### 技术文档
- [ ] IR 中间层设计规范
- [ ] 扁平化 SQL 生成原理
- [ ] 流式处理架构文档
- [ ] 别名管理算法说明
- [ ] 性能调优指南

### 开发培训
- [ ] IR 架构设计培训
- [ ] 新开发流程培训
- [ ] 性能优化最佳实践
- [ ] 故障排查和调试指南

## 📈 后续优化方向

### 短期优化 (3个月)
- 查询计划缓存机制
- 自适应优化策略
- 更丰富的错误诊断
- 性能监控仪表板

### 长期规划 (6个月)
- 分布式查询支持
- 机器学习查询优化
- 多数据库后端支持
- 实时流式查询

## ✅ Sprint1 收尾验收（2026-03-28）

### 实施验收（本迭代范围）
- [x] 核心改造链路已打通：SPARQL 解析 -> IR 构建 -> 逻辑优化 -> 扁平 SQL 生成 -> 流式返回
- [x] 异常拦截和错误分类路径已接入，服务端不再因常见查询输入直接崩溃
- [x] 模块与文件交付齐备，已完成编译和核心测试验证
- [x] 压测/基准烟测脚本可执行，核心通路具备可重复验证能力

### 指标口径说明
- “100% 查询类型支持、95% 覆盖率、生产 SLA（99.9%）”作为发布级目标，转入下一迭代持续验证。
- Sprint1 以“完成架构重构并稳定运行”为关闭标准，本次达到关闭条件。

---

**总结**: 这个详细的改造计划基于 `sprint1.md` 的技术方案，通过系统性的分阶段实施，确保 RS Ontop Core V2.0 的成功升级。重点关注了关键技术难点（如别名管理、流式处理）的风险控制，并提供了完整的验收标准和部署策略。
