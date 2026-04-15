//! [S6-P1-2] Federation Module
//!
//! Implements the SPARQL 1.1 SERVICE federated query feature.
//!
//! # Architecture
//!
//! ```text
//!  SPARQL Query (contains SERVICE clause)
//!        │
//!        ▼  parsing + IR build
//!  LogicNode::Service { endpoint, output_vars, inner_plan, silent }
//!        │
//!        ▼  ServiceMaterializer::materialize_all (runs BEFORE SQL gen)
//!   HTTP POST ──► remote SPARQL JSON results
//!        │
//!        ▼  TempTableManager::materialize
//!   CREATE TEMPORARY TABLE _service_N (var1 TEXT, var2 TEXT, ...)
//!   INSERT rows ...
//!        │
//!        ▼  node rewritten to:
//!   LogicNode::ExtensionalData { table_name: "_service_N", ... }
//!        │
//!        ▼  normal SQL generation
//!   SELECT ... FROM _service_N JOIN local_table ON ...
//! ```

pub mod materializer;

pub use materializer::{ServiceMaterializer, TempTableManager, MaterializeError};
