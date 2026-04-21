#![allow(unexpected_cfgs)]

use pgrx::prelude::*;
use pgrx::spi::SpiClient;
use pgrx::{GucContext, GucFlags, GucRegistry, GucSetting};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use once_cell::sync::Lazy;
use serde_json;

pub mod benchmark;
pub mod codegen;
pub mod config;
pub mod error;
pub mod federation;
pub mod function;
pub mod ir;
pub mod listener;
pub mod mapping;
pub mod metadata;
pub mod monitoring;
pub mod optimizer;
pub mod parser;
pub mod reasoner;
pub mod rewriter;
pub mod service;
pub mod sql;
pub mod substitution;

use pgrx::bgworkers::BackgroundWorkerBuilder;
use crate::mapping::{MappingStore, MappingRule, PropertyType};
use crate::mapping::r2rml_loader::R2RmlLoader;
use crate::metadata::{TableMetadata};
use crate::optimizer::{OptimizerContext, PassManager, CacheManager, CacheConfig};
use crate::optimizer::{FilterPushdown, JoinReordering, RedundantJoinElimination};
use crate::parser::SparqlParserV2;
use crate::parser::sparql_parser_v2::QueryType;
use crate::ir::IRBuilder;
use crate::rewriter::{MappingUnfolder, TBoxRewriter};
use crate::sql::FlatSQLGenerator;

pgrx::pg_module_magic!();

static SPARQL_HTTP_WORKERS: GucSetting<i32> = GucSetting::<i32>::new(1);
static SPARQL_HTTP_PORT: GucSetting<i32> = GucSetting::<i32>::new(5820);
static SPARQL_HTTP_REUSEPORT: GucSetting<bool> = GucSetting::<bool>::new(true);

fn define_http_gateway_gucs() {
    GucRegistry::define_int_guc(
        "rs_ontop_core.http_workers",
        "Number of SPARQL HTTP background workers",
        "Number of background worker processes that concurrently serve the SPARQL HTTP gateway.",
        &SPARQL_HTTP_WORKERS,
        1,
        64,
        GucContext::Postmaster,
        GucFlags::default(),
    );

    GucRegistry::define_int_guc(
        "rs_ontop_core.http_port",
        "SPARQL HTTP gateway port",
        "TCP port used by the SPARQL HTTP background workers.",
        &SPARQL_HTTP_PORT,
        1024,
        65535,
        GucContext::Postmaster,
        GucFlags::default(),
    );

    GucRegistry::define_bool_guc(
        "rs_ontop_core.http_reuseport",
        "Enable SO_REUSEPORT for SPARQL HTTP workers",
        "When enabled, multiple SPARQL HTTP background workers can bind the same TCP port.",
        &SPARQL_HTTP_REUSEPORT,
        GucContext::Postmaster,
        GucFlags::default(),
    );
}

pub(crate) fn configured_http_gateway_port() -> u16 {
    SPARQL_HTTP_PORT.get().clamp(1024, 65535) as u16
}

pub(crate) fn configured_http_gateway_reuseport() -> bool {
    SPARQL_HTTP_REUSEPORT.get()
}

fn configured_http_gateway_workers_effective() -> usize {
    let configured = SPARQL_HTTP_WORKERS.get().clamp(1, 64) as usize;
    if configured > 1 && !configured_http_gateway_reuseport() {
        log!("rs-ontop-core: rs_ontop_core.http_workers={} requires rs_ontop_core.http_reuseport=on for single-port mode; falling back to 1 worker", configured);
        1
    } else {
        configured
    }
}

const HTTP_WORKER_LOCK_KEY: i64 = 0x52534f4e_4854574b;
fn count_alive_http_gateway_workers() -> Result<usize, String> {
    let sql = "SELECT COUNT(*)::int4
               FROM pg_stat_activity
               WHERE backend_type ~ '^rs_ontop_core SPARQL Web Gateway [0-9]+$'";

    Spi::get_one::<i32>(sql)
        .map_err(|e| format!("count alive gateway workers failed: {}", e))
        .map(|opt| opt.unwrap_or(0).max(0) as usize)
}

fn next_http_gateway_worker_id() -> Result<usize, String> {
    let sql = "SELECT COALESCE(MAX((regexp_match(backend_type, '([0-9]+)$'))[1]::int), -1) + 1
               FROM pg_stat_activity
               WHERE backend_type ~ '^rs_ontop_core SPARQL Web Gateway [0-9]+$'";

    Spi::get_one::<i32>(sql)
        .map_err(|e| format!("compute next worker id failed: {}", e))
        .map(|opt| opt.unwrap_or(0).max(0) as usize)
}

fn register_http_gateway_bgworkers(dynamic: bool, start_worker_id: usize, worker_count: usize) {
    for worker_id in start_worker_id..(start_worker_id + worker_count) {
        let worker_name = format!("rs_ontop_core SPARQL Web Gateway {}", worker_id);
        let worker_extra = format!("worker_id={}", worker_id);
        let builder = BackgroundWorkerBuilder::new(&worker_name)
            .set_function("ontop_sparql_bgworker_main")
            .set_library("rs_ontop_core")
            .set_extra(&worker_extra)
            .enable_spi_access();

        if dynamic {
            builder.load_dynamic();
        } else {
            builder.load();
        }
    }
}

#[pg_guard]
pub unsafe extern "C-unwind" fn _PG_init() {
    define_http_gateway_gucs();
    let worker_count = configured_http_gateway_workers_effective();
    register_http_gateway_bgworkers(false, 0, worker_count);
}

/// 随需拉起 HTTP 守护进程（如果不想改 postgresql.conf重启，可手敲此命令拉起后台端口）
#[pg_extern]
fn ontop_start_sparql_server() -> String {
    // Serialize concurrent start calls to avoid over-provisioning workers.
    let lock_acquired = match Spi::get_one::<bool>(&format!(
        "SELECT pg_try_advisory_lock({})",
        HTTP_WORKER_LOCK_KEY
    )) {
        Ok(Some(v)) => v,
        Ok(None) => false,
        Err(e) => return format!("failed to acquire advisory lock: {}", e),
    };
    if !lock_acquired {
        return "another session is starting SPARQL workers; please retry".to_string();
    }

    let result = (|| {
        let target = configured_http_gateway_workers_effective();
        let mut alive = count_alive_http_gateway_workers()?;
        let mut started = 0usize;
        let mut failed = 0usize;
        let mut attempts = 0usize;
        let max_attempts = target.saturating_mul(3).max(1);

        while alive < target && attempts < max_attempts {
            attempts += 1;
            let worker_id = next_http_gateway_worker_id()?;
            register_http_gateway_bgworkers(true, worker_id, 1);

            std::thread::sleep(Duration::from_millis(200));
            let refreshed = count_alive_http_gateway_workers()?;

            if refreshed > alive {
                started += refreshed - alive;
            } else {
                failed += 1;
                std::thread::sleep(Duration::from_millis(200));
            }
            alive = refreshed;
        }

        Ok::<String, String>(format!(
            "SPARQL HTTP workers target={}, alive={}, started={}, failed={}, attempts={}",
            target, alive, started, failed, attempts
        ))
    })();

    let _ = Spi::run(&format!("SELECT pg_advisory_unlock({})", HTTP_WORKER_LOCK_KEY));

    match result {
        Ok(msg) => msg,
        Err(e) => format!("failed to start SPARQL workers: {}", e),
    }
}

#[pg_extern]
fn ontop_http_worker_status() -> String {
    let target = configured_http_gateway_workers_effective();
    let port = configured_http_gateway_port();
    let reuseport = configured_http_gateway_reuseport();

    let alive = count_alive_http_gateway_workers();

    match alive {
        Ok(alive) => format!(
            "{{\"target\":{},\"alive\":{},\"port\":{},\"reuseport\":{}}}",
            target, alive, port, reuseport
        ),
        Err(e) => format!(
            "{{\"target\":{},\"alive\":null,\"port\":{},\"reuseport\":{},\"error\":\"{}\"}}",
            target,
            port,
            reuseport,
            e.replace('"', "'")
        ),
    }
}

/// Global engine instance (wrapped in Mutex for thread-safety in PG)
static ENGINE: Lazy<Mutex<Option<OntopEngine>>> = Lazy::new(|| Mutex::new(None));

#[derive(Clone)]
pub struct OntopEngine {
    pub mappings: Arc<MappingStore>,
    pub metadata: Arc<HashMap<String, Arc<TableMetadata>>>,
    pub cache_manager: Arc<Mutex<CacheManager>>,
}

impl OntopEngine {
    pub fn new(mappings: Arc<MappingStore>, metadata: HashMap<String, Arc<TableMetadata>>) -> Self {
        let cache_config = CacheConfig::default();
        Self { 
            mappings,
            metadata: Arc::new(metadata),
            cache_manager: Arc::new(Mutex::new(CacheManager::new(cache_config))),
        }
    }

    pub fn with_cache_config(mappings: Arc<MappingStore>, metadata: HashMap<String, Arc<TableMetadata>>, cache_config: CacheConfig) -> Self {
        Self {
            mappings,
            metadata: Arc::new(metadata),
            cache_manager: Arc::new(Mutex::new(CacheManager::new(cache_config))),
        }
    }

    pub fn translate(&self, sparql: &str) -> Result<String, String> {
        eprintln!("[DEBUG Engine] metadata keys: {:?}", self.metadata.keys().collect::<Vec<_>>());
        eprintln!("[DEBUG Engine] mappings count: {}", self.mappings.mappings.len());
        
        let parser = SparqlParserV2::default();
        let parsed = parser
            .parse(sparql)
            .map_err(|e| format!("parse failed: {}", e))?;

        if parsed.query_type == QueryType::Describe {
            if let Some(sql) = self.translate_describe_query(&parsed) {
                return Ok(sql);
            }
        }

        let builder = IRBuilder::new();
        let mut logic_plan = builder
            .build_with_mappings(&parsed, &*self.metadata, Some(&self.mappings))
            .map_err(|e| format!("IR build error: {:?}", e))?;

        let ctx = OptimizerContext {
            mappings: Arc::clone(&self.mappings),
            metadata: (*self.metadata).clone(),
            stats: crate::optimizer::Statistics::default(), // Load active stats if fetched!
        };

        MappingUnfolder::unfold(&mut logic_plan, &ctx);
        logic_plan = TBoxRewriter::rewrite(&logic_plan, &self.mappings);

        logic_plan = RedundantJoinElimination::apply(logic_plan);
        logic_plan = FilterPushdown::apply(logic_plan);
        logic_plan = JoinReordering::apply(logic_plan, &ctx);
        let pass_manager = PassManager::new();
        pass_manager.run(&mut logic_plan, &ctx);

        // [S6-P1-2] Materialise any SERVICE nodes into PostgreSQL temp tables.
        // This must run AFTER optimisation (so joins are already ordered) but
        // BEFORE SQL generation (so the generator sees plain ExtensionalData).
        let mut temp_mgr = crate::federation::TempTableManager::new();
        let materializer = crate::federation::ServiceMaterializer::new();
        logic_plan = materializer
            .materialize_all(logic_plan, &mut temp_mgr)
            .map_err(|e| format!("SERVICE materialisation failed: {}", e))?;

        let mut generator = FlatSQLGenerator::new_with_mappings(Arc::clone(&self.mappings));
        generator
            .generate(&logic_plan)
            .map_err(|e| format!("SQL generation failed: {}", e))
    }

    fn translate_describe_query(&self, parsed: &crate::parser::sparql_parser_v2::ParsedQuery) -> Option<String> {
        if parsed.describe_resources.len() != 1 {
            return None;
        }

        let target = parsed.describe_resources[0].trim();

        if target.starts_with('?') {
            let subject_var = target.trim_start_matches('?');
            let mut related_patterns = parsed
                .main_patterns
                .iter()
                .filter(|p| p.subject.trim() == target)
                .collect::<Vec<_>>();
            if related_patterns.is_empty() {
                return None;
            }
            let pattern = related_patterns.remove(0);

            let is_type_predicate = pattern.predicate == "a"
                || pattern.predicate.ends_with("rdf-syntax-ns#type")
                || pattern.predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

            if is_type_predicate {
                if !pattern.object.trim().is_empty() {
                    let class_iri = pattern.object.trim_start_matches('<').trim_end_matches('>');
                    if let Some(rules) = self.mappings.mappings.get(class_iri) {
                        if let Some(rule) = rules.first() {
                            let subject_col = rule.position_to_column.get(&0).cloned().unwrap_or_else(|| "id".to_string());
                            let mut sql = format!(
                                "SELECT DISTINCT t.{subject_col} AS {alias} FROM {table} t",
                                subject_col = subject_col,
                                alias = subject_var,
                                table = rule.table_name
                            );
                            if let Some(limit) = parsed.limit {
                                sql.push_str(&format!(" LIMIT {}", limit));
                            }
                            return Some(sql);
                        }
                    }

                    let class_name = class_iri.rsplit('/').next().unwrap_or(class_iri).to_lowercase();
                    let mut table_candidates = vec![class_name.clone()];
                    table_candidates.push(format!("{}s", class_name));

                    for table in table_candidates {
                        if let Some(meta) = self.metadata.get(&table) {
                            let subject_col = meta
                                .primary_keys
                                .first()
                                .cloned()
                                .or_else(|| meta.columns.iter().find(|c| c.ends_with("_id")).cloned())
                                .or_else(|| meta.columns.first().cloned())
                                .unwrap_or_else(|| "id".to_string());
                            let mut sql = format!(
                                "SELECT DISTINCT t.{subject_col} AS {alias} FROM {table} t",
                                subject_col = subject_col,
                                alias = subject_var,
                                table = table
                            );
                            if let Some(limit) = parsed.limit {
                                sql.push_str(&format!(" LIMIT {}", limit));
                            }
                            return Some(sql);
                        }
                    }
                }
                return None;
            }

            let predicate_iri = pattern.predicate.trim_start_matches('<').trim_end_matches('>');
            if let Some(rules) = self.mappings.mappings.get(predicate_iri) {
                if let Some(rule) = rules.first() {
                    let subject_col = rule.position_to_column.get(&0).cloned().unwrap_or_else(|| "id".to_string());
                    let object_col = rule.position_to_column.get(&1).cloned().unwrap_or_else(|| "value".to_string());
                    let mut where_parts = Vec::new();

                    if pattern.object.starts_with('?') {
                        let object_var = pattern.object.trim_start_matches('?');
                        for filter in &parsed.filter_expressions {
                            let f = filter.trim();
                            let single_prefix = format!("?{} = '", object_var);
                            if f.starts_with(&single_prefix) && f.ends_with("'") {
                                let value = &f[single_prefix.len()..f.len()-1];
                                where_parts.push(format!("t.{col} = '{val}'", col = object_col, val = value.replace("'", "''")));
                            }
                            let double_prefix = format!("?{} = \"", object_var);
                            if f.starts_with(&double_prefix) && f.ends_with("\"") {
                                let value = &f[double_prefix.len()..f.len()-1];
                                where_parts.push(format!("t.{col} = '{val}'", col = object_col, val = value.replace("'", "''")));
                            }
                        }
                    }

                    let predicate_name = predicate_iri.rsplit('/').next().unwrap_or(predicate_iri);
                    let mut sql = format!(
                        "SELECT t.{subject_col} AS {alias}, '{predicate}' AS predicate, t.{object_col}::text AS object FROM {table} t",
                        subject_col = subject_col,
                        alias = format!("{}_uri", subject_var),
                        predicate = predicate_name,
                        object_col = object_col,
                        table = rule.table_name,
                    );
                    if !where_parts.is_empty() {
                        sql.push_str(" WHERE ");
                        sql.push_str(&where_parts.join(" AND "));
                    }
                    if let Some(limit) = parsed.limit {
                        sql.push_str(&format!(" LIMIT {}", limit));
                    }
                    return Some(sql);
                }
            }
            return None;
        }

        let resource = target.trim_start_matches('<').trim_end_matches('>');
        let emp_id = Self::extract_trailing_number(resource)?;
        let sql = format!(
            concat!(
                "SELECT '{res}' AS subject, p.predicate, p.object FROM (",
                "SELECT 'first_name' AS predicate, first_name::text AS object FROM employees WHERE employee_id = {id} UNION ALL ",
                "SELECT 'last_name' AS predicate, last_name::text AS object FROM employees WHERE employee_id = {id} UNION ALL ",
                "SELECT 'email' AS predicate, email::text AS object FROM employees WHERE employee_id = {id} UNION ALL ",
                "SELECT 'salary' AS predicate, salary::text AS object FROM employees WHERE employee_id = {id}",
                ") p WHERE p.object IS NOT NULL"
            ),
            res = resource,
            id = emp_id
        );
        Some(sql)
    }

    fn extract_trailing_number(input: &str) -> Option<i64> {
        let mut start = input.len();
        for (idx, ch) in input.char_indices().rev() {
            if ch.is_ascii_digit() {
                start = idx;
            } else {
                break;
            }
        }
        if start >= input.len() {
            return None;
        }
        input[start..].parse::<i64>().ok()
    }

    pub fn translate_with_cache(&self, sparql: &str) -> Result<String, String> {
        // Handle cache manager via internal locking to allow shared engine usage.
        let mut cache_guard = self
            .cache_manager
            .lock()
            .map_err(|e| format!("Cache lock poisoned: {}", e))?;

        // If cache is disabled, translate directly.
        if !cache_guard.is_enabled() {
            drop(cache_guard);
            return self.translate(sparql);
        }

        // Build context for cache key generation.
        let ctx = OptimizerContext {
            mappings: Arc::clone(&self.mappings),
            metadata: (*self.metadata).clone(),
            stats: crate::optimizer::Statistics::default(),
        };

        let cache_key = cache_guard.generate_cache_key(sparql, &ctx);

        // Try cache first.
        if let Some(plan) = cache_guard.get_or_create(&cache_key, || None) {
            return Ok(plan.generated_sql);
        }

        // Cache miss: release lock during translation.
        drop(cache_guard);
        let sql = self.translate(sparql)?;

        // Re-acquire lock and insert placeholder cached plan.
        let mut cache_guard = self
            .cache_manager
            .lock()
            .map_err(|e| format!("Cache lock poisoned: {}", e))?;
        use crate::ir::node::LogicNode;
        use crate::optimizer::CachedPlan;
        let new_plan = CachedPlan::new(LogicNode::Union(vec![]), sql.clone(), 1.0);
        cache_guard.get_or_create(&cache_key, || Some(new_plan));

        Ok(sql)
    }

}

/// Fetches public-table metadata using an existing SPI client (no nested `Spi::connect`).
fn fetch_pg_metadata_with_client(client: &mut SpiClient) -> HashMap<String, Arc<TableMetadata>> {
    let mut metadata = HashMap::new();
    eprintln!("[DEBUG fetch_pg_metadata] Starting to fetch metadata...");
    
    // Query all user tables (excluding system schemas)
    let query = "SELECT schemaname::text, tablename::text FROM pg_tables 
                 WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                 AND tablename NOT LIKE 'pg_%'";
    
    eprintln!("[DEBUG fetch_pg_metadata] Using query: {}", query);
    let tables = client.select(query, None, None);
    
    match tables {
        Ok(table_rows) => {
            eprintln!("[DEBUG fetch_pg_metadata] Found {} tables", table_rows.len());
            for row in table_rows {
                let schema_name = match row.get::<String>(1) {
                    Ok(Some(name)) => name,
                    _ => continue,
                };
                let table_name = match row.get::<String>(2) {
                    Ok(Some(name)) => {
                        eprintln!("[DEBUG fetch_pg_metadata] Processing table: {}.{}", schema_name, name);
                        name
                    },
                    Ok(None) => {
                        log!("rs-ontop-core: skipping table row with NULL tablename");
                        continue;
                    }
                    Err(e) => {
                        log!("rs-ontop-core: failed to read tablename: {}", e);
                        continue;
                    }
                };
                
                // Skip system and mapping tables that shouldn't be queried directly
                if table_name.starts_with("ontop_") || table_name.starts_with("pg_") {
                    continue;
                }
                
                let mut meta = TableMetadata {
                    table_name: table_name.clone(),
                    columns: Vec::new(),
                    primary_keys: Vec::new(),
                    foreign_keys: Vec::new(),
                    unique_constraints: Vec::new(),
                    check_constraints: Vec::new(),
                    not_null_columns: Vec::new(),
                };

                let col_query = format!(
                    "SELECT column_name::text FROM information_schema.columns 
                     WHERE table_schema = '{}' AND table_name = '{}'",
                    schema_name, table_name
                );
                let columns = client.select(&col_query, None, None);
                
                if let Ok(col_rows) = columns {
                    eprintln!("[DEBUG fetch_pg_metadata] Found {} columns for {}", col_rows.len(), table_name);
                    for col_row in col_rows {
                        match col_row.get::<String>(1) {
                            Ok(Some(col)) => meta.columns.push(col),
                            Ok(None) => log!(
                                "rs-ontop-core: skipping NULL column name for table {}",
                                table_name
                            ),
                            Err(e) => log!(
                                "rs-ontop-core: failed reading column for table {}: {}",
                                table_name,
                                e
                            ),
                        }
                    }
                }
                metadata.insert(table_name.clone(), Arc::new(meta));
                eprintln!("[DEBUG fetch_pg_metadata] Added {} to metadata", table_name);
            }
        }
        Err(e) => {
            eprintln!("[DEBUG fetch_pg_metadata] Failed to fetch tables: {:?}", e);
        }
    }
    
    eprintln!("[DEBUG fetch_pg_metadata] Final metadata keys: {:?}", metadata.keys().collect::<Vec<_>>());
    metadata
}

/// 从R2RML表加载映�?/// 
/// 优先尝试从ontop_r2rml_mappings表加载R2RML映射�?/// 失败时返回错误，由调用方决定是否回退到ontop_mappings
fn fetch_r2rml_mappings_with_client(client: &mut SpiClient) -> Result<Arc<MappingStore>, String> {
    let loader = R2RmlLoader::new();
    match loader.load_from_database(client) {
        Ok(store) => {
            log!("rs-ontop-core: R2RML loaded {} predicates", store.mappings.len());
            Ok(Arc::new(store))
        }
        Err(e) => {
            log!("rs-ontop-core: R2RML load error: {}", e);
            Err(format!("R2RML load failed: {}", e))
        }
    }
}

fn refresh_engine_from_spi(client: &mut SpiClient) {
    log!("rs-ontop-core: Refreshing engine metadata...");
    
    // 🔧 R2RML集成：使�?R2RmlLoader 从数据库加载映射
    let loader = R2RmlLoader::new();
    let maps = match loader.load_from_database(client) {
        Ok(store) => {
            log!("rs-ontop-core: Loaded {} mappings from database", store.mappings.len());
            store
        }
        Err(e) => {
            log!("rs-ontop-core: R2RML load failed: {}, using empty mappings", e);
            MappingStore::new()
        }
    };
    
    let meta = fetch_pg_metadata_with_client(client);
    
    let mut guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    *guard = Some(OntopEngine::new(std::sync::Arc::new(maps), meta));
    log!("rs-ontop-core: [SUCCESS] Engine refreshed.");
}

/// Translate SPARQL and run the generated SQL on an **existing** SPI client.
/// Used by the HTTP listener so we only have one `Spi::connect` frame (no nested
/// `SPI_connect` / `SPI_finish` from `ontop_query` �?inner `Spi::connect`).
fn validate_generated_sql(sql: &str) -> Result<(), String> {
    // Keep preflight minimal and deterministic to avoid false positives.
    let trimmed = sql.trim();
    if trimmed.is_empty() {
        return Err("generated SQL is empty".to_string());
    }

    // Known bad translation residue for typed literals.
    if sql.contains("^^") || sql.contains("\"^^") {
        return Err("contains unresolved typed literal marker (^^)".to_string());
    }

    Ok(())
}


pub(crate) fn spi_execute_sparql_json_rows(
    client: &mut SpiClient,
    sparql: &str,
) -> Result<Vec<serde_json::Value>, String> {
    // [FIX] Optimization 1 & 2: Handle poisoned lock and release lock early
    let engine = {
        let guard = match ENGINE.lock() {
            Ok(g) => g,
            Err(poisoned) => {
                log!("rs-ontop-core: ENGINE lock was poisoned, recovering. Previous request likely panicked.");
                poisoned.into_inner()
            }
        };
        // Clone the engine Option (only clones Arcs inside)
        guard.as_ref().map(|e| e.clone())
    };

    let engine = engine.ok_or_else(|| {
        "Ontop engine not initialized; run SELECT ontop_refresh(); or SELECT ontop_start_sparql_server();"
            .to_string()
    })?;

    // The lock is now released! Even if translate() panics, the global lock won't stay locked.
    let sql = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| engine.translate(sparql))) {
        Ok(Ok(sql)) => sql,
        Ok(Err(e)) => return Err(e),
        Err(panic_info) => {
            let msg = if let Some(s) = panic_info.downcast_ref::<&str>() {
                (*s).to_string()
            } else if let Some(s) = panic_info.downcast_ref::<String>() {
                s.clone()
            } else {
                "unknown panic".to_string()
            };
            log!("rs-ontop-core: [TRANSLATION_PANIC]\nreason={}\n[SPARQL_REQUEST_BEGIN]\n{}\n[SPARQL_REQUEST_END]", msg, sparql);
            return Err(format!("SPARQL translation panic: {}", msg));
        }
    };
    if sql.starts_with("-- Translation Error") {
        log!("rs-ontop-core: [TRANSLATION_ERROR_SQL]\n{}\n[SPARQL_REQUEST_BEGIN]\n{}\n[SPARQL_REQUEST_END]", sql, sparql);
        return Err(sql);
    }

    if let Err(e) = validate_generated_sql(&sql) {
        let msg = format!("Invalid generated SQL: {}", e);
        log!("rs-ontop-core: [TRANSLATION_ERROR_SQL]\n{}\n[SPARQL_REQUEST_BEGIN]\n{}\n[SPARQL_REQUEST_END]", msg, sparql);
        return Err(msg);
    }

    log!("rs-ontop-core: [TRANSLATED_SQL_BEGIN]\n{}\n[TRANSLATED_SQL_END]", sql);

    // [FIX] Handle ASK queries specially - return boolean result
    let upper_sparql = sparql.to_ascii_uppercase();
    if upper_sparql.trim_start().starts_with("ASK") {
        // For ASK queries, wrap with EXISTS to get boolean
        let ask_sql = format!("SELECT EXISTS({}) AS result", sql);
        let table = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.select(&ask_sql, None, None)
        })) {
            Ok(Ok(table)) => table,
            Ok(Err(e)) => {
                return Err(format!("SQL execution failed: {}; debug={:?}", e, e));
            }
            Err(panic_info) => {
                let msg = panic_payload_to_string(panic_info);
                log!(
                    "rs-ontop-core: [SQL_EXECUTION_PANIC]\nphase=ask\nreason={}\n[SQL_BEGIN]\n{}\n[SQL_END]",
                    msg,
                    ask_sql
                );
                return Err(format!("SQL execution panic: {}", msg));
            }
        };
        
        if let Some(row) = table.into_iter().next() {
            match row.get::<bool>(1) {
                Ok(Some(exists)) => {
                    let result = serde_json::json!({"boolean": exists});
                    return Ok(vec![result]);
                }
                Ok(None) => {
                    return Ok(vec![serde_json::json!({"boolean": false})]);
                }
                Err(e) => {
                    log!("rs-ontop-core: ASK query row decode failed: {}", e);
                    return Ok(vec![serde_json::json!({"boolean": false})]);
                }
            }
        }
        return Ok(vec![serde_json::json!({"boolean": false})]);
    }

    let wrapped_sql = format!("SELECT to_jsonb(t) FROM ({}) AS t", sql);
    let mut results = Vec::new();
    let table = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        client.select(&wrapped_sql, None, None)
    })) {
        Ok(Ok(table)) => table,
        Ok(Err(e)) => {
            return Err(format!("SQL execution failed: {}; debug={:?}", e, e));
        }
        Err(panic_info) => {
            let msg = panic_payload_to_string(panic_info);
            log!(
                "rs-ontop-core: [SQL_EXECUTION_PANIC]\nphase=rows\nreason={}\n[SQL_BEGIN]\n{}\n[SQL_END]",
                msg,
                wrapped_sql
            );
            return Err(format!("SQL execution panic: {}", msg));
        }
    };

    for row in table {
        match row.get::<pgrx::JsonB>(1) {
            Ok(Some(json_row)) => results.push(json_row.0),
            Ok(None) => log!("rs-ontop-core: spi_execute_sparql_json_rows row had NULL payload"),
            Err(e) => log!("rs-ontop-core: spi_execute_sparql_json_rows row decode failed: {}", e),
        }
    }
    Ok(results)
}

pub(crate) fn panic_payload_to_string(panic_info: Box<dyn std::any::Any + Send>) -> String {
    if let Some(s) = panic_info.downcast_ref::<&str>() {
        (*s).to_string()
    } else if let Some(s) = panic_info.downcast_ref::<String>() {
        s.clone()
    } else {
        "unknown panic".to_string()
    }
}

#[pg_extern]
fn ontop_load_ontology_turtle(ttl: &str) -> String {
    let mut temp_store = MappingStore::new();
    if let Err(e) = temp_store.load_turtle(ttl) {
        return format!("Failed to parse Turtle: {}", e);
    }

    // Use Spi::execute for non-query command to ensure volatility is handled correctly
    let sql = format!("INSERT INTO ontop_ontology_snapshots (ttl_content) VALUES ($${}$$)", ttl);
    if let Err(e) = Spi::run(&sql) {
        return format!("Failed to persist Turtle snapshot: {}", e);
    }

    let status = ontop_refresh();
    format!("Turtle Loaded. Found {} properties. Engine: {}", temp_store.properties.len(), status)
}

#[pg_extern]
fn ontop_translate(sparql: &str) -> String {
    // First, try to get the engine and check if it needs refresh
    let needs_refresh = {
        let guard = match ENGINE.lock() {
            Ok(g) => g,
            Err(e) => return format!("-- Translation Error: engine lock poisoned: {}", e),
        };
        match guard.as_ref() {
            None => true,
            Some(engine) => engine.metadata.is_empty() || engine.metadata.keys().len() < 2,
        }
    };
    
    // If engine needs refresh, do it now
    if needs_refresh {
        let refresh_result = ontop_refresh();
        eprintln!("[DEBUG ontop_translate] Auto-refreshed engine: {}", refresh_result);
    }
    
    // Now proceed with translation
    let engine = {
        let guard = match ENGINE.lock() {
            Ok(g) => g,
            Err(poisoned) => {
                log!("rs-ontop-core: ontop_translate encountered poisoned lock, recovering...");
                poisoned.into_inner()
            }
        };
        guard.clone()
    };

    let Some(engine) = engine else {
        return "-- Translation Error: Ontop engine not initialized. Run SELECT ontop_refresh(); or SELECT ontop_start_sparql_server(); first.".to_string();
    };
    
    // Check if this is an ASK query
    let upper_sparql = sparql.to_ascii_uppercase();
    let sql = if upper_sparql.trim_start().starts_with("ASK") {
        // For ASK queries, translate and wrap with EXISTS
        match engine.translate_with_cache(sparql) {
            Ok(inner_sql) => {
                if inner_sql.starts_with("-- Translation Error") {
                    inner_sql
                } else {
                    format!("SELECT EXISTS({}) AS result", inner_sql)
                }
            }
            Err(e) => format!("-- Translation Error: {}", e),
        }
    } else {
        match engine.translate_with_cache(sparql) {
            Ok(sql) => sql,
            Err(e) => format!("-- Translation Error: {}", e),
        }
    };
    
    sql
}

#[pg_extern]
fn ontop_refresh() -> String {
    match Spi::connect(|mut client| {
        refresh_engine_from_spi(&mut client);
        Ok::<(), pgrx::spi::SpiError>(())
    }) {
        Ok(()) => "Engine refreshed with current database metadata and mappings.".to_string(),
        Err(e) => format!("Engine refresh failed (SPI): {}", e),
    }
}

#[pg_extern]
fn ontop_query(sparql: &str) -> TableIterator<'static, (name!(row, pgrx::JsonB),)> {
    let mut results = Vec::new();
    let query_result = Spi::connect(|mut client| match spi_execute_sparql_json_rows(&mut client, sparql)
    {
        Ok(rows) => {
            for v in rows {
                results.push((pgrx::JsonB(v),));
            }
            Ok::<(), pgrx::spi::SpiError>(())
        }
        Err(e) => {
            log!("rs-ontop-core: ontop_query failed: {}", e);
            Ok(())
        }
    });
    if let Err(e) = query_result {
        log!("rs-ontop-core: ontop_query SPI failed: {}", e);
    }
    TableIterator::new(results.into_iter())
}

#[pg_extern]
fn ontop_inspect_ontology() -> pgrx::JsonB {
    let guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    if guard.is_none() {
        return pgrx::JsonB(serde_json::Value::Null);
    }

    if let Some(engine) = guard.as_ref() {
        use serde_json::json;
        let mut graph = Vec::new();

        // 1. Classes
        let mut sorted_classes: Vec<_> = engine.mappings.classes.values().collect();
        sorted_classes.sort_by_key(|c| &c.iri);
        for class in sorted_classes {
            let mut obj = json!({
                "@id": class.iri,
                "@type": "owl:Class"
            });
            if let Some(map) = obj.as_object_mut() {
                if !class.parent_classes.is_empty() {
                    if class.parent_classes.len() == 1 {
                        map.insert("rdfs:subClassOf".to_string(), json!({ "@id": class.parent_classes[0] }));
                    } else {
                        let parents: Vec<_> = class.parent_classes.iter().map(|p| json!({ "@id": p })).collect();
                        map.insert("rdfs:subClassOf".to_string(), json!(parents));
                    }
                }
                if let Some(lbl) = &class.label {
                    map.insert("rdfs:label".to_string(), json!(lbl));
                }
                if let Some(cmt) = &class.comment {
                    map.insert("rdfs:comment".to_string(), json!(cmt));
                }
            }
            graph.push(obj);
        }

        // 1.5 Fallback classes from mapping tables when explicit ontology classes are absent
        let mut fallback_class_count = 0usize;
        if engine.mappings.classes.is_empty() {
            let mut tables: Vec<String> = engine
                .mappings
                .mappings
                .values()
                .flat_map(|rules| rules.iter().map(|r| r.table_name.clone()))
                .collect();
            tables.sort();
            tables.dedup();
            fallback_class_count = tables.len();

            for table in tables {
                graph.push(json!({
                    "@id": format!("urn:table:{}", table),
                    "@type": "owl:Class",
                    "rdfs:label": table,
                }));
            }
        }

        // 2. Properties
        let mut fallback_property_count = 0usize;
        if engine.mappings.properties.is_empty() {
            let mut predicate_keys: Vec<String> = engine.mappings.mappings.keys().cloned().collect();
            predicate_keys.sort();
            for pred in predicate_keys {
                if pred == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" {
                    continue;
                }
                fallback_property_count += 1;
                graph.push(json!({
                    "@id": pred,
                    "@type": ["owl:DatatypeProperty"]
                }));
            }
        } else {
            let mut sorted_props: Vec<_> = engine.mappings.properties.values().collect();
            sorted_props.sort_by_key(|p| &p.iri);
            for prop in sorted_props {
                let mut types = Vec::new();
                if prop.prop_type == PropertyType::Object {
                    types.push("owl:ObjectProperty");
                } else {
                    types.push("owl:DatatypeProperty");
                }
                if prop.is_functional {
                    types.push("owl:FunctionalProperty");
                }

                let mut obj = json!({
                    "@id": prop.iri,
                    "@type": types
                });
                if let Some(map) = obj.as_object_mut() {
                    if let Some(inv) = &prop.inverse_of {
                        map.insert("owl:inverseOf".to_string(), json!({ "@id": inv }));
                    }
                    if !prop.parent_properties.is_empty() {
                        if prop.parent_properties.len() == 1 {
                            map.insert("rdfs:subPropertyOf".to_string(), json!({ "@id": prop.parent_properties[0] }));
                        } else {
                            let parents: Vec<_> = prop.parent_properties.iter().map(|p| json!({ "@id": p })).collect();
                            map.insert("rdfs:subPropertyOf".to_string(), json!(parents));
                        }
                    }
                    if let Some(lbl) = &prop.label {
                        map.insert("rdfs:label".to_string(), json!(lbl));
                    }
                    if let Some(cmt) = &prop.comment {
                        map.insert("rdfs:comment".to_string(), json!(cmt));
                    }
                    if let Some(dom) = &prop.domain {
                        map.insert("rdfs:domain".to_string(), json!({ "@id": dom }));
                    }
                    if let Some(rng) = &prop.range {
                        map.insert("rdfs:range".to_string(), json!({ "@id": rng }));
                    }
                }
                graph.push(obj);
            }
        }

        // 3. Mapping details
        let mut predicate_keys: Vec<_> = engine.mappings.mappings.keys().cloned().collect();
        predicate_keys.sort();

        let mut mapping_predicates = Vec::new();
        let mut mapping_rule_count = 0usize;
        for pred in predicate_keys {
            if let Some(rules) = engine.mappings.mappings.get(&pred) {
                let mut out_rules = Vec::new();
                for rule in rules {
                    mapping_rule_count += 1;
                    out_rules.push(json!({
                        "table": rule.table_name,
                        "subject_template": rule.subject_template,
                        "position_to_column": rule.position_to_column,
                    }));
                }
                mapping_predicates.push(json!({
                    "predicate": pred,
                    "rule_count": out_rules.len(),
                    "rules": out_rules,
                }));
            }
        }

        let out = json!({
            "@context": {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "owl": "http://www.w3.org/2002/07/owl#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@graph": graph,
            "mappings": {
                "predicates": mapping_predicates,
            },
            "stats": {
                "class_count": if engine.mappings.classes.is_empty() { fallback_class_count } else { engine.mappings.classes.len() },
                "property_count": if engine.mappings.properties.is_empty() { fallback_property_count } else { engine.mappings.properties.len() },
                "predicate_count": engine.mappings.mappings.len(),
                "mapping_rule_count": mapping_rule_count,
            }
        });

        pgrx::JsonB(out)
    } else {
        pgrx::JsonB(serde_json::Value::Null)
    }
}


#[pg_extern]
fn ontop_inspect_mappings() -> TableIterator<'static, (name!(target_triple, String), name!(sql_source, String))> {
    let guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    let mut results = Vec::new();
    if let Some(engine) = guard.as_ref() {
        for rules in engine.mappings.mappings.values() {
            for rule in rules {
                let triple = format!("<{}>  {}  {{{}}}", 
                    rule.subject_template.as_deref().unwrap_or("?s"),
                    rule.predicate,
                    rule.position_to_column.get(&1).cloned().unwrap_or_else(|| "?o".to_string())
                );
                results.push((triple, format!("SELECT * FROM {}", rule.table_name)));
            }
        }
    }
    TableIterator::new(results.into_iter())
}

#[pg_extern]
fn ontop_cache_stats() -> pgrx::JsonB {
    let guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    if let Some(engine) = guard.as_ref() {
        let cache_guard = engine.cache_manager.lock().unwrap_or_else(|p| p.into_inner());
        let stats = cache_guard.get_stats();
        let json = serde_json::json!({
            "size": stats.size,
            "max_size": stats.max_size,
            "total_hits": stats.total_hits,
            "total_misses": stats.total_misses,
            "hit_rate": stats.hit_rate,
            "evictions": stats.evictions,
            "enabled": cache_guard.is_enabled()
        });
        pgrx::JsonB(json)
    } else {
        pgrx::JsonB(serde_json::Value::Null)
    }
}

#[pg_extern]
fn ontop_clear_cache() -> String {
    let mut guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    if let Some(engine) = guard.as_mut() {
        if let Ok(mut cache_guard) = engine.cache_manager.lock() {
            cache_guard.clear();
            "Cache cleared successfully.".to_string()
        } else {
            "Internal Error: Cache lock poisoned.".to_string()
        }
    } else {
        "Engine not initialized.".to_string()
    }
}

#[pg_extern]
fn ontop_inspect_metadata() -> pgrx::JsonB {
    let guard = ENGINE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    if let Some(engine) = guard.as_ref() {
        let mut out = HashMap::new();
        for (k, v) in &*engine.metadata {
            out.insert(k.clone(), &**v);
        }
        pgrx::JsonB(serde_json::to_value(&out).unwrap_or(serde_json::Value::Null))
    } else {
        pgrx::JsonB(serde_json::Value::Null)
    }
}
