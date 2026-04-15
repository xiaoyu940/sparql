# Sprint 9 系统伪代码

> 创建时间：2026-04-02  
> 说明：本文档包含当前系统（Sprint 8 已完成）的伪代码，并标识 Sprint 9 开发计划  
> 标记说明：`[S8]` = 已实现, `[S9-P0]` = Sprint 9 P0计划, `[S9-P1]` = Sprint 9 P1计划, `[S9-P2]` = Sprint 9 P2计划

---

## 1. 解析层 - `src/parser/property_path_parser.rs`

### 1.1 PropertyPath 枚举 [S8 + S9-P0]

```pseudocode
// [S8] 当前已实现
ENUM PropertyPath:
    Direct(String),                    // <http://.../knows>
    
    // [S9-P0-1] 反向路径 - 未实现
    // ^<http://.../knows>
    // Inverse(Box<PropertyPath>),
    
    // [S9-P0-2] 序列路径 - 未实现
    // <p1>/<p2>/<p3>
    // Sequence(Vec<PropertyPath>),
    
    // [S9-P0-3] 选择路径 - 未实现
    // <p1>|<p2>
    // Alternative(Vec<PropertyPath>),
    
    // [S9-P2-1] 零次或多次 - 未实现
    // <p>*
    // ZeroOrMore(Box<PropertyPath>),
    
    // [S9-P2-2] 一次或多次 - 未实现
    // <p>+
    // OneOrMore(Box<PropertyPath>),
    
    // [S9-P2-3] 可选 - 未实现
    // <p>?
    // Optional(Box<PropertyPath>),
END ENUM
```

### 1.2 属性路径解析函数 [S8 + S9-P0]

```pseudocode
// [S8] 当前已实现：仅支持直接路径
FUNCTION parse_property_path(path_str: &str) -> Result<PropertyPath, ParseError>:
    // [S9-P0] 需要扩展为完整解析器
    // 解析优先级: 选择 (|) > 序列 (/) > 修饰符 (? * +) > 反向 (^) > 原子
    
    // [S9-P0-3] IF path_str.contains('|'):
    //     RETURN parse_alternative(path_str)
    // [S9-P0-2] ELSE IF path_str.contains('/'):
    //     RETURN parse_sequence(path_str)
    // [S9-P0-1] ELSE IF path_str.starts_with('^'):
    //     RETURN parse_inverse(path_str)
    // [S9-P2-1] ELSE IF path_str.ends_with('*'):
    //     RETURN parse_zero_or_more(path_str)
    // [S9-P2-2] ELSE IF path_str.ends_with('+'):
    //     RETURN parse_one_or_more(path_str)
    // [S9-P2-3] ELSE IF path_str.ends_with('?'):
    //     RETURN parse_optional(path_str)
    // ELSE:
    
    // [S8] 当前仅支持直接路径
    RETURN PropertyPath::Direct(path_str.to_string())
END FUNCTION
```

### 1.3 路径转换函数 [S9-P0]

```pseudocode
// [S9-P0-1] 反向路径 IR 转换 - 未实现
// ^<predicate> 转换为 <predicate> 但交换 subject 和 object
// ?a ^:knows ?b  等价于 ?b :knows ?a

// FUNCTION convert_inverse_path(
//     inverse_path: &PropertyPath, 
//     subject: Term, 
//     object: Term
// ) -> LogicNode:
//     LET inner_path = match inverse_path:
//         PropertyPath::Inverse(inner) => inner,
//         _ => panic!("Expected inverse path")
//     
//     // 交换 subject 和 object
//     convert_path_to_triples(inner_path, object, subject)
// END FUNCTION


// [S9-P0-2] 序列路径 SQL 生成 - 未实现
// <p1>/<p2>/<p3> 生成多表 JOIN

// FUNCTION generate_sequence_sql(
//     paths: &[PropertyPath], 
//     start_table: &str, 
//     ctx: &GeneratorContext
// ) -> String:
//     LET mut current_alias = start_table.to_string()
//     LET mut join_sql = String::new()
//     
//     FOR (i, path) IN paths.iter().enumerate():
//         LET join_alias = format!("seq_{}", i)
//         LET predicate = extract_predicate(path)
//         
//         join_sql.push_str(&format!(
//             " JOIN employees AS {} ON {}.employee_id = {}.employee_id",
//             join_alias, current_alias, join_alias
//         ))
//         
//         current_alias = join_alias
//     END FOR
//     
//     RETURN join_sql
// END FUNCTION


// [S9-P0-3] 选择路径 SQL 生成 - 未实现
// <p1>|<p2> 生成 UNION

// FUNCTION generate_alternative_sql(
//     paths: &[PropertyPath], 
//     ctx: &GeneratorContext
// ) -> String:
//     LET union_parts: Vec<String> = paths.iter()
//         .map(|path| generate_path_sql(path, ctx))
//         .collect()
//     
//     format!("({})", union_parts.join(" UNION "))
// END FUNCTION
```

---

## 2. 解析层 - `src/parser/ir_converter.rs`

### 2.1 FILTER 表达式解析 [S8 + S9-P1]

```pseudocode
// [S8] 当前已实现：支持算术、字符串、基础GeoSPARQL
FUNCTION parse_filter_expr(filter: &str) -> Option<Expr>:
    let trimmed = filter.trim();
    
    // [S8] 1. 尝试解析函数调用
    // 支持 prefix:function 格式 (如 geof:sfWithin)
    let func_regex = regex::Regex::new(
        r"^([A-Za-z_][A-Za-z0-9_]*:?[A-Za-z_][A-Za-z0-9_]*)\((.*)\)$"
    ).ok()?;
    
    if let Some(caps) = func_regex.captures(trimmed) {
        let name = caps[1].to_uppercase();
        let args_str = caps[2].trim();
        
        // [S8] 解析逗号分隔的参数列表
        let arg_strs = Self::split_function_args(args_str);
        let mut parsed_args = Vec::new();
        for arg_str in arg_strs {
            let arg_trimmed = arg_str.trim();
            if let Some(e) = Self::parse_filter_expr(arg_trimmed) {
                parsed_args.push(e);
            } else {
                parsed_args.push(Expr::Term(Self::token_to_term(arg_trimmed)));
            }
        }
        
        return Some(Expr::Function { name, args: parsed_args });
    }
    
    // [S8] 2. 尝试解析算术操作符 (+, -, *, /)
    for op_str in &["+", "-", "*", "/"] {
        if let Some(pos) = Self::find_logical_op(trimmed, op_str) {
            // [S8] 排除负数情况
            if op_str == &"-" && pos == 0 {
                continue;
            }
            
            let left_str = trimmed[..pos].trim();
            let right_str = trimmed[pos + op_str.len()..].trim();
            
            if left_str.is_empty() || right_str.is_empty() {
                continue;
            }
            
            let left = Self::parse_filter_expr(left_str)?;
            let right = Self::parse_filter_expr(right_str)?;
            
            let func_name = match *op_str {
                "+" => "ADD",
                "-" => "SUB",
                "*" => "MUL",
                "/" => "DIV",
                _ => unreachable!(),
            };
            
            return Some(Expr::Function {
                name: func_name.to_string(),
                args: vec![left, right],
            });
        }
    }
    
    // [S9-P1-1] 3. 尝试解析 IF 条件函数 - 未实现
    // IF expr.to_uppercase().starts_with("IF("):
    //     LET args = Self::split_function_args(&expr[3..expr.len()-1])
    //     IF args.len() == 3:
    //         LET condition = Self::parse_filter_expr(args[0].trim())?
    //         LET true_expr = Self::parse_filter_expr(args[1].trim())?
    //         LET false_expr = Self::parse_filter_expr(args[2].trim())?
    //         
    //         RETURN Some(Expr::Function {
    //             name: "IF".to_string(),
    //             args: vec![condition, true_expr, false_expr]
    //         })
    
    // [S9-P1-1] 4. 尝试解析 COALESCE - 未实现
    // IF expr.to_uppercase().starts_with("COALESCE("):
    //     LET args_str = &expr[10..expr.len()-1]
    //     LET args: Vec<&str> = Self::split_function_args(args_str)
    //     LET parsed_args = args.iter()
    //         .filter_map(|arg| Self::parse_filter_expr(arg.trim()))
    //         .collect()
    //     
    //     RETURN Some(Expr::Function {
    //         name: "COALESCE".to_string(),
    //         args: parsed_args
    //     })
    
    // 终端节点处理...
END FUNCTION
```

### 2.2 辅助函数 [S8]

```pseudocode
// [S8] 分割函数参数字符串，正确处理引号内的逗号
FUNCTION split_function_args(args_str: &str) -> Vec<&str>:
    LET mut result = Vec::new()
    LET mut start = 0
    LET mut in_quotes = false
    LET mut paren_depth = 0
    LET bytes = args_str.as_bytes()
    
    FOR i IN 0..bytes.len():
        LET c = bytes[i]
        
        // 处理引号
        IF c == b'"' || c == b'\'':
            in_quotes = !in_quotes
            continue
        
        // 处理括号嵌套
        IF !in_quotes:
            IF c == b'(':
                paren_depth += 1
            ELSE IF c == b')':
                paren_depth -= 1
            ELSE IF c == b',' && paren_depth == 0:
                result.push(&args_str[start..i])
                start = i + 1
    
    // 添加最后一个参数
    IF start < args_str.len():
        result.push(&args_str[start..])
    
    IF result.is_empty():
        result.push(args_str)
    
    RETURN result
END FUNCTION


// [S8] 处理类型化字面量，如 "POINT(...)"^^geo:wktLiteral
FUNCTION token_to_term(token: &str) -> Term:
    LET t = token.trim()
    
    // 处理变量
    IF t.starts_with('?'):
        RETURN Term::Variable(t.trim_start_matches('?').to_string())
    
    // [S8] 处理类型化字面量
    IF t.starts_with('"') && t.contains("^^"):
        IF let Some(end_quote) = t[1..].find('"'):
            LET value = &t[1..=end_quote]
            LET rest = &t[end_quote+2..]
            IF rest.starts_with("^^"):
                LET datatype = &rest[2..]
                RETURN Term::Literal {
                    value: value.to_string(),
                    datatype: Some(datatype.to_string()),
                    language: None,
                }
    
    // 处理数字常量
    IF t.chars().all(|c| c.is_ascii_digit() || c == '.'):
        RETURN Term::Literal {
            value: t.to_string(),
            datatype: Some("integer".to_string()),
            language: None,
        }
    
    // 处理普通字符串字面量
    IF (t.starts_with('"') && t.ends_with('"')) ||
       (t.starts_with('\'') && t.ends_with('\'')):
        RETURN Term::Literal {
            value: t.trim_matches('"').trim_matches('\'').to_string(),
            datatype: None,
            language: None,
        }
    
    Term::Constant(t.to_string())
END FUNCTION
```

---

## 3. SQL 生成层 - `src/sql/flat_generator.rs`

### 3.1 表达式翻译 [S8 + S9-P1/P2]

```pseudocode
// [S8] 翻译表达式为 SQL，支持 BIND 和基础 GeoSPARQL
FUNCTION translate_expression(&self, expr: &Expr) -> Result<String, GenerationError>:
    MATCH expr:
        Expr::Function { name, args } => {
            LET mut args_sql = Vec::new()
            FOR arg IN args:
                args_sql.push(self.translate_expression(arg)?)
            
            MATCH name.as_str():
                // [S8] 算术运算函数
                "ADD" if args_sql.len() == 2 => 
                    Ok(format!("({} + {})", args_sql[0], args_sql[1]))
                "SUB" if args_sql.len() == 2 => 
                    Ok(format!("({} - {})", args_sql[0], args_sql[1]))
                "MUL" if args_sql.len() == 2 => 
                    Ok(format!("({} * {})", args_sql[0], args_sql[1]))
                "DIV" if args_sql.len() == 2 => 
                    Ok(format!("({} / {})", args_sql[0], args_sql[1]))
                
                // [S8] 字符串函数
                "CONCAT" => 
                    Ok(format!("({})", args_sql.join(" || ")))
                "STR" if args_sql.len() == 1 => 
                    Ok(format!("CAST({} AS TEXT)", args_sql[0]))
                "LCASE" | "LOWER" if args_sql.len() == 1 => 
                    Ok(format!("LOWER({})", args_sql[0]))
                "UCASE" | "UPPER" if args_sql.len() == 1 => 
                    Ok(format!("UPPER({})", args_sql[0]))
                "REGEX" if args_sql.len() >= 2 => 
                    Ok(format!("{} ~ {}", args_sql[0], args_sql[1]))
                
                // [S8] GeoSPARQL 基础函数 (简单要素拓扑关系)
                "GEOF:SFWITHIN" | "SFWITHIN" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Within(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                "GEOF:SFCONTAINS" | "SFCONTAINS" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Contains(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                "GEOF:SFINTERSECTS" | "SFINTERSECTS" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Intersects(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                "GEOF:SFOVERLAPS" | "SFOVERLAPS" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Overlaps(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                "GEOF:SFTOUCHES" | "SFTOUCHES" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Touches(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                "GEOF:SFDISJOINT" | "SFDISJOINT" if args_sql.len() == 2 =>
                    Ok(format!(
                        "ST_Disjoint(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                        args_sql[0], args_sql[1]
                    ))
                
                // [S9-P1-2] GeoSPARQL 度量函数 - 未实现
                // "GEOF:DISTANCE" | "DISTANCE" if args_sql.len() >= 2 =>
                //     Ok(format!(
                //         "ST_Distance(ST_GeomFromText({}, 4326), ST_GeomFromText({}, 4326))",
                //         args_sql[0], args_sql[1]
                //     ))
                
                // [S9-P1-2] GeoSPARQL 缓冲区函数 - 未实现
                // "GEOF:BUFFER" | "BUFFER" if args_sql.len() >= 2 =>
                //     Ok(format!(
                //         "ST_Buffer(ST_GeomFromText({}, 4326), {})",
                //         args_sql[0], args_sql[1]
                //     ))
                
                // [S9-P1-1] BIND 条件函数 - 未实现
                // "IF" if args_sql.len() == 3 =>
                //     Ok(format!(
                //         "CASE WHEN {} THEN {} ELSE {} END",
                //         args_sql[0], args_sql[1], args_sql[2]
                //     ))
                
                // [S9-P1-1] COALESCE - 未实现
                // "COALESCE" =>
                //     Ok(format!("COALESCE({})", args_sql.join(", ")))
                
                // [S9-P2-2] 日期时间函数 - 未实现
                // "NOW" => Ok("CURRENT_TIMESTAMP".to_string())
                // "YEAR" if args_sql.len() == 1 =>
                //     Ok(format!("EXTRACT(YEAR FROM {})", args_sql[0]))
                // "MONTH" if args_sql.len() == 1 =>
                //     Ok(format!("EXTRACT(MONTH FROM {})", args_sql[0]))
                // "DAY" if args_sql.len() == 1 =>
                //     Ok(format!("EXTRACT(DAY FROM {})", args_sql[0]))
                
                _ => Ok(format!("{}({})", name, args_sql.join(", ")))
        }
        
        Expr::Term(term) => self.translate_term(term)
        
        Expr::Comparison { left, op, right } => {
            LET left_sql = self.translate_expression(left)?
            LET right_sql = self.translate_expression(right)?
            LET op_sql = self.translate_comparison_op(*op)
            Ok(format!("{} {} {}", left_sql, op_sql, right_sql))
        }
        
        // [S8] EXISTS/NOT EXISTS
        Expr::Function { name, args } if name == "EXISTS" || name == "NOT_EXISTS" => {
            // EXISTS/NOT EXISTS 处理逻辑...
        }
END FUNCTION
```

### 3.2 EXISTS/NOT EXISTS 处理 [S8]

```pseudocode
// [S8] 解析 EXISTS 模式并生成子查询 SQL
FUNCTION parse_exists_pattern(&self, pattern: &str, ctx: &GeneratorContext) 
    -> Result<String, GenerationError>:
    
    LET clean_pattern = pattern.trim_matches('\'')
    LET parts: Vec<&str> = clean_pattern.split_whitespace().collect()
    
    IF parts.len() >= 3:
        LET subject = parts[0]      // ?emp
        LET predicate = parts[1]    // <http://example.org/status>
        LET object = parts[2]       // "Terminated" or ?dept
        
        // 获取外部表的别名
        LET outer_table_alias = ctx.from_tables.first()
            .map(|t| &t.alias)
            .unwrap_or("t0")
        
        // 从谓词 URI 提取列名
        LET column = IF predicate.starts_with('<') && predicate.ends_with('>'):
            LET uri = &predicate[1..predicate.len()-1]
            uri.split('/').last().unwrap_or("id")
        ELSE:
            "id"
        
        // 获取主变量名并映射到正确列名
        LET subject_var = IF subject.starts_with('?'):
            &subject[1..]
        ELSE:
            subject
        
        // [S8] 列名映射修正
        LET correlation_col = MATCH subject_var:
            "emp" | "employee" => "employee_id"
            "dept" | "department" => "department_id"
            _ => &format!("{}_id", subject_var)
        
        LET subquery_alias = format!("{}_sub", subject_var)
        
        // 构建关联条件
        LET condition = IF object.starts_with('?'):
            // [S8] 变量对象处理
            LET object_var = &object[1..]
            LET (subquery_corr_col, outer_corr_col) = IF column == "department_id":
                ("department_id", "department_id")
            ELSE IF object_var == "dept" || object_var == "department":
                ("department_id", "department_id")
            ELSE:
                (correlation_col, correlation_col)
            
            format!("{}.{} = {}.{}", 
                subquery_alias, subquery_corr_col,
                outer_table_alias, outer_corr_col)
                
        ELSE IF object.starts_with('"') && object.ends_with('"'):
            // [S8] 常量对象处理
            LET value = &object[1..object.len()-1]
            format!("{}.{} = {}.{} AND {}.{} = '{}'",
                subquery_alias, correlation_col,
                outer_table_alias, correlation_col,
                subquery_alias, column, value)
        ELSE:
            format!("{}.{} = {}.{}",
                subquery_alias, correlation_col,
                outer_table_alias, correlation_col)
        
        // 确定子查询表名
        LET subquery_table = MATCH subject_var:
            "emp" | "employee" => "employees"
            "dept" | "department" => "departments"
            _ => "employees"
        
        LET sql = format!(
            "EXISTS (SELECT 1 FROM {} AS {} WHERE {})",
            subquery_table, subquery_alias, condition
        )
        
        Ok(sql)
    ELSE:
        Ok("EXISTS (SELECT 1)".to_string())
END FUNCTION
```

---

## 4. 优化器 - `src/optimizer/query_optimizer.rs` [S9-P1-3]

```pseudocode
// [S9-P1-3] 查询优化器增强 - 未实现
// 当前系统仅有基础优化，Sprint 9需要增强

// [S9-P1-3] 查询优化器结构
// STRUCT QueryOptimizer:
//     stats_collector: PgStatsCollector,
//     cost_model: CostModel,
// END STRUCT

// [S9-P1-3] 优化查询主函数
// FUNCTION optimize_query(&self, plan: LogicNode) -> Result<LogicNode, OptimizerError>:
//     // 1. 统计信息收集
//     LET stats = self.stats_collector.collect_stats(&plan)?
//     
//     // 2. 成本估算
//     LET cost = self.cost_model.estimate_cost(&plan, &stats)
//     
//     // 3. 应用优化规则
//     LET optimized = self.apply_optimization_rules(plan)?
//     
//     // 4. 索引推荐
//     IF let Some(index_recommendation) = self.recommend_index(&optimized):
//         log::info!("Recommended index: {:?}", index_recommendation)
//     
//     RETURN optimized
// END FUNCTION

// [S9-P1-3] 优化规则应用
// FUNCTION apply_optimization_rules(&self, plan: LogicNode) 
//     -> Result<LogicNode, OptimizerError>:
//     LET mut current = plan
//     
//     // [S9-P1-3] 谓词下推
//     current = self.push_down_predicates(current)?
//     
//     // [S9-P1-3] 连接顺序优化 (基于成本)
//     current = self.optimize_join_order(current)?
//     
//     // [S9-P1-3] 子查询展开
//     current = self.unfold_subqueries(current)?
//     
//     // [S9-P2-4] 投影下推
//     current = self.push_down_projections(current)?
//     
//     RETURN current
// END FUNCTION
```

---

## 5. 缓存模块 - `src/cache/query_cache.rs` [S9-P2-3]

```pseudocode
// [S9-P2-3] 查询缓存基础 - 未实现（新模块）

// [S9-P2-3] 缓存结构
// STRUCT QueryCache:
//     cache: HashMap<String, CachedResult>,
//     ttl: Duration,
//     max_size: usize,
// END STRUCT

// [S9-P2-3] 缓存结果
// STRUCT CachedResult:
//     sql: String,
//     result: QueryResult,
//     timestamp: Instant,
// END STRUCT

// [S9-P2-3] 缓存操作
// FUNCTION get(&self, sparql: &str) -> Option<QueryResult>:
//     LET key = hash(sparql)
//     IF let Some(cached) = self.cache.get(&key):
//         IF cached.timestamp.elapsed() < self.ttl:
//             RETURN Some(cached.result.clone())
//     RETURN None
// END FUNCTION

// FUNCTION put(&mut self, sparql: &str, sql: &str, result: QueryResult):
//     IF self.cache.len() >= self.max_size:
//         self.evict_oldest()
//     
//     LET key = hash(sparql)
//     self.cache.insert(key, CachedResult {
//         sql: sql.to_string(),
//         result,
//         timestamp: Instant::now(),
//     })
// END FUNCTION
```

---

## 6. R2RML 映射 - `src/mapping/r2rml_loader.rs` [S9-P1-4]

```pseudocode
// [S8] 当前已实现：基础 R2RML 支持
// [S9-P1-4] 需要增强：完整 R2RML 规范支持

// [S8] 当前结构
STRUCT R2RMLMapping:
    subject_map: SubjectMap,
    predicate_object_maps: Vec<PredicateObjectMap>,
    // [S9-P1-4] 需要添加：
    // graph_maps: Vec<GraphMap>,           // 命名图支持
    // join_conditions: Vec<JoinCondition>,  // 复杂JOIN条件
    // ref_object_maps: Vec<RefObjectMap>, // 外键引用
END STRUCT

// [S9-P1-4] 扩展功能 - 未实现
// FUNCTION parse_r2rml_full(turtle_content: &str) -> Result<MappingStore, R2RMLError>:
//     // 1. 解析 Turtle 格式
//     // 2. 支持所有 R2RML 规范特性
//     // 3. 处理 rr:parentTriplesMap 外键引用
//     // 4. 处理 rr:joinCondition 复杂JOIN
//     // 5. 支持多图映射 (rr:graphMap)
// END FUNCTION
```

---

**文档版本**: 1.0  
**创建日期**: 2026-04-02  
**说明**: `[S8]` = Sprint 8 已实现, `[S9-P0/P1/P2]` = Sprint 9 各阶段计划
