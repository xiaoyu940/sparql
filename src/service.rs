//! SERVICE 联邦查询支持模块
//! 
//! 支持 SPARQL 1.1 SERVICE 关键字，实现跨端点联邦查询

use crate::ir::node::LogicNode;
use crate::ir::expr::Term;
use std::collections::HashMap;

/// SERVICE 端点配置
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ServiceEndpoint {
    /// 端点名称/标识符
    pub name: String,
    /// SPARQL 端点 URL
    pub url: String,
    /// 可选的默认图
    pub default_graph: Option<String>,
    /// 请求超时（秒）
    pub timeout_seconds: u64,
    /// 是否需要认证
    pub requires_auth: bool,
    /// 认证令牌（从环境变量或配置加载）
    pub auth_token: Option<String>,
}

/// SERVICE 查询节点
#[derive(Debug, Clone)]
pub struct ServiceQuery {
    /// 端点标识符（如 <http://example.org/sparql> 或命名服务如 ex:endpoint）
    pub endpoint: String,
    /// 查询变量绑定
    pub bindings: HashMap<String, Term>,
    /// 子查询逻辑计划（在远程端点执行的查询）
    pub inner_plan: Box<LogicNode>,
    /// 是否为 SILENT 模式（错误时返回空结果而非报错）
    pub silent: bool,
}

/// 联邦查询执行器
pub struct FederatedQueryExecutor {
    /// 端点注册表
    endpoints: HashMap<String, ServiceEndpoint>,
    /// 默认超时
    default_timeout: u64,
}

impl FederatedQueryExecutor {
    /// 创建新的联邦查询执行器
    pub fn new() -> Self {
        Self {
            endpoints: HashMap::new(),
            default_timeout: 30,
        }
    }

    /// 注册服务端点
    pub fn register_endpoint(&mut self, endpoint: ServiceEndpoint) {
        self.endpoints.insert(endpoint.name.clone(), endpoint);
    }

    /// 获取端点数量
    pub fn endpoint_count(&self) -> usize {
        self.endpoints.len()
    }

    /// 移除服务端点
    pub fn remove_endpoint(&mut self, name: &str) {
        self.endpoints.remove(name);
    }

    /// 列出所有端点名称
    pub fn list_endpoints(&self) -> Vec<String> {
        self.endpoints.keys().cloned().collect()
    }

    /// 获取指定名称的端点
    pub fn get_endpoint(&self, name: &str) -> Option<ServiceEndpoint> {
        self.endpoints.get(name).cloned()
    }

    /// 执行 SERVICE 查询（异步）
    /// 
    /// # Arguments
    /// * `service_query` - SERVICE 查询节点
    ///
    /// # Returns
    /// 远程查询结果或错误
    #[allow(dead_code)]
    pub async fn execute_service_query(
        &self,
        service_query: &ServiceQuery,
    ) -> Result<ServiceResult, ServiceError> {
        let endpoint = self.resolve_endpoint(&service_query.endpoint)?;
        
        // 构建子查询的 SPARQL 字符串
        let sparql = self.build_service_sparql(service_query)?;
        
        // 发送 HTTP 请求到远程端点
        match self.send_sparql_request(&endpoint, &sparql).await {
            Ok(result) => Ok(result),
            Err(_e) if service_query.silent => {
                // SILENT 模式：返回空结果
                Ok(ServiceResult::empty())
            }
            Err(e) => Err(e),
        }
    }

    /// 解析端点标识符
    fn resolve_endpoint(&self, identifier: &str) -> Result<ServiceEndpoint, ServiceError> {
        // 尝试直接匹配命名端点
        if let Some(endpoint) = self.endpoints.get(identifier) {
            return Ok(endpoint.clone());
        }

        // 处理 IRI 格式的端点（如 <http://example.org/sparql>）
        let url = identifier
            .trim_start_matches('<')
            .trim_end_matches('>')
            .to_string();

        if url.starts_with("http://") || url.starts_with("https://") {
            Ok(ServiceEndpoint {
                name: url.clone(),
                url,
                default_graph: None,
                timeout_seconds: self.default_timeout,
                requires_auth: false,
                auth_token: None,
            })
        } else {
            Err(ServiceError::UnknownEndpoint(identifier.to_string()))
        }
    }

    /// 构建 SERVICE 子查询的 SPARQL
    fn build_service_sparql(&self, query: &ServiceQuery) -> Result<String, ServiceError> {
        // 将 LogicNode 转换为 SPARQL 查询字符串
        // 这里简化处理，实际需要完整的 SPARQL 序列化
        let mut sparql = String::from("SELECT * WHERE {\n");
        
        // 添加变量绑定作为 VALUES 子句
        if !query.bindings.is_empty() {
            sparql.push_str("  VALUES ");
            for (var, term) in &query.bindings {
                sparql.push_str(&format!("?{} {{ {} }}", var, self.term_to_sparql(term)));
            }
            sparql.push_str("\n");
        }
        
        // 序列化内部查询计划
        sparql.push_str(&self.logic_node_to_sparql(&query.inner_plan)?);
        sparql.push_str("\n}");
        
        Ok(sparql)
    }

    /// 将 Term 转换为 SPARQL 格式
    fn term_to_sparql(&self, term: &Term) -> String {
        match term {
            Term::Variable(v) => format!("?{}", v),
            Term::Constant(c) => format!("<{}>", c),
            Term::Literal { value, datatype, language: _ } => {
                if let Some(dt) = datatype {
                    format!("\"{}\"^^{}", value.escape_default(), dt)
                } else {
                    format!("\"{}\"", value.escape_default())
                }
            }
            Term::Column { table, column } => format!("?{}_{}", table.replace('.', "_"), column),
            Term::BlankNode(b) => format!("_:{}", b),
        }
    }

    /// 将 LogicNode 转换为 SPARQL 模式
    fn logic_node_to_sparql(&self, node: &LogicNode) -> Result<String, ServiceError> {
        match node {
            LogicNode::ExtensionalData { table_name: _, column_mapping, .. } => {
                // 表数据映射为三元组模式
                let mut triples = Vec::new();
                for (var, col) in column_mapping {
                    triples.push(format!("?{} <{}> ?{}", var, col, var));
                }
                Ok(triples.join(" .\n  "))
            }
            LogicNode::Join { children, condition: _, .. } => {
                let mut patterns = Vec::new();
                for child in children {
                    patterns.push(self.logic_node_to_sparql(child)?);
                }
                Ok(patterns.join(" .\n  "))
            }
            LogicNode::Filter { expression, child } => {
                let child_sparql = self.logic_node_to_sparql(child)?;
                let filter_expr = self.expr_to_sparql_filter(expression)?;
                Ok(format!("{} FILTER ({})", child_sparql, filter_expr))
            }
            _ => Err(ServiceError::UnsupportedNode(
                format!("Cannot convert {:?} to SPARQL", node)
            ))
        }
    }

    /// 将表达式转换为 SPARQL FILTER
    fn expr_to_sparql_filter(&self, expr: &crate::ir::expr::Expr) -> Result<String, ServiceError> {
        use crate::ir::expr::Expr;
        
        match expr {
            Expr::Compare { left, op, right } => {
                let left_str = self.expr_to_sparql_filter(left)?;
                let right_str = self.expr_to_sparql_filter(right)?;
                let op_str = match op {
                    crate::ir::expr::ComparisonOp::Eq => "=",
                    crate::ir::expr::ComparisonOp::Neq => "!=",
                    crate::ir::expr::ComparisonOp::Lt => "<",
                    crate::ir::expr::ComparisonOp::Lte => "<=",
                    crate::ir::expr::ComparisonOp::Gt => ">",
                    crate::ir::expr::ComparisonOp::Gte => ">=",
                    _ => return Err(ServiceError::UnsupportedExpression(
                        format!("{:?}", op)
                    )),
                };
                Ok(format!("{} {} {}", left_str, op_str, right_str))
            }
            Expr::Term(term) => Ok(self.term_to_sparql(term)),
            _ => Err(ServiceError::UnsupportedExpression(
                format!("{:?}", expr)
            ))
        }
    }

    /// 发送 SPARQL HTTP 请求
    async fn send_sparql_request(
        &self,
        endpoint: &ServiceEndpoint,
        sparql: &str,
    ) -> Result<ServiceResult, ServiceError> {
        use reqwest::{Client, header};
        use std::time::Duration;
        
        // 创建 HTTP 客户端
        let client = Client::builder()
            .timeout(Duration::from_secs(endpoint.timeout_seconds))
            .build()
            .map_err(|e| ServiceError::HttpError(format!("Failed to create HTTP client: {}", e)))?;
        
        // 构建请求
        let mut request = client
            .post(&endpoint.url)
            .header(header::ACCEPT, "application/sparql-results+json")
            .header(header::CONTENT_TYPE, "application/x-www-form-urlencoded")
            .form(&[("query", sparql)]);
        
        // 添加认证头（如果需要）
        if endpoint.requires_auth {
            if let Some(token) = &endpoint.auth_token {
                request = request.bearer_auth(token);
            }
        }
        
        // 添加默认图参数（如果指定）
        if let Some(graph) = &endpoint.default_graph {
            request = request.form(&[("default-graph-uri", graph.as_str())]);
        }
        
        // 发送请求
        let response = request
            .send()
            .await
            .map_err(|e| ServiceError::HttpError(format!("Request failed: {}", e)))?;
        
        // 检查响应状态
        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            return Err(ServiceError::HttpError(
                format!("HTTP {}: {}", status, body)
            ));
        }
        
        // 解析 SPARQL JSON 结果
        let json_results: SparqlJsonResults = response
            .json()
            .await
            .map_err(|e| ServiceError::ParseError(format!("Failed to parse JSON response: {}", e)))?;
        
        // 转换为 ServiceResult
        self.convert_json_to_service_result(json_results)
    }
    
    /// 将 SPARQL JSON 结果转换为 ServiceResult
    fn convert_json_to_service_result(
        &self,
        json_results: SparqlJsonResults,
    ) -> Result<ServiceResult, ServiceError> {
        let mut bindings = Vec::new();
        let columns = json_results.head.vars.clone();
        
        for result in json_results.results.bindings {
            let mut row = HashMap::new();
            for (var, value_obj) in result {
                let term = self.json_value_to_term(value_obj)?;
                row.insert(var, term);
            }
            bindings.push(row);
        }
        
        Ok(ServiceResult { bindings, columns })
    }
    
    /// 将 JSON 值转换为 Term
    fn json_value_to_term(
        &self,
        value_obj: SparqlJsonValue,
    ) -> Result<Term, ServiceError> {
        match value_obj.type_.as_str() {
            "uri" => Ok(Term::Constant(value_obj.value)),
            "literal" => {
                let datatype = value_obj.datatype;
                let language = value_obj.xml_lang;
                Ok(Term::Literal { 
                    value: value_obj.value, 
                    datatype, 
                    language 
                })
            }
            "bnode" => Ok(Term::BlankNode(value_obj.value)),
            _ => Err(ServiceError::ParseError(
                format!("Unknown value type: {}", value_obj.type_)
            ))
        }
    }
}

impl Default for FederatedQueryExecutor {
    fn default() -> Self {
        Self::new()
    }
}

/// SERVICE 查询结果
#[derive(Debug, Clone)]
pub struct ServiceResult {
    pub bindings: Vec<HashMap<String, Term>>,
    pub columns: Vec<String>,
}

impl ServiceResult {
    pub fn empty() -> Self {
        Self {
            bindings: Vec::new(),
            columns: Vec::new(),
        }
    }
}

/// SERVICE 错误类型
#[derive(Debug, Clone)]
pub enum ServiceError {
    UnknownEndpoint(String),
    HttpError(String),
    ParseError(String),
    Timeout(String),
    UnsupportedNode(String),
    UnsupportedExpression(String),
}

impl std::fmt::Display for ServiceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ServiceError::UnknownEndpoint(e) => write!(f, "Unknown endpoint: {}", e),
            ServiceError::HttpError(e) => write!(f, "HTTP error: {}", e),
            ServiceError::ParseError(e) => write!(f, "Parse error: {}", e),
            ServiceError::Timeout(e) => write!(f, "Timeout: {}", e),
            ServiceError::UnsupportedNode(e) => write!(f, "Unsupported node: {}", e),
            ServiceError::UnsupportedExpression(e) => write!(f, "Unsupported expression: {}", e),
        }
    }
}

impl std::error::Error for ServiceError {}

/// SPARQL JSON 查询结果响应结构
#[derive(Debug, Clone, serde::Deserialize)]
pub struct SparqlJsonResults {
    pub head: SparqlJsonHead,
    pub results: SparqlJsonResultsData,
}

/// SPARQL JSON 响应头部
#[derive(Debug, Clone, serde::Deserialize)]
pub struct SparqlJsonHead {
    pub vars: Vec<String>,
}

/// SPARQL JSON 响应结果数据
#[derive(Debug, Clone, serde::Deserialize)]
pub struct SparqlJsonResultsData {
    pub bindings: Vec<HashMap<String, SparqlJsonValue>>,
}

/// SPARQL JSON 值类型
#[derive(Debug, Clone, serde::Deserialize)]
pub struct SparqlJsonValue {
    #[serde(rename = "type")]
    pub type_: String,
    pub value: String,
    #[serde(rename = "xml:lang")]
    pub xml_lang: Option<String>,
    pub datatype: Option<String>,
}

/// 将 LogicNode::Service 转换为远程查询计划
pub fn convert_service_node(
    endpoint: &str,
    inner_plan: LogicNode,
    silent: bool,
) -> Result<ServiceQuery, ServiceError> {
    Ok(ServiceQuery {
        endpoint: endpoint.to_string(),
        bindings: HashMap::new(),
        inner_plan: Box::new(inner_plan),
        silent,
    })
}
