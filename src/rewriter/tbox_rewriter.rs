use std::collections::HashSet;

use crate::ir::node::LogicNode;
use crate::mapping::MappingStore;

/// Minimal TBox rewriting stage for Sprint2 P0-1.
/// Current coverage: rdfs:subClassOf and rdfs:subPropertyOf on IntensionalData predicates.
pub struct TBoxRewriter;

impl TBoxRewriter {
    pub fn rewrite(node: &LogicNode, mappings: &MappingStore) -> LogicNode {
        match node {
            LogicNode::Construction {
                projected_vars,
                bindings,
                child,
            } => LogicNode::Construction {
                projected_vars: projected_vars.clone(),
                bindings: bindings.clone(),
                child: Box::new(Self::rewrite(child, mappings)),
            },
            LogicNode::Join {
                children,
                condition,
                join_type,
            } => LogicNode::Join {
                children: children
                    .iter()
                    .map(|c| Self::rewrite(c, mappings))
                    .collect(),
                condition: condition.clone(),
                join_type: *join_type,
            },
            LogicNode::Filter { expression, child } => LogicNode::Filter {
                expression: expression.clone(),
                child: Box::new(Self::rewrite(child, mappings)),
            },
            LogicNode::Union(children) => {
                LogicNode::Union(children.iter().map(|c| Self::rewrite(c, mappings)).collect())
            }
            LogicNode::Aggregation {
                group_by,
                aggregates,
                having,
                child,
            } => LogicNode::Aggregation {
                group_by: group_by.clone(),
                aggregates: aggregates.clone(),
                having: having.clone(),
                child: Box::new(Self::rewrite(child, mappings)),
            },
            LogicNode::IntensionalData { predicate, args } => {
                let mut predicates = vec![predicate.clone()];

                if let Some(class_def) = mappings.classes.get(predicate) {
                    for parent in &class_def.parent_classes {
                        predicates.push(parent.clone());
                    }
                }

                if let Some(prop_def) = mappings.properties.get(predicate) {
                    for parent in &prop_def.parent_properties {
                        predicates.push(parent.clone());
                    }
                }

                let mut seen = HashSet::new();
                predicates.retain(|p| seen.insert(p.clone()));

                if predicates.len() == 1 {
                    return node.clone();
                }

                let branches = predicates
                    .into_iter()
                    .map(|pred| LogicNode::IntensionalData {
                        predicate: pred,
                        args: args.clone(),
                    })
                    .collect();
                LogicNode::Union(branches)
            }
            _ => node.clone(),
        }
    }
}

