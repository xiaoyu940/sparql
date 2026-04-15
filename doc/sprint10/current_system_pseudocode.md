# Sprint 10 Current System Pseudocode

Updated: 2026-04-15
Scope: lib.rs, listener.rs, parser/*, ir_converter.rs, sql/flat_generator.rs

## 1. End-to-End Flow

PSEUDOCODE:
  FUNCTION HANDLE_SPARQL_REQUEST(sparql_text, mode):
      IF mode == "sql_function":
          RETURN ONTOP_TRANSLATE_OR_EXECUTE(sparql_text)
      IF mode == "http_5820":
          RETURN BGWORKER_HTTP_HANDLER(sparql_text)
      RETURN ERROR("unsupported mode")

## 2. SQL Function Entry (lib.rs)

PSEUDOCODE:
  FUNCTION _PG_init():
      REGISTER background worker with ontop_sparql_bgworker_main

  FUNCTION ontop_start_sparql_server():
      DYNAMIC_LOAD background worker ontop_sparql_bgworker_main

  FUNCTION ontop_refresh():
      IN SPI transaction:
          LOAD metadata
          LOAD mappings
          BUILD OntopEngine
          STORE engine in global ENGINE (Mutex<Option<OntopEngine>>)
      RETURN "refreshed" or error

  FUNCTION ontop_translate(sparql):
      engine = READ ENGINE from global lock
      IF engine is None:
          RETURN translation error
      IF query is ASK:
          inner_sql = engine.translate_with_cache(sparql)
          RETURN "SELECT EXISTS(inner_sql) AS result"
      RETURN engine.translate_with_cache(sparql)

  FUNCTION spi_execute_sparql_json_rows(client, sparql):
      sql = ontop_translate(sparql)
      IF sparql is ASK:
          ask_sql = "SELECT EXISTS(sql) AS result"
          table = client.select(ask_sql)
          first_row = FIRST(table)
          IF first_row exists:
              RETURN [{"boolean": decode_bool(first_row)}]
          RETURN [{"boolean": false}]
      wrapped_sql = "SELECT to_jsonb(t) FROM (sql) AS t"
      table = client.select(wrapped_sql)
      RETURN map rows to JSON array

## 3. HTTP 5820 Entry (listener.rs)

PSEUDOCODE:
  FUNCTION ontop_sparql_bgworker_main(_arg):
      ATTACH signal handlers
      CONNECT worker to SPI
      TRY initialize engine in transaction (refresh_engine_from_spi)
      server = BIND "0.0.0.0:5820"

      WHILE worker latch active:
          req = server.recv_timeout(100ms)
          IF no request: CONTINUE

          IF request method is OPTIONS:
              RESPOND 204 with CORS headers
              CONTINUE

          IF path starts with "/ontology":
              RESPOND ontology JSON-LD
              CONTINUE

          IF path starts with "/sparql":
              PARSE query parameter
              rows = spi_execute_sparql_json_rows(...)
              RESPOND SPARQL JSON with CORS headers
              CONTINUE

          RESPOND 404

Current model note:
  Single bgworker loop handles HTTP requests serially.

## 4. Translation Pipeline (OntopEngine)

PSEUDOCODE:
  FUNCTION OntopEngine.translate(sparql):
      parsed = SparqlParserV2.parse(sparql)
      logic_ir = IRBuilder.build_with_mappings(parsed, metadata_map, mappings)
      optimized_ir = OptimizerPipeline.run(logic_ir, context)
      sql = FlatSQLGenerator.generate(optimized_ir)
      RETURN sql

  FUNCTION OntopEngine.translate_with_cache(sparql):
      key = make cache key(sparql, metadata version, mapping version)
      IF key in query_cache: RETURN cached sql
      sql = translate(sparql)
      SAVE cache[key] = sql
      RETURN sql

## 5. Parser Layer

PSEUDOCODE:
  FUNCTION SparqlParserV2.parse(sparql):
      NORMALIZE clauses
      EXTRACT PREFIX / SELECT / WHERE / ORDER / LIMIT
      where_block = raw WHERE body

      filters = extract_filter_expressions(where_block)
      binds = extract_bind_expressions(where_block)
      triples = parse_main_triples_without_filter_blocks(where_block)
      subqueries = extract_subqueries(where_block)
      values_block = parse_values(where_block)

      RETURN ParsedQuery(...)

## 6. IR Converter Layer

PSEUDOCODE:
  FUNCTION IRConverter.convert_with_mappings(parsed, metadata_map, mappings):
      projected_vars = normalize selected variables
      core_plan = build_core_plan_with_vars(parsed.main_patterns, metadata_map, mappings)

      FOR each bind expression:
          bind_expr = parse_filter_expr(bind.expression)
          core_plan = Construction(bind alias -> bind_expr, child=core_plan)

      FOR each filter expression:
          IF parse_exists_filter_expr(filter) succeeds:
              core_plan = Filter(EXISTS/NOT EXISTS expr, child=core_plan)
          ELSE:
              filter_expr = parse_filter_expr(filter)
              core_plan = Filter(filter_expr, child=core_plan)

      IF query has GROUP BY or aggregates:
          core_plan = build_aggregation_node(parsed, core_plan, projected_vars)

      IF query has ORDER BY / LIMIT:
          core_plan = Limit(order_by, limit, child=core_plan)

      RETURN Construction(projected_vars, child=core_plan)

## 7. SQL Generator Layer

PSEUDOCODE:
  FUNCTION FlatSQLGenerator.generate(root_node):
      RESET context
      TRAVERSE logic tree and collect:
          select items, from tables, join conditions,
          where/having/order/limit

      FOR expressions:
          translate_expression(expr)
          HANDLE compare/logical/function/arithmetic
          HANDLE EXISTS -> generate_exists_subquery(...)
          HANDLE GeoSPARQL mapping -> PostGIS SQL

      RETURN assemble_sql()

  FUNCTION generate_exists_subquery(patterns, correlated_vars, filters):
      RESOLVE mapping table for each triple pattern
      BUILD FROM + equality joins + constant constraints
      APPLY correlated links (outer_col = inner_col)
      APPLY simple filter fragments
      RETURN "SELECT 1 FROM ... WHERE ..."

## 8. Current Behavior Summary

PSEUDOCODE:
  RULES:
    1) ENGINE is process-local in each PostgreSQL process.
    2) HTTP 5820 path and SQL function path share translation/execution core.
    3) ASK query uses EXISTS-wrapped SQL and returns {"boolean": ...}.
    4) FILTER EXISTS/NOT EXISTS is lowered in SQL generator.
    5) Listener side is single-worker serial handling.

## 9. Evolution Hints

PSEUDOCODE:
  NEXT_STEPS_HINT:
    - Keep parser/IR/SQL contracts stable.
    - Decouple accept path and execute path for future concurrency.
    - Add queue/backpressure and metrics around spi_execute_sparql_json_rows.
    - Preserve ontop_refresh consistency when scaling workers.
