use crate::ir::node::LogicNode;
use crate::ir::expr::Expr;

/// 查询计划可视化器
#[derive(Debug, Clone)]
pub struct QueryPlanVisualizer {
    pub output_format: OutputFormat,
    pub show_metadata: bool,
    pub show_statistics: bool,
    pub max_depth: Option<usize>,
    pub node_counter: usize,
}

/// 输出格式
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    Text,
    Dot,
    Json,
    Mermaid,
}

impl QueryPlanVisualizer {
    /// 创建新的 QueryPlanVisualizer 实例
    pub fn new() -> Self {
        Self {
            output_format: OutputFormat::Text,
            show_metadata: true,
            show_statistics: false,
            max_depth: None,
            node_counter: 0,
        }
    }
    
    /// 设置输出格式（链式调用）
    pub fn with_format(mut self, format: OutputFormat) -> Self {
        self.output_format = format;
        self
    }
    
    /// 设置是否显示元数据（链式调用）
    pub fn with_metadata(mut self, show: bool) -> Self {
        self.show_metadata = show;
        self
    }
    
    /// 可视化查询计划
    pub fn visualize(&mut self, node: &LogicNode) -> String {
        self.node_counter = 0;
        match self.output_format {
            OutputFormat::Text => self.visualize_text(node),
            OutputFormat::Dot => self.visualize_dot(node),
            OutputFormat::Json => self.visualize_json(node),
            OutputFormat::Mermaid => self.visualize_mermaid(node),
        }
    }
    
    /// 文本格式可视化
    fn visualize_text(&mut self, node: &LogicNode) -> String {
        let mut output = String::new();
        output.push_str("Query Plan Visualization:\n");
        output.push_str("========================\n\n");
        self.visualize_node_text(node, 0, &mut output);
        output
    }
    
    /// 递归可视化节点（文本格式）
    fn visualize_node_text(&mut self, node: &LogicNode, depth: usize, output: &mut String) {
        // 检查深度限制
        if let Some(max_depth) = self.max_depth {
            if depth >= max_depth {
                return;
            }
        }
        
        let indent = "  ".repeat(depth);
        self.node_counter += 1;
        
        match node {
            LogicNode::Construction { projected_vars, bindings, child } => {
                output.push_str(&format!("{}[{}] Construction (Projection)\n", indent, self.node_counter));
                output.push_str(&format!("{}  Projected Variables: {:?}\n", indent, projected_vars));
                output.push_str(&format!("{}  Bindings: {} mappings\n", indent, bindings.len()));
                if self.show_metadata {
                    output.push_str(&format!("{}  Child:\n", indent));
                    self.visualize_node_text(child, depth + 1, output);
                }
            },
            
            LogicNode::Join { children, condition, join_type } => {
                output.push_str(&format!("{}[{}] Join ({:?})\n", indent, self.node_counter, join_type));
                if let Some(cond) = condition {
                    output.push_str(&format!("{}  Condition: {}\n", indent, self.format_expr(cond)));
                }
                output.push_str(&format!("{}  Children: {}\n", indent, children.len()));
                if self.show_metadata {
                    for (i, child) in children.iter().enumerate() {
                        output.push_str(&format!("{}  Child {}:\n", indent, i + 1));
                        self.visualize_node_text(child, depth + 2, output);
                    }
                }
            },
            
            LogicNode::ExtensionalData { table_name, column_mapping, metadata } => {
                output.push_str(&format!("{}[{}] ExtensionalData (Table Scan)\n", indent, self.node_counter));
                output.push_str(&format!("{}  Table: {}\n", indent, table_name));
                output.push_str(&format!("{}  Columns: {}\n", indent, column_mapping.len()));
                
                if self.show_metadata {
                    output.push_str(&format!("{}  Primary Keys: {:?}\n", indent, metadata.primary_keys));
                    output.push_str(&format!("{}  Foreign Keys: {}\n", indent, metadata.foreign_keys.len()));
                    output.push_str(&format!("{}  Unique Constraints: {}\n", indent, metadata.unique_constraints.len()));
                    output.push_str(&format!("{}  Not Null Columns: {}\n", indent, metadata.not_null_columns.len()));
                }
            },
            
            LogicNode::IntensionalData { predicate, args } => {
                output.push_str(&format!("{}[{}] IntensionalData (Predicate)\n", indent, self.node_counter));
                output.push_str(&format!("{}  Predicate: {}\n", indent, predicate));
                output.push_str(&format!("{}  Arguments: {}\n", indent, args.len()));
            },
            
            LogicNode::Filter { expression, child } => {
                output.push_str(&format!("{}[{}] Filter\n", indent, self.node_counter));
                output.push_str(&format!("{}  Expression: {}\n", indent, self.format_expr(expression)));
                if self.show_metadata {
                    output.push_str(&format!("{}  Child:\n", indent));
                    self.visualize_node_text(child, depth + 1, output);
                }
            },
            
            LogicNode::Union(children) => {
                output.push_str(&format!("{}[{}] Union\n", indent, self.node_counter));
                output.push_str(&format!("{}  Children: {}\n", indent, children.len()));
                if self.show_metadata {
                    for (i, child) in children.iter().enumerate() {
                        output.push_str(&format!("{}  Child {}:\n", indent, i + 1));
                        self.visualize_node_text(child, depth + 2, output);
                    }
                }
            },
            
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                output.push_str(&format!("{}[{}] Aggregation (GROUP BY)\n", indent, self.node_counter));
                output.push_str(&format!("{}  Group By: {:?}\n", indent, group_by));
                output.push_str(&format!("{}  Aggregates: {}\n", indent, aggregates.len()));
                if self.show_metadata {
                    output.push_str(&format!("{}  Child:\n", indent));
                    self.visualize_node_text(child, depth + 1, output);
                }
            },
            
            LogicNode::Limit { limit, offset, .. } => {
                output.push_str(&format!("{}[{}] Limit\n", indent, self.node_counter));
                output.push_str(&format!("{}  Limit: {}, Offset: {:?}\n", indent, limit, offset));
            },
            LogicNode::Values { .. } => {
                output.push_str(&format!("{}[{}] Values\n", indent, self.node_counter));
            },
            LogicNode::Path { .. } => {
                output.push_str(&format!("{}[{}] Path\n", indent, self.node_counter));
            },
            LogicNode::Graph { .. } => {
                output.push_str(&format!("{}[{}] Graph\n", indent, self.node_counter));
            },
            LogicNode::GraphUnion { graph_var, children } => {
                output.push_str(&format!("{}[{}] GraphUnion\n", indent, self.node_counter));
                output.push_str(&format!("{}  Graph Var: {}, Children: {}\n", indent, graph_var, children.len()));
            },
            LogicNode::Service { endpoint, .. } => {
                output.push_str(&format!("{}[{}] SERVICE\n", indent, self.node_counter));
                output.push_str(&format!("{}  Endpoint: {}\n", indent, endpoint));
            },
            LogicNode::SubQuery { .. } => {
                output.push_str(&format!("{}[{}] SubQuery\n", indent, self.node_counter));
            },
            LogicNode::CorrelatedJoin { .. } => {
                output.push_str(&format!("{}[{}] CorrelatedJoin\n", indent, self.node_counter));
            },
            LogicNode::RecursivePath { .. } => {
                output.push_str(&format!("{}[{}] RecursivePath\n", indent, self.node_counter));
            },
        }
    }
    
    /// DOT 格式可视化（Graphviz）
    fn visualize_dot(&mut self, node: &LogicNode) -> String {
        let mut output = String::new();
        output.push_str("digraph QueryPlan {\n");
        output.push_str("  rankdir=TB;\n");
        output.push_str("  node [shape=box, style=filled, fillcolor=lightblue];\n\n");
        
        self.node_counter = 0;
        self.visualize_node_dot(node, &mut output);
        
        output.push_str("}\n");
        output
    }
    
    /// 递归可视化节点（DOT 格式）
    fn visualize_node_dot(&mut self, node: &LogicNode, output: &mut String) {
        let current_id = self.node_counter;
        self.node_counter += 1;
        
        let node_label = match node {
            LogicNode::Construction { projected_vars, .. } => {
                format!("Construction\\nVars: {:?}", projected_vars.len())
            },
            LogicNode::Join { children, join_type, .. } => {
                format!("Join\\nType: {:?}\\nChildren: {}", join_type, children.len())
            },
            LogicNode::ExtensionalData { table_name, .. } => {
                format!("Table Scan\\n{}", table_name)
            },
            LogicNode::IntensionalData { predicate, .. } => {
                format!("Predicate\\n{}", predicate)
            },
            LogicNode::Filter { .. } => {
                "Filter".to_string()
            },
            LogicNode::Union(children) => {
                format!("Union\\nChildren: {}", children.len())
            },
            LogicNode::Aggregation { group_by, .. } => {
                format!("Aggregation\\nGroup By: {:?}", group_by.len())
            },
            LogicNode::Limit { limit, offset, .. } => {
                format!("Limit\\nLimit: {}, Offset: {:?}", limit, offset)
            },
            LogicNode::GraphUnion { graph_var, children } => {
                format!("Graph Union\\nVar: {}\nChildren: {}", graph_var, children.len())
            },
            LogicNode::Values { .. } => {
                "Values".to_string()
            },
            LogicNode::Path { .. } => {
                "Path".to_string()
            },
            LogicNode::Graph { .. } => {
                "Graph".to_string()
            },
            LogicNode::Service { endpoint, .. } => {
                format!("SERVICE\\nEndpoint: {}", endpoint)
            }
            LogicNode::SubQuery { .. } => format!("SubQuery"),
            LogicNode::CorrelatedJoin { .. } => format!("CorrelatedJoin"),
            LogicNode::RecursivePath { .. } => format!("RecursivePath"),
        };
        
        output.push_str(&format!("  node{} [label=\"{}\"];\n", current_id, node_label));
        
        // 添加边到子节点
        match node {
            LogicNode::Construction { child, .. } |
            LogicNode::Filter { child, .. } |
            LogicNode::Aggregation { child, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_dot(child, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
            },
            LogicNode::SubQuery { inner, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_dot(inner.as_ref(), output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
            },
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                let outer_id = self.node_counter;
                self.visualize_node_dot(outer, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, outer_id));
                let inner_id = self.node_counter;
                self.visualize_node_dot(inner, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, inner_id));
            },
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                let base_id = self.node_counter;
                self.visualize_node_dot(base_path, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, base_id));
                let rec_id = self.node_counter;
                self.visualize_node_dot(recursive_path, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, rec_id));
            },
            
            LogicNode::Join { children, .. } |
            LogicNode::Union(children) => {
                let mut child_ids = Vec::new();
                for child in children {
                    let child_id = self.node_counter;
                    self.visualize_node_dot(child, output);
                    child_ids.push(child_id);
                    output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
                }
            },
            
            LogicNode::ExtensionalData { .. } |
            LogicNode::IntensionalData { .. } |
            LogicNode::Limit { .. } |
            LogicNode::Values { .. } |
            LogicNode::Path { .. } |
            LogicNode::Graph { .. } => {
                // 叶子节点，没有子节点
            },
            LogicNode::GraphUnion { children, .. } => {
                let mut child_ids = Vec::new();
                for child in children {
                    let child_id = self.node_counter;
                    self.visualize_node_dot(child, output);
                    child_ids.push(child_id);
                    output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
                }
            },
            LogicNode::Service { inner_plan, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_dot(inner_plan, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
            }
            LogicNode::SubQuery { inner, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_dot(inner, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, child_id));
            }
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                let outer_id = self.node_counter;
                self.visualize_node_dot(outer, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, outer_id));
                let inner_id = self.node_counter;
                self.visualize_node_dot(inner, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, inner_id));
            }
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                let base_id = self.node_counter;
                self.visualize_node_dot(base_path, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, base_id));
                let rec_id = self.node_counter;
                self.visualize_node_dot(recursive_path, output);
                output.push_str(&format!("  node{} -> node{};\n", current_id, rec_id));
            }
        }
    }
    
    /// JSON 格式可视化
    fn visualize_json(&mut self, node: &LogicNode) -> String {
        self.node_counter = 0;
        let json = self.node_to_json(node);
        format!("{}", json)
    }
    
    /// 将节点转换为 JSON
    fn node_to_json(&mut self, node: &LogicNode) -> serde_json::Value {
        self.node_counter += 1;
        
        let mut json_obj = serde_json::Map::new();
        json_obj.insert("id".to_string(), serde_json::Value::Number(self.node_counter.into()));
        
        match node {
            LogicNode::Construction { projected_vars, bindings, child } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Construction".to_string()));
                json_obj.insert("projected_vars".to_string(), serde_json::to_value(projected_vars).unwrap_or(serde_json::Value::Null));
                json_obj.insert("bindings_count".to_string(), serde_json::Value::Number(bindings.len().into()));
                json_obj.insert("child".to_string(), self.node_to_json(child));
            },
            
            LogicNode::Join { children, condition, join_type } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Join".to_string()));
                json_obj.insert("join_type".to_string(), serde_json::Value::String(format!("{:?}", join_type)));
                if let Some(cond) = condition {
                    json_obj.insert("condition".to_string(), serde_json::Value::String(self.format_expr(cond)));
                }
                let children_json: Vec<serde_json::Value> = children.iter()
                    .map(|child| self.node_to_json(child))
                    .collect();
                json_obj.insert("children".to_string(), serde_json::Value::Array(children_json));
            },
            
            LogicNode::ExtensionalData { table_name, column_mapping, metadata } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("ExtensionalData".to_string()));
                json_obj.insert("table_name".to_string(), serde_json::Value::String(table_name.clone()));
                json_obj.insert("columns_count".to_string(), serde_json::Value::Number(column_mapping.len().into()));
                
                if self.show_metadata {
                    let mut metadata_obj = serde_json::Map::new();
                    metadata_obj.insert("primary_keys".to_string(), serde_json::to_value(&metadata.primary_keys).unwrap_or(serde_json::Value::Null));
                    metadata_obj.insert("foreign_keys_count".to_string(), serde_json::Value::Number(metadata.foreign_keys.len().into()));
                    metadata_obj.insert("unique_constraints_count".to_string(), serde_json::Value::Number(metadata.unique_constraints.len().into()));
                    metadata_obj.insert("not_null_columns_count".to_string(), serde_json::Value::Number(metadata.not_null_columns.len().into()));
                    json_obj.insert("metadata".to_string(), serde_json::Value::Object(metadata_obj));
                }
            },
            
            LogicNode::IntensionalData { predicate, args } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("IntensionalData".to_string()));
                json_obj.insert("predicate".to_string(), serde_json::Value::String(predicate.clone()));
                json_obj.insert("args_count".to_string(), serde_json::Value::Number(args.len().into()));
            },
            
            LogicNode::Filter { expression, child } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Filter".to_string()));
                json_obj.insert("expression".to_string(), serde_json::Value::String(self.format_expr(expression)));
                json_obj.insert("child".to_string(), self.node_to_json(child));
            },
            
            LogicNode::Union(children) => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Union".to_string()));
                let children_json: Vec<serde_json::Value> = children.iter()
                    .map(|child| self.node_to_json(child))
                    .collect();
                json_obj.insert("children".to_string(), serde_json::Value::Array(children_json));
            },
            
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Aggregation".to_string()));
                json_obj.insert("group_by".to_string(), serde_json::to_value(group_by).unwrap_or(serde_json::Value::Null));
                json_obj.insert("aggregates_count".to_string(), serde_json::Value::Number(aggregates.len().into()));
                json_obj.insert("child".to_string(), self.node_to_json(child));
            },
            
            LogicNode::Limit { limit, offset, child, .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Limit".to_string()));
                json_obj.insert("limit".to_string(), serde_json::Value::Number((*limit).into()));
                json_obj.insert("offset".to_string(), serde_json::to_value(offset).unwrap_or(serde_json::Value::Null));
                json_obj.insert("child".to_string(), self.node_to_json(child));
            },
            LogicNode::GraphUnion { graph_var, children, .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("GraphUnion".to_string()));
                json_obj.insert("graph_var".to_string(), serde_json::Value::String(graph_var.clone()));
                let children_json: Vec<serde_json::Value> = children.iter()
                    .map(|child| self.node_to_json(child))
                    .collect();
                json_obj.insert("children".to_string(), serde_json::Value::Array(children_json));
            },
            LogicNode::Values { .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Values".to_string()));
            },
            LogicNode::Path { .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Path".to_string()));
            },
            LogicNode::Graph { .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Graph".to_string()));
            },
            LogicNode::Service { endpoint, inner_plan, .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("Service".to_string()));
                json_obj.insert("endpoint".to_string(), serde_json::Value::String(endpoint.clone()));
                json_obj.insert("inner_plan".to_string(), self.node_to_json(inner_plan));
            }
            LogicNode::SubQuery { inner, correlated_vars } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("SubQuery".to_string()));
                json_obj.insert("inner".to_string(), self.node_to_json(inner));
                json_obj.insert("correlated_vars".to_string(), serde_json::to_value(correlated_vars).unwrap_or(serde_json::Value::Null));
            }
            LogicNode::CorrelatedJoin { outer, inner, condition } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("CorrelatedJoin".to_string()));
                json_obj.insert("outer".to_string(), self.node_to_json(outer));
                json_obj.insert("inner".to_string(), self.node_to_json(inner));
                json_obj.insert("condition".to_string(), serde_json::to_value(condition).unwrap_or(serde_json::Value::Null));
            }
            LogicNode::RecursivePath { base_path, recursive_path, min_depth, max_depth, .. } => {
                json_obj.insert("type".to_string(), serde_json::Value::String("RecursivePath".to_string()));
                json_obj.insert("base_path".to_string(), self.node_to_json(base_path));
                json_obj.insert("recursive_path".to_string(), self.node_to_json(recursive_path));
                json_obj.insert("min_depth".to_string(), serde_json::Value::Number((*min_depth).into()));
                json_obj.insert("max_depth".to_string(), serde_json::Value::Number((*max_depth).into()));
            }
        }
        
        serde_json::Value::Object(json_obj)
    }
    
    /// Mermaid 格式可视化
    fn visualize_mermaid(&mut self, node: &LogicNode) -> String {
        let mut output = String::new();
        output.push_str("graph TD\n");
        output.push_str("    %% Query Plan Visualization\n\n");
        
        self.node_counter = 0;
        self.visualize_node_mermaid(node, &mut output);
        
        output
    }
    
    /// 递归可视化节点（Mermaid 格式）
    fn visualize_node_mermaid(&mut self, node: &LogicNode, output: &mut String) {
        let current_id = self.node_counter;
        self.node_counter += 1;
        
        let node_label = match node {
            LogicNode::Construction { projected_vars, .. } => {
                format!("Construction<br/>Vars: {}", projected_vars.len())
            },
            LogicNode::Join { children, join_type, .. } => {
                format!("Join<br/>Type: {:?}<br/>Children: {}", join_type, children.len())
            },
            LogicNode::ExtensionalData { table_name, .. } => {
                format!("Table Scan<br/>{}", table_name)
            },
            LogicNode::IntensionalData { predicate, .. } => {
                format!("Predicate<br/>{}", predicate)
            },
            LogicNode::Filter { .. } => {
                "Filter".to_string()
            },
            LogicNode::Union(children) => {
                format!("Union<br/>Children: {}", children.len())
            },
            LogicNode::Aggregation { group_by, .. } => {
                format!("Aggregation<br/>Group By: {}", group_by.len())
            },
            LogicNode::Limit { limit, offset, .. } => {
                format!("Limit<br/>Limit: {}, Offset: {:?}", limit, offset)
            },
            LogicNode::GraphUnion { graph_var, children } => {
                format!("Graph Union<br/>Var: {}<br/>Children: {}", graph_var, children.len())
            },
            LogicNode::Values { .. } => {
                "Values".to_string()
            },
            LogicNode::Path { .. } => {
                "Path".to_string()
            },
            LogicNode::Graph { .. } => {
                "Graph".to_string()
            },
            LogicNode::Service { endpoint, .. } => {
                format!("SERVICE<br/>Endpoint: {}", endpoint)
            }
            LogicNode::SubQuery { .. } => "SubQuery".to_string(),
            LogicNode::CorrelatedJoin { .. } => "CorrelatedJoin".to_string(),
            LogicNode::RecursivePath { .. } => "RecursivePath".to_string(),
        };
        
        output.push_str(&format!("    A{}[\"{}\"]\n", current_id, node_label));
        
        // 添加边到子节点
        match node {
            LogicNode::Construction { child, .. } |
            LogicNode::Filter { child, .. } |
            LogicNode::Aggregation { child, .. } |
            LogicNode::Limit { child, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_mermaid(child, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
            },
            LogicNode::SubQuery { inner, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_mermaid(inner, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
            },
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                let outer_id = self.node_counter;
                self.visualize_node_dot(outer, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, outer_id));
                let inner_id = self.node_counter;
                self.visualize_node_dot(inner, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, inner_id));
            },
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                let base_id = self.node_counter;
                self.visualize_node_dot(base_path, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, base_id));
                let rec_id = self.node_counter;
                self.visualize_node_dot(recursive_path, output);
                output.push_str(&format!("  node{} -> node{};
", current_id, rec_id));
            },
            
            LogicNode::Join { children, .. } |
            LogicNode::Union(children) => {
                for child in children {
                    let child_id = self.node_counter;
                    self.visualize_node_mermaid(child, output);
                    output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
                }
            },
            
            LogicNode::ExtensionalData { .. } |
            LogicNode::IntensionalData { .. } |
            LogicNode::Values { .. } |
            LogicNode::Path { .. } |
            LogicNode::Graph { .. } => {
                // 叶子节点，没有子节点
            },
            LogicNode::GraphUnion { children, .. } => {
                for child in children {
                    let child_id = self.node_counter;
                    self.visualize_node_mermaid(child, output);
                    output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
                }
            },
            LogicNode::Service { inner_plan, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_mermaid(inner_plan, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
            }
            LogicNode::SubQuery { inner, .. } => {
                let child_id = self.node_counter;
                self.visualize_node_mermaid(inner, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, child_id));
            }
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                let outer_id = self.node_counter;
                self.visualize_node_mermaid(outer, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, outer_id));
                let inner_id = self.node_counter;
                self.visualize_node_mermaid(inner, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, inner_id));
            }
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                let base_id = self.node_counter;
                self.visualize_node_mermaid(base_path, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, base_id));
                let rec_id = self.node_counter;
                self.visualize_node_mermaid(recursive_path, output);
                output.push_str(&format!("    A{} --> A{}\n", current_id, rec_id));
            }
        }
    }
    
    /// 格式化表达式
    fn format_expr(&self, expr: &Expr) -> String {
        match expr {
            Expr::Term(term) => format!("{:?}", term),
            Expr::Function { name, args } => {
                let args_str: Vec<String> = args.iter().map(|arg| self.format_expr(arg)).collect();
                format!("{}({})", name, args_str.join(", "))
            },
            Expr::Logical { op, args } => {
                let args_str: Vec<String> = args.iter().map(|arg| self.format_expr(arg)).collect();
                format!("{:?}({})", op, args_str.join(", "))
            },
            Expr::Compare { left, right, op } => {
                format!("{} {:?} {}", self.format_expr(left), op, self.format_expr(right))
            },
            Expr::Arithmetic { left, right, op } => {
                format!("{} {:?} {}", self.format_expr(left), op, self.format_expr(right))
            },
            Expr::Exists { patterns, .. } => {
                format!("EXISTS ({} patterns)", patterns.len())
            },
            Expr::NotExists { patterns, .. } => {
                format!("NOT EXISTS ({} patterns)", patterns.len())
            },
        }
    }
    
    /// 设置输出格式
    pub fn set_output_format(&mut self, format: OutputFormat) {
        self.output_format = format;
    }
    
    /// 设置是否显示元数据
    pub fn set_show_metadata(&mut self, show: bool) {
        self.show_metadata = show;
    }
    
    /// 设置最大深度
    pub fn set_max_depth(&mut self, depth: Option<usize>) {
        self.max_depth = depth;
    }
    
    /// 获取节点计数
    pub fn get_node_count(&self) -> usize {
        self.node_counter
    }
}

impl Default for QueryPlanVisualizer {
    fn default() -> Self {
        Self::new()
    }
}

/// 查询计划分析器
#[derive(Debug, Clone)]
pub struct QueryPlanAnalyzer {
    pub node_count: usize,
    pub max_depth: usize,
    pub join_count: usize,
    pub filter_count: usize,
    pub aggregation_count: usize,
    pub union_count: usize,
    pub table_scan_count: usize,
}

impl QueryPlanAnalyzer {
    pub fn new() -> Self {
        Self {
            node_count: 0,
            max_depth: 0,
            join_count: 0,
            filter_count: 0,
            aggregation_count: 0,
            union_count: 0,
            table_scan_count: 0,
        }
    }
    
    /// 分析查询计划
    pub fn analyze(&mut self, node: &LogicNode) {
        self.node_count = 0;
        self.max_depth = 0;
        self.join_count = 0;
        self.filter_count = 0;
        self.aggregation_count = 0;
        self.union_count = 0;
        self.table_scan_count = 0;
        
        self.analyze_node(node, 0);
    }
    
    /// 递归分析节点
    fn analyze_node(&mut self, node: &LogicNode, depth: usize) {
        self.node_count += 1;
        self.max_depth = self.max_depth.max(depth);
        
        match node {
            LogicNode::Join { children, .. } => {
                self.join_count += 1;
                for child in children {
                    self.analyze_node(child, depth + 1);
                }
            },
            LogicNode::Filter { child, .. } => {
                self.filter_count += 1;
                self.analyze_node(child, depth + 1);
            },
            LogicNode::Aggregation { child, .. } => {
                self.aggregation_count += 1;
                self.analyze_node(child, depth + 1);
            },
            LogicNode::Union(children) => {
                self.union_count += 1;
                for child in children {
                    self.analyze_node(child, depth + 1);
                }
            },
            LogicNode::Construction { child, .. } => {
                self.analyze_node(child, depth + 1);
            },
            LogicNode::ExtensionalData { .. } => {
                self.table_scan_count += 1;
            },
            LogicNode::IntensionalData { .. } => {
                // 叶子节点
            },
            LogicNode::Limit { child, .. } => {
                self.analyze_node(child, depth + 1);
            },
            LogicNode::Values { .. } => {
                // 叶子节点
            },
            LogicNode::Path { .. } => {
                // 叶子节点
            },
            LogicNode::Graph { .. } => {
                // 叶子节点
            },
            LogicNode::GraphUnion { children, .. } => {
                for child in children {
                    self.analyze_node(child, depth + 1);
                }
            },
            LogicNode::Service { inner_plan, .. } => {
                self.analyze_node(inner_plan, depth + 1);
            },
            LogicNode::SubQuery { inner, .. } => {
                self.analyze_node(inner, depth + 1);
            },
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                self.analyze_node(outer, depth + 1);
                self.analyze_node(inner, depth + 1);
            },
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                self.analyze_node(base_path, depth + 1);
                self.analyze_node(recursive_path, depth + 1);
            },
        }
    }
    
    /// 生成分析报告
    pub fn generate_report(&self) -> String {
        format!(
            "Query Plan Analysis Report:\n\
             ==========================\n\
             Total Nodes: {}\n\
             Max Depth: {}\n\
             Joins: {}\n\
             Filters: {}\n\
             Aggregations: {}\n\
             Unions: {}\n\
             Table Scans: {}\n\
             ==========================\n\
             Complexity: {}",
            self.node_count,
            self.max_depth,
            self.join_count,
            self.filter_count,
            self.aggregation_count,
            self.union_count,
            self.table_scan_count,
            self.calculate_complexity()
        )
    }
    
    /// 计算复杂度分数
    pub fn calculate_complexity(&self) -> String {
        let score = self.join_count * 3 + 
                   self.aggregation_count * 2 + 
                   self.union_count * 2 + 
                   self.filter_count + 
                   self.max_depth;
        
        if score < 10 {
            "Low".to_string()
        } else if score < 25 {
            "Medium".to_string()
        } else if score < 50 {
            "High".to_string()
        } else {
            "Very High".to_string()
        }
    }
}

impl Default for QueryPlanAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}
