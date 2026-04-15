# Ontop 开源系统伪代码（Sprint2 参考）

> 说明：这是面向架构对照的伪代码，不是 Ontop 源码逐行翻译。  
> 目标：帮助在 Sprint2 中对齐“标准 OBDA 引擎”的关键处理链路。

---

## 1. 系统入口（加载本体 + 映射 + DB 元数据）

```pseudocode
FUNCTION ONTOP_START(config):
    ontology = LOAD_ONTOLOGY(config.ontology_file)
    mappings = LOAD_MAPPING(config.mapping_file)          // R2RML/OBDA
    db_meta  = LOAD_DB_METADATA(config.datasource)        // 表、键、类型、约束

    tbox = CLASSIFY_AND_NORMALIZE_TBOX(ontology)
    mapping_index = BUILD_MAPPING_INDEX(mappings)

    query_engine = CREATE_QUERY_ENGINE(
        tbox = tbox,
        mappings = mapping_index,
        metadata = db_meta,
        optimizer_pipeline = DEFAULT_OPTIMIZERS()
    )
    RETURN query_engine
END FUNCTION
```

---

## 2. SPARQL 查询主流程

```pseudocode
FUNCTION EXECUTE_SPARQL(engine, sparql):
    ast = PARSE_SPARQL(sparql)
    VALIDATE_QUERY(ast)

    iq = BUILD_INITIAL_IQ(ast)                   // Intermediate Query
    iq = UNFOLD_MAPPINGS(iq, engine.mappings)    // Intensional -> Extensional
    iq = APPLY_TBOX_REWRITING(iq, engine.tbox)   // 本体语义重写

    iq = OPTIMIZE_IQ(iq, engine.optimizer_pipeline)
    native_sql = GENERATE_SQL(iq, engine.metadata)

    rows = EXECUTE_SQL(native_sql)
    results = FORMAT_SPARQL_RESULTS(rows, ast.result_form)  // SELECT/ASK/CONSTRUCT
    RETURN results
END FUNCTION
```

---

## 3. 映射展开（Unfolding）核心逻辑

```pseudocode
FUNCTION UNFOLD_MAPPINGS(iq, mapping_index):
    FOR each atom IN iq.intensional_atoms:
        candidates = mapping_index.FIND(atom.predicate)
        unfolded_branches = []

        FOR each mapping_rule IN candidates:
            substitution = UNIFY(atom.terms, mapping_rule.target_terms)
            IF substitution IS COMPATIBLE:
                source_tree = PARSE_SQL_SOURCE(mapping_rule.source_sql)
                unfolded = APPLY_SUBSTITUTION(source_tree, substitution)
                unfolded_branches.ADD(unfolded)

        REPLACE atom WITH UNION(unfolded_branches)

    RETURN iq
END FUNCTION
```

---

## 4. IQ 优化流水线（典型）

```pseudocode
FUNCTION OPTIMIZE_IQ(iq, pipeline):
    iq = NORMALIZE_PROJECTIONS(iq)
    iq = PUSH_DOWN_FILTERS(iq)
    iq = ELIMINATE_REDUNDANT_JOINS(iq)
    iq = MERGE_EQUIVALENT_NODES(iq)
    iq = LIFT_UNIONS_WHEN_BENEFICIAL(iq)
    iq = REORDER_JOINS_BY_COST(iq)
    iq = PRUNE_UNUSED_COLUMNS(iq)
    iq = ENFORCE_NULLABILITY_AND_TYPE_CONSTRAINTS(iq)
    RETURN iq
END FUNCTION
```

---

## 5. SQL 生成（方言感知）

```pseudocode
FUNCTION GENERATE_SQL(iq, metadata):
    dialect = DETECT_SQL_DIALECT(metadata.datasource)
    builder = CREATE_SQL_BUILDER(dialect)

    sql_tree = TRANSLATE_IQ_TO_SQL_TREE(iq, builder)
    sql_tree = APPLY_DIALECT_RULES(sql_tree, dialect)   // quoting, limit/offset, funcs
    sql_text = SERIALIZE_SQL(sql_tree)
    RETURN sql_text
END FUNCTION
```

---

## 6. 结果构造（RDF Term 组装）

```pseudocode
FUNCTION FORMAT_SPARQL_RESULTS(rows, result_form):
    IF result_form == ASK:
        RETURN BOOLEAN(rows.NOT_EMPTY)

    output = INIT_RESULT_CONTAINER(result_form)
    FOR each row IN rows:
        binding = {}
        FOR each projected_var:
            term_spec = LOOKUP_TERM_TEMPLATE(projected_var)    // IRI/BNode/Literal
            binding[projected_var] = MATERIALIZE_RDF_TERM(row, term_spec)
        output.ADD(binding)

    RETURN output
END FUNCTION
```

---

## 7. 异常与可观测性（工程实践）

```pseudocode
FUNCTION SAFE_EXECUTE(query):
    TRY:
        return EXECUTE_SPARQL(engine, query)
    CATCH ParseError:
        return HTTP_400("Invalid SPARQL syntax")
    CATCH MappingError:
        return HTTP_500("Mapping/unfolding failure")
    CATCH SqlExecutionError:
        return HTTP_502("Database execution failure")
    FINALLY:
        RECORD_METRICS(latency, rows, optimizer_steps, sql_length)
END FUNCTION
```

