use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};

pub struct JoinEliminationPass;

impl JoinEliminationPass {
    pub fn new() -> Self {
        Self
    }
}

impl OptimizerPass for JoinEliminationPass {
    fn name(&self) -> &str {
        "JoinEliminationPass"
    }

    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            LogicNode::Join { children, .. } => {
                // First recurse
                for child in children.iter_mut() {
                    self.apply(child, ctx);
                }

                // FK-based Join Elimination:
                // If Join(T1, T2) on T1.fk = T2.pk, and T2 is not used in projections...
                
                let mut discarded_indices = std::collections::HashSet::new();
                
                // For simplicity, we compare every pair of children
                for i in 0..children.len() {
                    for j in 0..children.len() {
                        if i == j || discarded_indices.contains(&i) || discarded_indices.contains(&j) { continue; }
                        
                        if let (LogicNode::ExtensionalData { table_name: _t1, column_mapping: m1, metadata: md1 },
                                LogicNode::ExtensionalData { table_name: t2, column_mapping: m2, metadata: _md2 }) = (&children[i], &children[j]) {
                            
                            // Check if there is an FK from T1 to T2
                            for fk in &md1.foreign_keys {
                                if fk.target_table == *t2 {
                                    // Verify T1.fk matches T2.pk in the join condition
                                    // For a quick check: are they sharing variables on these columns?
                                    let mut pk_fk_match = true;
                                    for (k, local_col) in fk.local_columns.iter().enumerate() {
                                        let target_col = &fk.target_columns[k];
                                        
                                        let var_in_t1 = m1.iter().find(|(_, c)| *c == local_col).map(|(v, _)| v);
                                        let var_in_t2 = m2.iter().find(|(_, c)| *c == target_col).map(|(v, _)| v);
                                        
                                        if var_in_t1 != var_in_t2 || var_in_t1.is_none() {
                                            pk_fk_match = false;
                                            break;
                                        }
                                    }

                                    if pk_fk_match {
                                        // T1 depends on T2 via FK. 
                                        // Can T2 be removed? Yes, if NONE of T2's OTHER variables are used 
                                        // anywhere else in the query.
                                        
                                        // Determine which variables are EXCLUSIVE to T2 (except for the FK/PK join vars)
                                        let mut other_vars_used = false;
                                        let join_vars: std::collections::HashSet<_> = fk.target_columns.iter()
                                            .filter_map(|tc| m2.iter().find(|(_, c)| *c == tc).map(|(v, _)| v.clone()))
                                            .collect();

                                        for (var, _) in m2 {
                                            if !join_vars.contains(var) {
                                                // This variable is "new" from T2. Is it used?
                                                // (Checking globally is hard here, but we can check the parent's projected scope)
                                                // For a safe bet in this POC: if it's in m2, assume it's used unless analyzed.
                                                // BUT, if m2 ONLY contains join_vars, it's definitely safe to remove T2!
                                                other_vars_used = true;
                                                break;
                                            }
                                        }

                                        if !other_vars_used {
                                            // T2 is just a lookup for an FK that IS NOT NULL.
                                            // Safety: only if local_col is NOT NULL.
                                            let mut all_not_null = true;
                                            for local_col in &fk.local_columns {
                                                if !md1.not_null_columns.contains(local_col) {
                                                    all_not_null = false; break;
                                                }
                                            }

                                            if all_not_null {
                                                discarded_indices.insert(j);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                if !discarded_indices.is_empty() {
                    let mut new_children = Vec::new();
                    for (idx, child) in children.drain(..).enumerate() {
                        if !discarded_indices.contains(&idx) {
                            new_children.push(child);
                        }
                    }
                    *children = new_children;
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
