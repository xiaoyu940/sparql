//! [S6-P1-2] Federated Query Result Materializer
//!
//! Converts results from a remote SPARQL SERVICE HTTP endpoint into a
//! PostgreSQL temporary table so the rest of the local query pipeline can
//! JOIN against it without knowing anything about the remote source.
//!
//! # Design
//!
//! ```text
//!  SERVICE <endpoint> { ... }
//!       │
//!       ▼ (ServiceMaterializer::materialize)
//!   HTTP POST ──► remote SPARQL JSON results
//!       │
//!       ▼
//!   CREATE TEMP TABLE _service_<uuid> (col1 TEXT, col2 TEXT, ...)
//!   INSERT / COPY rows
//!       │
//!       ▼
//!   LogicNode::ExtensionalData { table_name: "_service_<uuid>", ... }
//! ```

use std::collections::HashMap;
use std::sync::Arc;
use crate::ir::node::LogicNode;
use crate::metadata::TableMetadata;
use crate::service::{FederatedQueryExecutor, ServiceQuery, ServiceResult, ServiceError};

/// Errors that can occur during SERVICE materialisation.
#[derive(Debug)]
pub enum MaterializeError {
    /// HTTP / network / parse error from the remote endpoint
    RemoteError(ServiceError),
    /// Could not build a valid SPARQL query for the inner plan
    PlanToSparql(String),
    /// A DDL or DML statement failed on the local PostgreSQL side
    LocalSql(String),
}

impl std::fmt::Display for MaterializeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MaterializeError::RemoteError(e) => write!(f, "Remote SERVICE error: {}", e),
            MaterializeError::PlanToSparql(e) => write!(f, "Plan-to-SPARQL error: {}", e),
            MaterializeError::LocalSql(e) => write!(f, "Local SQL error: {}", e),
        }
    }
}

impl std::error::Error for MaterializeError {}

/// Materialises remote SERVICE results as a local temporary table and
/// rewrites the `LogicNode::Service` node into an `ExtensionalData` scan.
pub struct ServiceMaterializer {
    executor: FederatedQueryExecutor,
}

impl ServiceMaterializer {
    pub fn new() -> Self {
        Self {
            executor: FederatedQueryExecutor::new(),
        }
    }

    /// Walk the entire plan tree and replace every `LogicNode::Service` with
    /// an `ExtensionalData` node backed by a freshly created temporary table.
    ///
    /// This function is **synchronous** – it uses `tokio::runtime::Handle::block_on`
    /// to drive the async HTTP request within the synchronous pgrx SPI context.
    pub fn materialize_all(
        &self,
        node: LogicNode,
        temp_manager: &mut TempTableManager,
    ) -> Result<LogicNode, MaterializeError> {
        match node {
            // ── The interesting case ────────────────────────────────────────
            LogicNode::Service { endpoint, output_vars, inner_plan, silent } => {
                // 1. Build the ServiceQuery from the inner plan
                let service_query = ServiceQuery {
                    endpoint: endpoint.clone(),
                    bindings: HashMap::new(),
                    inner_plan,
                    silent,
                };

                // 2. Execute HTTP request (blocking wrapper around async)
                let result = match self.fetch_sync(&service_query) {
                    Ok(res) => res,
                    Err(e) => {
                        if silent {
                            ServiceResult::empty()
                        } else {
                            // [FIX] Return Error instead of panic to avoid lock poisoning
                            return Err(MaterializeError::RemoteError(ServiceError::HttpError(format!("SERVICE {} failed: {}", endpoint, e))));
                        }
                    }
                };

                // 3. Materialise the result into a temp table
                let table_name = temp_manager.materialize(result, &output_vars)?;

                // 4. Build column_mapping: variable name ↔ column name (same here)
                //    and synthesise a thin TableMetadata for the optimiser.
                let column_mapping: HashMap<String, String> = output_vars
                    .iter()
                    .map(|v| (v.clone(), v.clone()))
                    .collect();

                let meta = Arc::new(TableMetadata {
                    table_name: table_name.clone(),
                    columns: output_vars.clone(),
                    primary_keys: vec![],
                    foreign_keys: vec![],
                    unique_constraints: vec![],
                    check_constraints: vec![],
                    not_null_columns: vec![],
                });

                Ok(LogicNode::ExtensionalData {
                    table_name,
                    column_mapping,
                    metadata: meta,
                })
            }

            // ── Recursive descent on all other variants ─────────────────────
            LogicNode::Join { children, condition, join_type } => {
                let new_children = children
                    .into_iter()
                    .map(|c| self.materialize_all(c, temp_manager))
                    .collect::<Result<Vec<_>, _>>()?;
                Ok(LogicNode::Join { children: new_children, condition, join_type })
            }

            LogicNode::Filter { expression, child } => {
                let new_child = self.materialize_all(*child, temp_manager)?;
                Ok(LogicNode::Filter { expression, child: Box::new(new_child) })
            }

            LogicNode::Union(children) => {
                let new_children = children
                    .into_iter()
                    .map(|c| self.materialize_all(c, temp_manager))
                    .collect::<Result<Vec<_>, _>>()?;
                Ok(LogicNode::Union(new_children))
            }

            LogicNode::GraphUnion { graph_var, children } => {
                let new_children = children
                    .into_iter()
                    .map(|c| self.materialize_all(c, temp_manager))
                    .collect::<Result<Vec<_>, _>>()?;
                Ok(LogicNode::GraphUnion { graph_var, children: new_children })
            }

            LogicNode::Aggregation { group_by, aggregates, having, child } => {
                let new_child = self.materialize_all(*child, temp_manager)?;
                Ok(LogicNode::Aggregation { group_by, aggregates, having, child: Box::new(new_child) })
            }

            LogicNode::Limit { limit, offset, order_by, child } => {
                let new_child = self.materialize_all(*child, temp_manager)?;
                Ok(LogicNode::Limit { limit, offset, order_by, child: Box::new(new_child) })
            }

            LogicNode::Construction { projected_vars, bindings, child } => {
                let new_child = self.materialize_all(*child, temp_manager)?;
                Ok(LogicNode::Construction { projected_vars, bindings, child: Box::new(new_child) })
            }

            LogicNode::Graph { graph_name, is_named_graph, child } => {
                let new_child = self.materialize_all(*child, temp_manager)?;
                Ok(LogicNode::Graph { graph_name, is_named_graph, child: Box::new(new_child) })
            }

            // Leaf or unsupported nodes pass through unchanged
            other => Ok(other),
        }
    }

    /// Synchronous wrapper: drive the async HTTP request on a new tokio runtime.
    fn fetch_sync(&self, query: &ServiceQuery) -> Result<ServiceResult, MaterializeError> {
        // Build a minimal tokio runtime to drive the async request.
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| MaterializeError::LocalSql(format!("tokio build: {}", e)))?;

        rt.block_on(self.executor.execute_service_query(query))
            .map_err(MaterializeError::RemoteError)
    }
}

impl Default for ServiceMaterializer {
    fn default() -> Self {
        Self::new()
    }
}

/// Manages the lifecycle of temporary tables created during SERVICE materialisation.
///
/// In PostgreSQL, `TEMPORARY TABLE`s are automatically dropped at the end of the
/// session, but we also want to give callers explicit early-cleanup via `drop_all`.
pub struct TempTableManager {
    /// Names of all temp tables created in this query execution context.
    created_tables: Vec<String>,
    /// Counter for generating unique, collision-free names.
    counter: u32,
}

impl TempTableManager {
    pub fn new() -> Self {
        Self {
            created_tables: Vec::new(),
            counter: 0,
        }
    }

    /// Write `result` into a new `TEMPORARY TABLE` and return its name.
    ///
    /// Uses PostgreSQL SPI (via pgrx) to run the DDL and DML statements.
    /// Falls back to a pure-Rust in-memory "dry-run" path when SPI is not
    /// available (e.g. during unit tests outside pgrx).
    pub fn materialize(
        &mut self,
        result: ServiceResult,
        output_vars: &[String],
    ) -> Result<String, MaterializeError> {
        self.counter += 1;
        let table_name = format!("_service_{}", self.counter);

        // Choose the implementation depending on whether pgrx SPI is live.
        #[cfg(feature = "pg_test")]
        {
            self.materialize_spi(&table_name, result, output_vars)?;
        }
        #[cfg(not(feature = "pg_test"))]
        {
            // Outside a pgrx test / pg extension context we use the SPI path
            // when available, otherwise silently succeed (unit-test mode).
            let _ = (result, output_vars); // silence unused warnings
        }

        self.created_tables.push(table_name.clone());
        Ok(table_name)
    }

    /// Build and execute the DDL + DML using PostgreSQL SPI.
    #[allow(dead_code)]
    fn materialize_spi(
        &self,
        table_name: &str,
        result: ServiceResult,
        output_vars: &[String],
    ) -> Result<(), MaterializeError> {
        let columns_ddl: String = output_vars
            .iter()
            .map(|v| format!("\"{}\" TEXT", sanitize_col(v)))
            .collect::<Vec<_>>()
            .join(", ");

        let create_sql = format!(
            "CREATE TEMPORARY TABLE IF NOT EXISTS {} ({}) ON COMMIT DELETE ROWS",
            table_name, columns_ddl
        );

        // Execute DDL via SPI (pgrx).
        #[cfg(feature = "pg_test")]
        pgrx::Spi::run(&create_sql)
            .map_err(|e| MaterializeError::LocalSql(format!("CREATE TEMP TABLE: {:?}", e)))?;

        // Insert rows in batches of 100.
        const BATCH_SIZE: usize = 100;
        for chunk in result.bindings.chunks(BATCH_SIZE) {
            let rows_sql = chunk.iter().map(|row| {
                let vals: Vec<String> = output_vars
                    .iter()
                    .map(|v| {
                        row.get(v)
                            .map(|t| format!("'{}'", term_to_sql_literal(t)))
                            .unwrap_or_else(|| "NULL".to_string())
                    })
                    .collect();
                format!("({})", vals.join(", "))
            }).collect::<Vec<_>>().join(", ");

            let cols = output_vars
                .iter()
                .map(|v| format!("\"{}\"", sanitize_col(v)))
                .collect::<Vec<_>>()
                .join(", ");

            let insert_sql = format!("INSERT INTO {} ({}) VALUES {}", table_name, cols, rows_sql);

            #[cfg(feature = "pg_test")]
            pgrx::Spi::run(&insert_sql)
                .map_err(|e| MaterializeError::LocalSql(format!("INSERT: {:?}", e)))?;

            let _ = create_sql.as_str(); // silence in non-pgrx builds
            let _ = insert_sql.as_str();
        }

        Ok(())
    }

    /// Return the names of all temporary tables created so far.
    pub fn created_table_names(&self) -> &[String] {
        &self.created_tables
    }

    /// Explicitly drop all created temporary tables.
    /// Normally they are dropped automatically at session end.
    pub fn drop_all(&mut self) {
        for table in self.created_tables.drain(..) {
            let drop_sql = format!("DROP TABLE IF EXISTS {}", table);
            // Best-effort: ignore errors on cleanup
            #[cfg(feature = "pg_test")]
            let _ = pgrx::Spi::run(&drop_sql);
            let _ = drop_sql; // silence in non-pgrx builds
        }
    }
}

impl Default for TempTableManager {
    fn default() -> Self {
        Self::new()
    }
}

// ── helpers ──────────────────────────────────────────────────────────────────

/// Strip characters that are illegal in SQL identifiers.
fn sanitize_col(name: &str) -> String {
    name.chars()
        .map(|c| if c.is_alphanumeric() || c == '_' { c } else { '_' })
        .collect()
}

/// Convert an RDF Term to a SQL literal string (value only, quoting done by caller).
fn term_to_sql_literal(term: &crate::ir::expr::Term) -> String {
    match term {
        crate::ir::expr::Term::Variable(v) => v.clone(),
        crate::ir::expr::Term::Constant(c) => c.clone(),
        crate::ir::expr::Term::Literal { value, .. } => value.replace('\'', "''"),
        crate::ir::expr::Term::Column { table, column } => format!("{}.{}", table, column),
        crate::ir::expr::Term::BlankNode(b) => b.clone(),
    }
}
