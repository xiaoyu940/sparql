use std::sync::Arc;
use crate::ir::node::LogicNode;
use crate::mapping::MappingStore;
use crate::metadata::TableMetadata;
use std::collections::HashMap;

/// Global context for all optimization passes.
pub struct OptimizerContext {
    pub mappings: Arc<MappingStore>,
    pub metadata: HashMap<String, Arc<TableMetadata>>,
    pub stats: statistics::Statistics,
}

/// A single optimization rule or pass.
pub trait OptimizerPass: Sync {
    fn name(&self) -> &str;
    /// Process the current node and potentially modify its structure.
    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext);
}

pub mod rules;
pub mod cache;
pub mod pass_manager;
pub mod expression_optimizer;
pub mod parallel_optimizer;
pub mod visualizer;
pub mod redundant_elimination;
pub mod filter_pushdown;
pub mod join_reordering;
pub mod statistics;
pub mod selectivity;
pub mod cost_model;
pub mod dp_size;
pub mod stats_collector;

pub use rules::*;
pub use cache::*;
pub use pass_manager::*;
pub use expression_optimizer::*;
pub use parallel_optimizer::*;
pub use visualizer::*;
pub use redundant_elimination::*;
pub use filter_pushdown::*;
pub use join_reordering::*;
pub use statistics::*;
pub use selectivity::*;
pub use cost_model::*;
pub use dp_size::*;
pub use stats_collector::*;
