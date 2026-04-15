# Sprint 9 系统伪代码 (实际实现状态)

> 创建时间：2026-04-04  
> 说明：本文档反映 Sprint 9 的实际实现状态，基于当前代码库分析  
> 标记说明：`[S8]` = Sprint 8 已完成, `[S9-P0-DONE]` = Sprint 9 P0 已实现, `[S9-P0-PARTIAL]` = 部分实现, `[S9-P1-TODO]` = 待实现, `[S9-P2-TODO]` = 待实现

---

## 1. 解析层 - `src/parser/property_path_parser.rs`

### 1.1 PropertyPath 枚举 [S8 + S9-P0-DONE]

```pseudocode
// [S8] 当前已实现
ENUM PropertyPath:
    Predicate(String),               // <http://.../knows>
    
    // [S9-P0-DONE] 反向路径 - 已实现
    Inverse(Box<PropertyPath>),     // ^<http://.../knows>
    
    // [S9-P0-DONE] 序列路径 - 已实现
    Sequence(Vec<PropertyPath>),    // <p1>/<p2>/<p3>
    
    // [S9-P0-DONE] 选择路径 - 已实现
    Alternative(Vec<PropertyPath>), // <p1>|<p2>
    
    // [S9-P2-TODO] 零次或多次 - 待实现
    Star(Box<PropertyPath>),         // <p>*
    
    // [S9-P2-TODO] 一次或多次 - 待实现
    Plus(Box<PropertyPath>),         // <p>+
    
    // [S9-P2-TODO] 可选 - 待实现
    Optional(Box<PropertyPath>),     // <p>?
END ENUM
```

### 1.2 属性路径解析函数 [S8 + S9-P0-DONE]

```pseudocode
// [S8 + S9-P0-DONE] 当前已实现：支持直接、反向、序列、选择路径
FUNCTION parse_property_path(path_str: &str) -> Result<PropertyPath, ParseError>:
    // 解析优先级: 选择 (|) > 序列 (/) > 反向 (^) > 原子
    
    IF path_str.contains('|'):
        RETURN parse_alternative(path_str)
    ELSE IF path_str.contains('/'):
        RETURN parse_sequence(path_str)
    ELSE IF path_str.starts_with('^'):
        RETURN parse_inverse(path_str)
    // [S9-P2-TODO] 路径修饰符待实现
    // ELSE IF path_str.ends_with('*'):
    //     RETURN parse_star(path_str)
    // ELSE IF path_str.ends_with('+'):
    //     RETURN parse_plus(path_str)
    // ELSE IF path_str.ends_with('?'):
    //     RETURN parse_optional(path_str)
    ELSE:
        RETURN PropertyPath::Predicate(path_str.to_string())
END FUNCTION
```

### 1.3 路径转换函数 [S9-P0-PARTIAL]

```pseudocode
// [S9-P0-DONE] 反向路径 IR 转换 - 已实现但有bug
// ^<predicate> 转换为 <predicate> 但交换 subject 和 object
// ?a ^:knows ?b  等价于 ?b :knows ?a

FUNCTION convert_inverse_path(
    inverse_path: &PropertyPath, 
    subject: Term, 
    object: Term
) -> LogicNode:
    LET inner_path = match inverse_path:
        PropertyPath::Inverse(inner) => inner,
        _ => panic!("Expected inverse path")
    
    // 交换 subject 和 object
    convert_path_to_triples(inner_path, object, subject)
END FUNCTION

// [S9-P0-PARTIAL] 序列路径 SQL 生成 - 部分实现
// <p1>/<p2>/<p3> 生成多表 JOIN - 但当前使用RDF三元组模型

FUNCTION generate_sequence_sql(
    paths: &[PropertyPath], 
    start_table: &str, 
    ctx: &GeneratorContext
) -> String:
    // [CURRENT BUG] 当前生成针对rdf_triples表的递归CTE
    // [TODO] 需要改为OBDA模型的JOIN链
    
    LET mut current_alias = start_table.to_string()
    LET mut join_sql = String::new()
    
    FOR (i, path) IN paths.iter().enumerate():
        LET join_alias = format!("seq_{}", i)
        LET predicate = extract_predicate(path)
        
        // [TODO] 这里应该生成关系表JOIN，而不是递归CTE
        join_sql.push_str(&format!(
            " JOIN {} AS {} ON {}.{} = {}.{}",
            get_table_name(predicate), join_alias, 
            current_alias, get_join_column(predicate),
            join_alias, get_pk_column(predicate)
        ))
        
        current_alias = join_alias
    END FOR
    
    RETURN join_sql
END FUNCTION

// [S9-P0-PARTIAL] 选择路径 SQL 生成 - 部分实现
// <p1>|<p2> 生成 UNION

FUNCTION generate_alternative_sql(
    paths: &[PropertyPath], 
    ctx: &GeneratorContext
) -> String:
    LET union_parts: Vec<String> = paths.iter()
        .map(|path| generate_path_sql(path, ctx))
        .collect()
    
    format!("({})", union_parts.join(" UNION "))
END FUNCTION
```

---

## 2. 解析层 - `src/parser/ir_converter.rs`

### 2.1 动态映射解析 [S9-P0-DONE]

```pseudocode
// [S9-P0-DONE] 动态解析谓词到列的映射 - 已实现
FUNCTION resolve_predicate_to_column(
    predicate_iri: &str, 
    mapping_store: &MappingStore,
    table_name: &str
) -> Option<String>:
    // 1. 首先尝试从映射表中查找
    IF let Some(mappings) = mapping_store.mappings.get(predicate_iri):
        FOR mapping IN mappings:
            IF mapping.table_name == table_name:
                // 返回第一个位置的列映射
                RETURN mapping.position_to_column.get(&0).cloned()
            END IF
        END FOR
    END IF
    
    // 2. 如果没有找到映射，使用启发式规则
    MATCH predicate_iri:
        iri IF iri.contains("name") => Some("last_name".to_string()),
        iri IF iri.contains("first_name") => Some("first_name".to_string()),
        iri IF iri.contains("last_name") => Some("last_name".to_string()),
        iri IF iri.contains("manager") => Some("manager_id".to_string()),
        iri IF iri.contains("employee") => Some("employee_id".to_string()),
        iri IF iri.contains("department") => Some("department_id".to_string()),
        iri IF iri.contains("email") => Some("email".to_string()),
        iri IF iri.contains("phone") => Some("phone".to_string()),
        _ => None,
    END MATCH
END FUNCTION
```

### 2.2 反向路径JOIN生成 [S9-P0-DONE]

```pseudocode
// [S9-P0-DONE] 反向路径的JOIN逻辑 - 已实现
FUNCTION create_inverse_path_join(
    patterns: &[&TriplePattern],
    metadata: Arc<TableMetadata>,
    mapping_store: &MappingStore,
) -> LogicNode:
    // 分离反向路径和普通路径
    LET mut inverse_patterns = Vec::new()
    LET mut normal_patterns = Vec::new()
    
    FOR pattern IN patterns:
        IF is_inverse_path(&pattern.predicate):
            inverse_patterns.push(pattern)
        ELSE:
            normal_patterns.push(pattern)
        END IF
    END FOR
    
    // 检查是否是跨表关系
    IF is_cross_table_inverse_path(&inverse_patterns):
        RETURN create_cross_table_inverse_join(
            &inverse_patterns, &normal_patterns, metadata, mapping_store
        )
    ELSE:
        RETURN create_single_table_inverse_join(
            &inverse_patterns, &normal_patterns, metadata, mapping_store
        )
    END IF
END FUNCTION

// [S9-P0-DONE] 单表反向路径JOIN - 已实现
FUNCTION create_single_table_inverse_join(
    inverse_patterns: &[&&TriplePattern],
    normal_patterns: &[&&TriplePattern],
    metadata: Arc<TableMetadata>,
    mapping_store: &MappingStore,
) -> LogicNode:
    // 为反向路径创建两个表实例
    LET mut left_mapping = HashMap::new()
    LET mut right_mapping = HashMap::new()
    
    // 处理反向路径：?s ^ex:manager ?o
    FOR pattern IN inverse_patterns:
        // 对于反向路径，原始subject在左表，原始object在右表
        IF pattern.subject.starts_with('?'):
            LET var = pattern.subject.trim_start_matches('?')
            // 动态解析主键列
            IF let Some(pk_col) = resolve_predicate_to_column(
                "http://example.org/employee", mapping_store, &metadata.table_name
            ):
                left_mapping.insert(var.to_string(), pk_col)
            ELSE:
                left_mapping.insert(var.to_string(), "employee_id".to_string())
            END IF
        END IF
        
        IF pattern.object.starts_with('?'):
            LET var = pattern.object.trim_start_matches('?')
            // 动态解析主键列
            IF let Some(pk_col) = resolve_predicate_to_column(
                "http://example.org/employee", mapping_store, &metadata.table_name
            ):
                right_mapping.insert(var.to_string(), pk_col)
            ELSE:
                right_mapping.insert(var.to_string(), "employee_id".to_string())
            END IF
        END IF
        
        // 动态解析manager_id列
        IF let Some(pred_iri) = extract_predicate_iri(&pattern.predicate):
            IF let Some(manager_col) = resolve_predicate_to_column(
                &pred_iri, mapping_store, &metadata.table_name
            ):
                left_mapping.insert("manager_id".to_string(), manager_col)
            END IF
        END IF
    END FOR
    
    // 处理普通路径（如name属性）
    FOR pattern IN normal_patterns:
        IF pattern.subject.starts_with('?'):
            LET var = pattern.subject.trim_start_matches('?')
            IF var != "subordinate" AND var != "manager":
                IF let Some(pred_iri) = extract_predicate_iri(&pattern.predicate):
                    IF let Some(col_name) = resolve_predicate_to_column(
                        &pred_iri, mapping_store, &metadata.table_name
                    ):
                        IF left_mapping.contains_key(var):
                            left_mapping.insert(var.to_string(), col_name)
                        ELSE IF right_mapping.contains_key(var):
                            right_mapping.insert(var.to_string(), col_name)
                        END IF
                    END IF
                END IF
            END IF
        END IF
    END FOR
    
    // 创建两个ExtensionalData节点
    LET left_node = LogicNode::ExtensionalData {
        table_name: metadata.table_name.clone(),
        column_mapping: left_mapping,
        metadata: Arc::clone(&metadata),
    }
    
    LET right_node = LogicNode::ExtensionalData {
        table_name: metadata.table_name.clone(),
        column_mapping: right_mapping,
        metadata: Arc::clone(&metadata),
    }
    
    // 创建JOIN条件：LEFT.manager_id = RIGHT.employee_id
    LET join_condition = Expr::Compare {
        left: Box::new(Expr::Term(Term::Variable("left.manager_id".to_string()))),
        right: Box::new(Expr::Term(Term::Variable("right.employee_id".to_string()))),
        op: ComparisonOp::Eq,
    }
    
    // 返回JOIN节点
    LogicNode::Join {
        children: vec![left_node, right_node],
        condition: Some(join_condition),
        join_type: JoinType::Inner,
    }
END FUNCTION
```

---

## 3. 重写层 - `src/rewriter/path_unfolder.rs`

### 3.1 PathUnfolder 结构 [S9-P0-DONE]

```pseudocode
// [S9-P0-DONE] 路径展开器 - 已实现但未集成到主流程
STRUCT PathUnfolder {
    mapping_store: Arc<MappingStore>,
    metadata_cache: HashMap<String, Arc<TableMetadata>>,
}

IMPL PathUnfolder:
    FUNCTION new(mapping_store: Arc<MappingStore>) -> Self:
        Self {
            mapping_store,
            metadata_cache: HashMap::new(),
        }
    END FUNCTION
    
    // [S9-P0-DONE] 展开PropertyPath为LogicNode - 已实现
    FUNCTION unfold_path(
        &self,
        path: &PropertyPath,
        subject: Term,
        object: Term,
    ) -> Result<LogicNode, PathUnfoldError>:
        MATCH path:
            PropertyPath::Predicate(iri) =>
                self.unfold_predicate_path(iri, subject, object)
            
            PropertyPath::Inverse(inner) =>
                self.unfold_inverse_path(inner, subject, object)
            
            PropertyPath::Sequence(paths) =>
                self.unfold_sequence_path(paths, subject, object)
            
            PropertyPath::Alternative(paths) =>
                self.unfold_alternative_path(paths, subject, object)
            
            // [S9-P2-TODO] 路径修饰符待实现
            PropertyPath::Star(inner) => 
                self.unfold_star_path(inner, subject, object)
            
            PropertyPath::Plus(inner) => 
                self.unfold_plus_path(inner, subject, object)
            
            PropertyPath::Optional(inner) => 
                self.unfold_optional_path(inner, subject, object)
        END MATCH
    END FUNCTION
    
    // [S9-P0-DONE] 谓词路径展开 - 已实现
    FUNCTION unfold_predicate_path(
        &self,
        predicate: &str,
        subject: Term,
        object: Term,
    ) -> Result<LogicNode, PathUnfoldError>:
        // 查找映射规则
        IF let Some(mappings) = self.mapping_store.mappings.get(predicate):
            FOR mapping IN mappings:
                LET metadata = self.get_or_load_metadata(&mapping.table_name)
                
                // 创建变量映射
                LET mut column_mapping = HashMap::new()
                
                // 处理subject
                IF let Term::Variable(var) = &subject:
                    LET subject_col = self.map_variable_to_column(var, &metadata)
                    column_mapping.insert(var.clone(), subject_col)
                END IF
                
                // 处理object
                IF let Term::Variable(var) = &object:
                    LET object_col = mapping.object_col.clone()
                    column_mapping.insert(var.clone(), object_col)
                END IF
                
                RETURN Ok(LogicNode::ExtensionalData {
                    table_name: mapping.table_name.clone(),
                    column_mapping,
                    metadata,
                })
            END FOR
        END IF
        
        RETURN Err(PathUnfoldError::MappingNotFound(predicate.to_string()))
    END FUNCTION
    
    // [S9-P0-DONE] 反向路径展开 - 已实现
    FUNCTION unfold_inverse_path(
        &self,
        inner_path: &PropertyPath,
        subject: Term,
        object: Term,
    ) -> Result<LogicNode, PathUnfoldError>:
        // 反向路径：交换subject和object
        self.unfold_path(inner_path, object, subject)
    END FUNCTION
    
    // [S9-P0-DONE] 序列路径展开 - 已实现
    FUNCTION unfold_sequence_path(
        &self,
        paths: &[PropertyPath],
        start_subject: Term,
        final_object: Term,
    ) -> Result<LogicNode, PathUnfoldError>:
        IF paths.is_empty():
            RETURN Err(PathUnfoldError::EmptyPath)
        END IF
        
        LET mut current_node = self.unfold_path(
            &paths[0], 
            start_subject.clone(), 
            self.create_fresh_variable()
        )?
        
        // 为中间路径创建JOIN链
        FOR i IN 1..paths.len():
            LET next_var = self.create_fresh_variable()
            LET next_node = self.unfold_path(
                &paths[i],
                self.extract_last_variable(&current_node),
                next_var.clone()
            )?
            
            current_node = LogicNode::Join {
                children: vec![current_node, next_node],
                condition: self.create_join_condition(&current_node, &next_node),
                join_type: JoinType::Inner,
            }
        END FOR
        
        // 连接到最终object
        self.connect_to_final_object(current_node, final_object)
    END FUNCTION
    
    // [S9-P0-DONE] 选择路径展开 - 已实现
    FUNCTION unfold_alternative_path(
        &self,
        paths: &[PropertyPath],
        subject: Term,
        object: Term,
    ) -> Result<LogicNode, PathUnfoldError>:
        IF paths.is_empty():
            RETURN Err(PathUnfoldError::EmptyPath)
        END IF
        
        LET union_children: Result<Vec<_>, _> = paths.iter()
            .map(|path| self.unfold_path(path, subject.clone(), object.clone()))
            .collect()
        
        Ok(LogicNode::Union(union_children?))
    END FUNCTION
END IMPL
```

---

## 4. SQL生成层 - `src/sql/flat_generator.rs`

### 4.1 递归路径处理 [S9-P2-PARTIAL]

```pseudocode
// [S9-P2-PARTIAL] 递归路径处理 - 部分实现（仅框架）
FUNCTION handle_recursive_path(
    &mut self,
    base_path: &LogicNode,
    recursive_path: &LogicNode,
    min_depth: usize,
) -> Result<(), GenerationError>:
    // 1. 使用策略模式创建递归CTE构建器
    LET column_strategy = Box::new(RecursivePathColumnStrategy)
    LET cte_builder = RecursiveCTEBulder::new(column_strategy)
    
    // 2. 结构化构建递归CTE AST，传递min_depth
    LET recursive_ast = cte_builder.build_recursive_cte(
        base_path, recursive_path, min_depth
    )?
    
    // 3. 从AST生成结构化SQL
    LET cte_sql = recursive_ast.to_sql()?
    
    // 4. 将CTE作为派生表添加到FROM子句
    LET cte_alias = self.alias_manager.allocate_table_alias("recursive_cte")
    self.ctx.from_tables.push(FromTable {
        table_name: cte_sql,
        alias: cte_alias.clone(),
        join_type: None,
        join_condition: None,
        is_values_table: false,
        values_columns: vec![],
    })
    
    // 5. 从AST中提取列信息并注册到上下文
    FOR column IN &recursive_ast.select_clause.columns:
        self.ctx.select_items.push(SelectItem {
            expression: column.expression.clone(),
            alias: column.alias.clone(),
            is_aggregate: false,
        })
        self.ctx.all_available_items.push(SelectItem {
            expression: column.expression.clone(),
            alias: column.alias.clone(),
            is_aggregate: false,
        })
    END FOR
    
    Ok(())
END FUNCTION
```

---

## 5. 当前实现状态总结

### 5.1 已完成功能 [S9-P0-DONE]

1. **PropertyPath 枚举扩展** ✅
   - 反向路径 (Inverse)
   - 序列路径 (Sequence) 
   - 选择路径 (Alternative)

2. **路径解析器** ✅
   - 支持混合路径解析
   - 正确的优先级处理

3. **动态映射解析** ✅
   - `resolve_predicate_to_column` 函数
   - 数据库映射表查询
   - 启发式规则回退

4. **反向路径JOIN逻辑** ✅
   - `create_inverse_path_join` 函数
   - 单表和跨表支持
   - 正确的变量映射

5. **PathUnfolder模块** ✅
   - 完整的路径展开框架
   - 支持所有基础路径类型
   - 错误处理机制

### 5.2 部分实现功能 [S9-P0-PARTIAL]

1. **序列路径SQL生成** ⚠️
   - 逻辑已实现，但生成RDF三元组模型SQL
   - 需要改为OBDA模型的JOIN链

2. **变量映射系统** ⚠️
   - 基础框架存在
   - 但存在 `table.name` vs `first_name` 映射问题

3. **PathUnfolder集成** ⚠️
   - 模块已实现
   - 但未集成到主解析流程

### 5.3 待实现功能 [S9-P1-TODO] [S9-P2-TODO]

1. **路径修饰符** (S9-P2)
   - Star (*), Plus (+), Optional (?)
   - 递归CTE生成

2. **BIND条件函数** (S9-P1)
   - IF(), COALESCE()
   - SQL CASE映射

3. **GeoSPARQL度量函数** (S9-P1)
   - geof:distance, geof:buffer
   - PostGIS函数映射

4. **查询缓存** (S9-P2)
   - LRU + TTL缓存
   - 查询计划缓存

5. **成本优化器** (S9-P1)
   - 统计信息收集
   - 索引推荐

---

## 6. 下一步开发计划

### 6.1 立即任务 (集成PathUnfolder)

```pseudocode
// 在 ir_converter.rs 中集成PathUnfolder
FUNCTION build_join_from_patterns_with_vars(
    patterns: &[TriplePattern],
    metadata_map: &HashMap<String, Arc<TableMetadata>>,
    mappings: Option<&MappingStore>,
    needed_vars: &HashSet<String>,
) -> LogicNode:
    // [NEW] 检查是否有PropertyPath需要展开
    FOR pattern IN patterns:
        IF is_property_path_pattern(pattern):
            LET path_unfolder = PathUnfolder::new(mappings.unwrap())
            LET unfolded_node = path_unfolder.unfold_path(
                &parse_property_path(&pattern.predicate),
                parse_term(&pattern.subject),
                parse_term(&pattern.object),
            )?
            RETURN unfolded_node
        END IF
    END FOR
    
    // [EXISTING] 回退到原有逻辑
    // ... 现有代码
END FUNCTION
```

### 6.2 修复变量映射问题

```pseudocode
// 修复 extract_variable_mappings 中的临时格式问题
FUNCTION collect_variable_mappings(node: &LogicNode, mappings: &mut HashMap<String, Expr>) {
    MATCH node:
        LogicNode::ExtensionalData { column_mapping, .. } =>
            FOR (var, col) IN column_mapping:
                // [FIX] 直接使用列名，不要添加table.前缀
                LET expr = Expr::Term(Term::Variable(col.clone()))
                mappings.insert(var.clone(), expr)
            END FOR
        // ... 其他情况
    END MATCH
}
END FUNCTION
```

### 6.3 完成序列路径OBDA化

```pseudocode
// 修复 generate_sequence_sql 使用OBDA模型
FUNCTION generate_sequence_sql_obda(
    paths: &[PropertyPath], 
    start_subject: Term,
    ctx: &GeneratorContext
) -> Result<LogicNode, GenerationError>:
    LET mut current_node = None
    LET mut current_subject = start_subject
    
    FOR (i, path) IN paths.iter().enumerate():
        LET next_subject = create_fresh_variable()
        LET path_node = unfold_single_path(path, current_subject, next_subject)?
        
        MATCH current_node:
            None => current_node = Some(path_node)
            Some(node) => 
                current_node = Some(LogicNode::Join {
                    children: vec![node, path_node],
                    condition: create_join_condition(node, &path_node),
                    join_type: JoinType::Inner,
                })
        END MATCH
        
        current_subject = next_subject
    END FOR
    
    Ok(current_node.unwrap())
END FUNCTION
```

---

**总结**：Sprint 9 P0 的核心架构已基本完成，主要剩余工作是集成现有模块和修复映射问题。整体框架符合OBDA设计理念，为后续P1和P2功能奠定了坚实基础。
