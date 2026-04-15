use crate::ir::node::{LogicNode, JoinType};
use crate::optimizer::OptimizerContext;
use crate::optimizer::dp_size::dp_size_optimal_order;

#[derive(Debug, Default)]
pub struct JoinReordering;

impl JoinReordering {
    pub fn apply(node: LogicNode, ctx: &OptimizerContext) -> LogicNode {
        match node {
            LogicNode::Join {
                children,
                condition,
                join_type,
            } => {
                // Recursively optimize children
                let opt_children: Vec<LogicNode> = children.into_iter()
                    .map(|child| Self::apply(child, ctx))
                    .collect();

                // Apply DPSize to the children if inner join
                if matches!(join_type, JoinType::Inner) && opt_children.len() > 1 {
                    dp_size_optimal_order(opt_children, condition, &ctx.stats)
                } else {
                    LogicNode::Join {
                        children: opt_children,
                        condition,
                        join_type,
                    }
                }
            }
            LogicNode::Filter { expression, child } => {
                LogicNode::Filter {
                    expression,
                    child: Box::new(Self::apply(*child, ctx)),
                }
            }
            LogicNode::Union(children) => LogicNode::Union(
                children.into_iter().map(|c| Self::apply(c, ctx)).collect()
            ),
            LogicNode::GraphUnion { children, graph_var } => LogicNode::GraphUnion {
                children: children.into_iter().map(|c| Self::apply(c, ctx)).collect(),
                graph_var,
            },
            LogicNode::Aggregation { group_by, aggregates, child, .. } => LogicNode::Aggregation { having: None,
                group_by,
                aggregates,
                child: Box::new(Self::apply(*child, ctx)),
            },
            LogicNode::Limit { limit, offset, order_by, child } => LogicNode::Limit {
                limit, 
                offset, 
                order_by,
                child: Box::new(Self::apply(*child, ctx))
            },
            LogicNode::Construction { projected_vars, bindings, child } => LogicNode::Construction {
                projected_vars, 
                bindings,
                child: Box::new(Self::apply(*child, ctx))
            },
            LogicNode::Graph { graph_name, is_named_graph, child } => LogicNode::Graph {
                graph_name, 
                is_named_graph,
                child: Box::new(Self::apply(*child, ctx))
            },
            // Service nodes are passed through — they will be materialized later.
            LogicNode::Service { endpoint, output_vars, inner_plan, silent } =>
                LogicNode::Service {
                    endpoint,
                    output_vars,
                    inner_plan: Box::new(Self::apply(*inner_plan, ctx)),
                    silent,
                },
            other => other,
        }
    }
}
