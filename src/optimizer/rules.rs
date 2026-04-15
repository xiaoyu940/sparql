pub mod unfolding;
pub mod self_join_elimination;
pub mod join_elimination;
pub mod left_to_inner;
pub mod predicate_pushdown;
pub mod union_lifting_fixed;
pub mod tree_witness;
pub mod normalize_projection;
pub mod prune_unused_columns;

pub use unfolding::*;
pub use self_join_elimination::*;
pub use join_elimination::*;
pub use predicate_pushdown::*;
pub use tree_witness::*;

// 重新导出别名
pub use union_lifting_fixed::UnionLiftingPass;
pub use left_to_inner::LeftToInnerJoinPass;
pub use normalize_projection::NormalizeProjectionPass;
pub use prune_unused_columns::PruneUnusedColumnsPass;
