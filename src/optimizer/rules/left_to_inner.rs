use crate::ir::node::{LogicNode, JoinType};
use crate::optimizer::{OptimizerPass, OptimizerContext};

/// 左连接转内连接优化器
///
/// 将 LEFT JOIN 转换为 INNER JOIN 的优化规则。
/// 转换条件：当右表的所有被投影或连接使用的列在元数据中都标记为 NOT NULL 时，
/// 可以安全地将 LEFT JOIN 转换为 INNER JOIN，从而可能获得更好的查询性能。
///
/// # 算法逻辑
/// 1. 后序遍历 Join 节点的子节点
/// 2. 对于 Left Join，检查右子节点（children[1]）的列映射
/// 3. 验证所有涉及的列都在 `metadata.not_null_columns` 中
/// 4. 如果满足条件，将 join_type 从 Left 改为 Inner
///
/// # Safety
/// 此转换仅在右表列的 NOT NULL 约束可验证时才执行。
/// 如果右表可能产生 NULL 值，转换将导致结果集变化，因此必须保守处理。
pub struct LeftToInnerJoinPass;

impl LeftToInnerJoinPass {
    /// 创建新的 LeftToInnerJoinPass 实例
    ///
    /// # Example
    /// ```
    /// let pass = LeftToInnerJoinPass::new();
    /// pass.apply(&mut plan, &ctx);
    /// ```
    pub fn new() -> Self {
        Self
    }
}

impl OptimizerPass for LeftToInnerJoinPass {
    /// 返回优化器名称
    fn name(&self) -> &str {
        "LeftToInnerJoinPass"
    }

    /// 应用左连接转内连接优化
    ///
    /// # Arguments
    /// * `node` - 当前处理的逻辑节点（会被修改）
    /// * `ctx` - 优化器上下文
    ///
    /// # Algorithm
    /// 使用后序遍历递归处理子节点，然后检查当前节点：
    /// - 如果是 Join 节点且类型为 Left，并且子节点数 >= 2
    /// - 检查右子节点的列映射中所有列都在 metadata.not_null_columns 中
    /// - 满足条件则将 join_type 改为 Inner
    ///
    /// # Panics
    /// 不会 panic，但可能静默跳过不满足条件的节点
    fn apply(&self, node: &mut LogicNode, ctx: &OptimizerContext) {
        match node {
            LogicNode::Join { join_type, children, .. } => {
                // 后序遍历：先递归处理子节点
                for child in children.iter_mut() {
                    self.apply(child, ctx);
                }

                if *join_type == JoinType::Left && children.len() >= 2 {
                    // 检查是否可以安全转换为 Inner Join
                    // 条件：右表（children[1]）的所有列都在 metadata.not_null_columns 中
                    
                    let mut all_not_null = true;
                    
                    if let LogicNode::ExtensionalData { column_mapping, metadata, .. } = &children[1] {
                        for (_var, col) in column_mapping {
                            if !metadata.not_null_columns.contains(col) {
                                all_not_null = false;
                                break;
                            }
                        }
                    } else {
                        // 如果右子节点不是 ExtensionalData，无法验证 NOT NULL，保守处理
                        all_not_null = false;
                    }

                    // 如果所有列都 NOT NULL，安全转换为 Inner Join
                    if all_not_null {
                        *join_type = JoinType::Inner;
                    }
                }
            }
            // 递归处理其他节点类型
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
