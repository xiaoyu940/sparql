use crate::ir::node::LogicNode;

#[derive(Debug, Default)]
pub struct RedundantJoinElimination;

impl RedundantJoinElimination {
    pub fn apply(node: LogicNode) -> LogicNode {
        match node {
            LogicNode::Join {
                mut children,
                condition,
                join_type,
            } => {
                let mut deduped = Vec::new();
                for child in children.drain(..) {
                    if !deduped.iter().any(|c| is_same_scan(c, &child)) {
                        deduped.push(child);
                    }
                }
                if deduped.len() == 1 {
                    deduped.pop().unwrap_or(LogicNode::Union(Vec::new()))
                } else {
                    LogicNode::Join {
                        children: deduped,
                        condition,
                        join_type,
                    }
                }
            }
            other => other,
        }
    }
}

fn is_same_scan(left: &LogicNode, right: &LogicNode) -> bool {
    match (left, right) {
        (
            LogicNode::ExtensionalData {
                table_name: lt,
                column_mapping: lm,
                ..
            },
            LogicNode::ExtensionalData {
                table_name: rt,
                column_mapping: rm,
                ..
            },
        ) => lt == rt && lm == rm,
        _ => false,
    }
}
