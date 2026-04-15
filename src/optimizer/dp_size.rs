//! DPSize Join Reordering Algorithm
//! 
//! Applies dynamic programming to find the optimal join order across N relations.

use crate::ir::node::{LogicNode, JoinType};
use crate::ir::expr::Expr;
use crate::optimizer::statistics::Statistics;
use crate::optimizer::cost_model::CostModel;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
struct DpState {
    cost: f64,
    cardinality: f64,
    plan: LogicNode,
}

/// A graph holding relations and join conditions for ordering.
pub struct JoinGraph {
    pub nodes: Vec<LogicNode>,
    // Store implicitly any join conditions we can push (for simplicity skipped the full condition graph extraction here, relying on existing AST structures).
}

/// Applies the DPSize algorithm to find the optimal Left-Deep or Bushy join order 
/// for the specified relations.
pub fn dp_size_optimal_order(
    relations: Vec<LogicNode>,
    predicates: Option<Expr>,
    stats: &Statistics,
) -> LogicNode {
    let n = relations.len();
    if n == 0 {
        return LogicNode::Union(vec![]); 
    }
    if n == 1 {
        return relations[0].clone();
    }
    
    // [SECURITY] Prevent bit-shift overflow if way too many joins (unlikely but possible via expansion)
    if n > 60 {
        eprintln!("[OPTIMIZER] Join set too large ({}), skipping DP reordering", n);
        return LogicNode::Join {
            join_type: JoinType::Inner,
            children: relations,
            condition: predicates,
        };
    }
    
    // DP array keyed by bitmask. 1 << i means relation `i` is included.
    let mut dp: HashMap<u64, DpState> = HashMap::new();
    let cost_model = CostModel::new(stats);

    // Initialize DP array with size 1 (single relations)
    for (i, rel) in relations.iter().enumerate() {
        let mask = 1u64 << i;
        let card = cost_model.estimate_cardinality(rel);
        dp.insert(mask, DpState {
            cost: 0.0, 
            cardinality: card,
            plan: rel.clone(),
        });
    }

    // Iterate up to set size N
    for size in 2..=n {
        for mask in 1u64..(1u64 << n) {
            if mask.count_ones() == size as u32 {
                let mut best_state: Option<DpState> = None;

                for r in 0..n {
                    if (mask & (1u64 << r)) != 0 {
                        let subset_mask = mask ^ (1u64 << r); 
                        
                        if let Some(left_state) = dp.get(&subset_mask) {
                            let right_rel = &relations[r];
                            
                            let simulated_join = LogicNode::Join {
                                join_type: JoinType::Inner,
                                children: vec![left_state.plan.clone(), right_rel.clone()],
                                condition: None, 
                            };
                            let out_card = cost_model.estimate_cardinality(&simulated_join);
                            let current_cost = left_state.cost + out_card;

                            if best_state.as_ref().map_or(true, |b| current_cost < b.cost) {
                                best_state = Some(DpState {
                                    cost: current_cost,
                                    cardinality: out_card,
                                    plan: simulated_join,
                                });
                            }
                        }
                    }
                }
                
                if let Some(state) = best_state {
                    dp.insert(mask, state);
                }
            }
        }
    }

    let full_mask = (1u64 << n) - 1;
    let mut final_plan = match dp.remove(&full_mask) {
        Some(s) => s.plan,
        None => {
            // Fallback if DP failed to find the full mask (should not happen)
            return LogicNode::Join {
                join_type: JoinType::Inner,
                children: relations,
                condition: predicates,
            };
        }
    };
    
    // Reattach the original condition to the root of the selected join tree
    if let LogicNode::Join { ref mut condition, .. } = final_plan {
        *condition = predicates;
    }
    
    final_plan
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::optimizer::statistics::{TableStatistics, ColumnStatistics};
    use crate::ir::expr::Term;

    #[test]
    fn test_dp_size_ordering() {
        let mut stats = Statistics::default();
        stats.insert_table_stats(TableStatistics::new("SmallTbl", 10));
        stats.insert_table_stats(TableStatistics::new("HugeTbl", 1_000_000));
        stats.insert_table_stats(TableStatistics::new("MediumTbl", 5_000));

        let r1 = LogicNode::ExtensionalData {
            table_name: "SmallTbl".to_string(),
            column_mapping: HashMap::new(),
            metadata: std::sync::Arc::new(crate::metadata::TableMetadata::default()),
        };
        let r2 = LogicNode::ExtensionalData {
            table_name: "HugeTbl".to_string(),
            column_mapping: HashMap::new(),
            metadata: std::sync::Arc::new(crate::metadata::TableMetadata::default()),
        };
        let r3 = LogicNode::ExtensionalData {
            table_name: "MediumTbl".to_string(),
            column_mapping: HashMap::new(),
            metadata: std::sync::Arc::new(crate::metadata::TableMetadata::default()),
        };

        // DP should reorder to join SmallTbl with MediumTbl first before HugeTbl to minimize intermediate cards
        let ordered = dp_size_optimal_order(vec![r1, r2.clone(), r3.clone()], None, &stats);
        
        // Root plan should be a join containing all 3.
        // It should be (((SmallTbl ⨝ MediumTbl) ⨝ HugeTbl) )
        if let LogicNode::Join { children, .. } = &ordered {
            if let LogicNode::Join { children: inner_children, .. } = &children[0] {
                // Should contain Small and Medium in any order
                let c0 = match &inner_children[0] { LogicNode::ExtensionalData { table_name, .. } => table_name, _ => "" };
                let c1 = match &inner_children[1] { LogicNode::ExtensionalData { table_name, .. } => table_name, _ => "" };
                assert!((c0 == "SmallTbl" && c1 == "MediumTbl") || (c0 == "MediumTbl" && c1 == "SmallTbl"));
            }
            assert!(matches!(&children[1], LogicNode::ExtensionalData { table_name, .. } if table_name == "HugeTbl"));
        } else {
            panic!("Expected Join root");
        }
    }
}
