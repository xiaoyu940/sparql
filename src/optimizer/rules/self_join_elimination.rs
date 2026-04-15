use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};

pub struct SelfJoinEliminationPass;

impl SelfJoinEliminationPass {
    pub fn new() -> Self {
        Self
    }

    /// Try to merge two ExtensionalData nodes if they belong to the same table and join on the PK.
    fn try_merge(&self, n1: &LogicNode, n2: &LogicNode) -> Option<LogicNode> {
        if let (LogicNode::ExtensionalData { table_name: t1, column_mapping: m1, metadata: md1 },
                LogicNode::ExtensionalData { table_name: t2, column_mapping: m2, metadata: _md2 }) = (n1, n2) {
            
            if t1 == t2 {
                // Check if they are joined on ALL primary key columns.
                let mut pk_joined = true;
                for pk_col in &md1.primary_keys {
                    // find which variable maps to this pk_col in both
                    let var1 = m1.iter().find(|(_, col)| *col == pk_col).map(|(v, _)| v);
                    let var2 = m2.iter().find(|(_, col)| *col == pk_col).map(|(v, _)| v);

                    if let (Some(v1), Some(v2)) = (var1, var2) {
                        if v1 != v2 {
                            // If they maps to different variables, we must ensure they are unified.
                            // However, at this high-level, if they are the SAME variable, it's a join on PK.
                            // If different, they might be unified later; let's keep it simple for now:
                            // They must use the same variable name.
                            pk_joined = false;
                        }
                    } else {
                        pk_joined = false;
                    }
                }

                if pk_joined && !md1.primary_keys.is_empty() {
                    // Merge!
                    let mut merged_mapping = m1.clone();
                    for (v, c) in m2 {
                        merged_mapping.insert(v.clone(), c.clone());
                    }
                    return Some(LogicNode::ExtensionalData {
                        table_name: t1.clone(),
                        column_mapping: merged_mapping,
                        metadata: md1.clone(),
                    });
                }
            }
        }
        None
    }
}

impl OptimizerPass for SelfJoinEliminationPass {
    fn name(&self) -> &str {
        "SelfJoinEliminationPass"
    }

    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        // Deep traversal
        match node {
            LogicNode::Join { children, .. } => {
                // Post-order: process children first.
                for child in children.iter_mut() {
                    self.apply(child, ctx);
                }

                // Attempt merging adjacent children for simplicity (can be N-way later)
                let mut i = 0;
                while i < children.len() {
                    let mut j = i + 1;
                    while j < children.len() {
                        if let Some(merged) = self.try_merge(&children[i], &children[j]) {
                            children[i] = merged;
                            children.remove(j);
                            // continue j at same level
                        } else {
                            j += 1;
                        }
                    }
                    i += 1;
                }
            }
            LogicNode::Construction { child, .. } => self.apply(child, ctx),
            LogicNode::Filter { child, .. } => self.apply(child, ctx),
            LogicNode::Union(children) => {
                for child in children {
                    self.apply(child, ctx);
                }
            }
            _ => {}
        }
    }
}
