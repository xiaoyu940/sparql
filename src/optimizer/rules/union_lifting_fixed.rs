use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};

pub struct UnionLiftingPass;

impl UnionLiftingPass {
    pub fn new() -> Self {
        Self
    }

    fn lift_union_above_join(&self, node: &mut LogicNode) {
        match node {
            LogicNode::Join { children, condition: _, join_type: _ } => {
                // 检查是否有 Union 子节点
                let mut union_indices = Vec::new();
                for (i, child) in children.iter().enumerate() {
                    if matches!(child, LogicNode::Union(_)) {
                        union_indices.push(i);
                    }
                }
                
                // 如果有 Union 子节点，尝试提升
                if !union_indices.is_empty() && children.len() > 1 {
                    self.perform_union_lifting(node, &union_indices);
                } else {
                    // 递归处理子节点
                    for child in children.iter_mut() {
                        self.lift_union_above_join(child);
                    }
                }
            },
            LogicNode::Union(children) => {
                // 递归处理 Union 的子节点
                for child in children.iter_mut() {
                    self.lift_union_above_join(child);
                }
            },
            _ => {}
        }
    }
    
    fn perform_union_lifting(&self, join_node: &mut LogicNode, union_indices: &[usize]) {
        if let LogicNode::Join { children, condition, join_type } = join_node {
            // 简单的并集提升：将 Union 提升到 Join 之上
            let mut union_children = Vec::new();
            
            for &union_idx in union_indices {
                if let Some(LogicNode::Union(union_sub_children)) = children.get(union_idx) {
                    union_children.extend(union_sub_children.clone());
                }
            }
            
            // 创建新的 Union 节点，其中每个分支都包含原来的 Join
            let mut new_union_branches = Vec::new();
            for union_child in union_children {
                let mut new_join_children = children.clone();
                
                // 替换 Union 节点为具体的 Union 子节点
                for &union_idx in union_indices.iter().rev() {
                    new_join_children[union_idx] = union_child.clone();
                }
                
                new_union_branches.push(LogicNode::Join {
                    children: new_join_children,
                    condition: condition.clone(),
                    join_type: *join_type,
                });
            }
            
            // 用新的 Union 替换原来的 Join
            *join_node = LogicNode::Union(new_union_branches);
        }
    }

    fn merge_similar_unions(&self, node: &mut LogicNode) {
        match node {
            LogicNode::Union(children) => {
                // 简化实现，只递归处理子节点
                for child in children.iter_mut() {
                    self.merge_similar_unions(child);
                }
            },
            _ => {}
        }
    }
}

impl OptimizerPass for UnionLiftingPass {
    fn name(&self) -> &str {
        "UnionLiftingPass"
    }

    fn apply(&self, node: &mut LogicNode, _ctx: &OptimizerContext) {
        // 1. 提升 Union 到 Join 之上
        self.lift_union_above_join(node);
        
        // 2. 合并相似的 Union
        self.merge_similar_unions(node);
    }
}
