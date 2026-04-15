//! SQL Cost Model 
//!
//! Evaluates the expected cardinality / executing cost of a given logical plan.

use crate::ir::node::{LogicNode, JoinType};
use crate::optimizer::statistics::Statistics;
use crate::optimizer::selectivity::{SelectivityEstimator, BasicSelectivityEstimator};

pub struct CostModel<'a> {
    pub statistics: &'a Statistics,
}

impl<'a> CostModel<'a> {
    pub fn new(statistics: &'a Statistics) -> Self {
        Self { statistics }
    }

    /// Recursively computes cardinality (rows expected)
    pub fn estimate_cardinality(&self, node: &LogicNode) -> f64 {
        match node {
            LogicNode::ExtensionalData { table_name, .. } => {
                if let Some(stats) = self.statistics.get_table_stats(table_name) {
                    stats.row_count as f64
                } else {
                    1000.0 // Default arbitrary DB size fallback
                }
            }
            LogicNode::IntensionalData { .. } => {
                1000.0 // Should usually be unfolded into ExtensionalData before cost is evaluated
            }
            LogicNode::Join { join_type, children, condition } => {
                if children.is_empty() { return 0.0; }
                
                let mut card = self.estimate_cardinality(&children[0]);
                for child in children.iter().skip(1) {
                    let c_card = self.estimate_cardinality(child);
                    // Standard inner join cardinality estimate using default cross-join times join_selectivity
                    match join_type {
                        JoinType::Inner | JoinType::Left => {
                            // Without explicit Foreign Key stats, assume a join selectivity
                            let join_sel = 0.01; 
                            card = card * c_card * join_sel;
                        }
                        _ => { card *= c_card; }
                    }
                }
                
                // If there is an overall condition, apply filter
                if let Some(cond) = condition {
                    let sel_est = BasicSelectivityEstimator::new(None, self.statistics);
                    card *= sel_est.estimate_expr(cond);
                }
                card.max(1.0)
            }
            LogicNode::Filter { expression, child } => {
                let child_card = self.estimate_cardinality(child);
                let sel_est = BasicSelectivityEstimator::new(None, self.statistics);
                (child_card * sel_est.estimate_expr(expression)).max(1.0)
            }
            LogicNode::Union(children) | LogicNode::GraphUnion { children, .. } => {
                let mut sum = 0.0;
                for child in children {
                    sum += self.estimate_cardinality(child);
                }
                sum.max(1.0)
            }
            LogicNode::Limit { limit, child, .. } => {
                let inner = self.estimate_cardinality(child);
                inner.min(*limit as f64)
            }
            LogicNode::Construction { child, .. } => {
                self.estimate_cardinality(child)
            }
            LogicNode::Aggregation { child, group_by, .. } => {
                let inner = self.estimate_cardinality(child);
                if group_by.is_empty() {
                    1.0 // Un-grouped aggregate produces 1 row
                } else {
                    // Estimate groups based on distinct values. Simplifying assuming grouping reduces sets a bit.
                    (inner * 0.1).max(1.0)
                }
            }
            LogicNode::Graph { child, .. } => self.estimate_cardinality(child),
            LogicNode::Values { rows, .. } => rows.len() as f64,
            LogicNode::Path { .. } => 1000.0,
            LogicNode::Service { inner_plan, .. } => self.estimate_cardinality(inner_plan),
            LogicNode::SubQuery { inner, .. } => self.estimate_cardinality(inner),
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                self.estimate_cardinality(outer) + self.estimate_cardinality(inner)
            }
            LogicNode::RecursivePath { .. } => 1000.0, // Estimate for recursive paths
        }
    }
}
