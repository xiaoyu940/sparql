//! SPARQL 函数注册系统
//!
//! 支持 SPARQL 1.1 标准函数和自定义函数的注册与管理
//! 提供 SQL 翻译能力，将 SPARQL 函数映射到对应的 SQL 实现

use crate::ir::expr::{Expr, Term};
use std::collections::HashMap;

/// 函数处理结果类型
pub type FunctionResult = Result<Expr, FunctionError>;

/// 函数错误类型
#[derive(Debug, Clone)]
pub enum FunctionError {
    UnknownFunction(String),
    InvalidArgumentCount { expected: usize, actual: usize },
    TypeError { expected: String, actual: String },
    EvaluationError(String),
}

impl std::fmt::Display for FunctionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FunctionError::UnknownFunction(name) => write!(f, "Unknown function: {}", name),
            FunctionError::InvalidArgumentCount { expected, actual } => {
                write!(f, "Invalid argument count: expected {}, got {}", expected, actual)
            }
            FunctionError::TypeError { expected, actual } => {
                write!(f, "Type error: expected {}, got {}", expected, actual)
            }
            FunctionError::EvaluationError(msg) => write!(f, "Evaluation error: {}", msg),
        }
    }
}

impl std::error::Error for FunctionError {}

/// 函数元数据
#[derive(Debug, Clone)]
pub struct FunctionMetadata {
    pub name: String,
    pub namespace: Option<String>,
    pub min_args: usize,
    pub max_args: usize,
    pub description: String,
    pub category: FunctionCategory,
}

/// 函数分类
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FunctionCategory {
    String,
    Numeric,
    DateTime,
    Boolean,
    Hash,
    Cast,
    Aggregation,
    Custom,
}

/// 函数处理器 trait
pub trait FunctionHandler: Send + Sync {
    /// 评估函数
    fn evaluate(&self, args: &[Expr]) -> FunctionResult;
    
    /// 获取函数元数据
    fn metadata(&self) -> &FunctionMetadata;
    
    /// 生成 SQL 表达式
    fn to_sql(&self, args: &[Expr], sql_generator: &dyn SqlExpressionGenerator) -> Result<String, FunctionError>;
}

/// SQL 表达式生成器 trait
pub trait SqlExpressionGenerator {
    fn generate_expr(&self, expr: &Expr) -> String;
}

/// 内置函数处理器
pub struct BuiltinFunctionHandler {
    metadata: FunctionMetadata,
    evaluator: Box<dyn Fn(&[Expr]) -> FunctionResult + Send + Sync>,
    sql_generator: Box<dyn Fn(&[Expr], &dyn SqlExpressionGenerator) -> Result<String, FunctionError> + Send + Sync>,
}

impl BuiltinFunctionHandler {
    pub fn new<F, G>(
        metadata: FunctionMetadata,
        evaluator: F,
        sql_generator: G,
    ) -> Self
    where
        F: Fn(&[Expr]) -> FunctionResult + Send + Sync + 'static,
        G: Fn(&[Expr], &dyn SqlExpressionGenerator) -> Result<String, FunctionError> + Send + Sync + 'static,
    {
        Self {
            metadata,
            evaluator: Box::new(evaluator),
            sql_generator: Box::new(sql_generator),
        }
    }
}

impl FunctionHandler for BuiltinFunctionHandler {
    fn evaluate(&self, args: &[Expr]) -> FunctionResult {
        (self.evaluator)(args)
    }
    
    fn metadata(&self) -> &FunctionMetadata {
        &self.metadata
    }
    
    fn to_sql(&self, args: &[Expr], sql_generator: &dyn SqlExpressionGenerator) -> Result<String, FunctionError> {
        (self.sql_generator)(args, sql_generator)
    }
}

/// 函数注册表
pub struct FunctionRegistry {
    functions: HashMap<String, Box<dyn FunctionHandler>>,
    #[allow(dead_code)]
    namespaces: HashMap<String, String>,
}

impl FunctionRegistry {
    /// 创建新的函数注册表
    pub fn new() -> Self {
        let mut registry = Self {
            functions: HashMap::new(),
            namespaces: HashMap::new(),
        };
        registry.register_builtin_functions();
        registry
    }
    
    /// 注册标准 SPARQL 函数
    fn register_builtin_functions(&mut self) {
        // 字符串函数
        self.register_string_functions();
        
        // 数值函数
        self.register_numeric_functions();
        
        // 日期时间函数
        self.register_datetime_functions();
        
        // 布尔函数
        self.register_boolean_functions();
        
        // 哈希函数
        self.register_hash_functions();
        
        // 类型转换函数
        self.register_cast_functions();
        
        // GeoSPARQL 函数
        self.register_geosparql_functions();
    }
    
    /// 注册 GeoSPARQL 函数
    fn register_geosparql_functions(&mut self) {
        // POINT -> ST_Point
        self.register_builtin(
            "POINT",
            FunctionMetadata {
                name: "POINT".to_string(),
                namespace: None,
                min_args: 2,
                max_args: 2,
                description: "Create a point from coordinates".to_string(),
                category: FunctionCategory::Custom,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                Ok(format!(
                    "ST_SetSRID(ST_Point({}, {}), 4326)",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );

        // geof:distance
        self.register_builtin(
            "geof:distance",
            FunctionMetadata {
                name: "geof:distance".to_string(),
                namespace: Some("http://www.opengis.net/def/function/geosparql/".to_string()),
                min_args: 2,
                max_args: 2,
                description: "Calculate distance between two geometries".to_string(),
                category: FunctionCategory::Custom,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                Ok(format!(
                    "ST_Distance({}, {})",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );
        
        // Also register without prefix for convenience
        self.register_builtin(
            "DISTANCE",
            FunctionMetadata {
                name: "DISTANCE".to_string(),
                namespace: None,
                min_args: 2,
                max_args: 2,
                description: "Calculate distance between two geometries".to_string(),
                category: FunctionCategory::Custom,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                Ok(format!(
                    "ST_Distance({}, {})",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );

        // geof:intersects
        self.register_builtin(
            "geof:intersects",
            FunctionMetadata {
                name: "geof:intersects".to_string(),
                namespace: Some("http://www.opengis.net/def/function/geosparql/".to_string()),
                min_args: 2,
                max_args: 2,
                description: "Check if two geometries intersect".to_string(),
                category: FunctionCategory::Custom,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                Ok(format!(
                    "ST_Intersects({}, {})",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );
        
        // geof:buffer
        self.register_builtin(
            "geof:buffer",
            FunctionMetadata {
                name: "geof:buffer".to_string(),
                namespace: Some("http://www.opengis.net/def/function/geosparql/".to_string()),
                min_args: 2,
                max_args: 2,
                description: "Calculate buffer around geometry".to_string(),
                category: FunctionCategory::Custom,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                Ok(format!(
                    "ST_Buffer({}, {})",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );
    }
    
    /// 注册字符串函数
    fn register_string_functions(&mut self) {
        // STR - 将值转换为字符串
        self.register_builtin(
            "STR",
            FunctionMetadata {
                name: "STR".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Convert a value to a string".to_string(),
                category: FunctionCategory::String,
            },
            |args| {
                // 简化实现：返回第一个参数
                Ok(args[0].clone())
            },
            |args, gen| {
                Ok(format!("CAST({} AS TEXT)", gen.generate_expr(&args[0])))
            },
        );
        
        // CONCAT - 字符串连接
        self.register_builtin(
            "CONCAT",
            FunctionMetadata {
                name: "CONCAT".to_string(),
                namespace: None,
                min_args: 2,
                max_args: usize::MAX,
                description: "Concatenate strings".to_string(),
                category: FunctionCategory::String,
            },
            |args| {
                if args.len() < 2 {
                    return Err(FunctionError::InvalidArgumentCount {
                        expected: 2,
                        actual: args.len(),
                    });
                }
                Ok(Expr::Function {
                    name: "CONCAT".to_string(),
                    args: args.to_vec(),
                })
            },
            |args, gen| {
                let parts: Vec<String> = args.iter()
                    .map(|a| gen.generate_expr(a))
                    .collect();
                Ok(format!("CONCAT({})", parts.join(", ")))
            },
        );
        
        // LCASE / UCASE - 大小写转换
        self.register_builtin(
            "LCASE",
            FunctionMetadata {
                name: "LCASE".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "Convert to lowercase".to_string(),
                category: FunctionCategory::String,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("LOWER({})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "UCASE",
            FunctionMetadata {
                name: "UCASE".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "Convert to uppercase".to_string(),
                category: FunctionCategory::String,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("UPPER({})", gen.generate_expr(&args[0]))),
        );
        
        // CONTAINS / STRSTARTS / STRENDS
        self.register_builtin(
            "CONTAINS",
            FunctionMetadata {
                name: "CONTAINS".to_string(),
                namespace: None,
                min_args: 2,
                max_args: 2,
                description: "Check if string contains substring".to_string(),
                category: FunctionCategory::String,
            },
            |_args| {
                Ok(Expr::Term(Term::Variable("contains_result".to_string())))
            },
            |args, gen| {
                Ok(format!(
                    "({} LIKE '%' || {} || '%')",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1])
                ))
            },
        );
        
        // STRLEN - 字符串长度
        self.register_builtin(
            "STRLEN",
            FunctionMetadata {
                name: "STRLEN".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "Get string length".to_string(),
                category: FunctionCategory::String,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("LENGTH({})", gen.generate_expr(&args[0]))),
        );
        
        // SUBSTR - 子字符串
        self.register_builtin(
            "SUBSTR",
            FunctionMetadata {
                name: "SUBSTR".to_string(),
                namespace: None,
                min_args: 2,
                max_args: 3,
                description: "Extract substring".to_string(),
                category: FunctionCategory::String,
            },
            |args| Ok(args[0].clone()),
            |args, gen| {
                if args.len() == 2 {
                    Ok(format!(
                        "SUBSTRING({} FROM CAST({} AS INTEGER))",
                        gen.generate_expr(&args[0]),
                        gen.generate_expr(&args[1])
                    ))
                } else {
                    Ok(format!(
                        "SUBSTRING({} FROM CAST({} AS INTEGER) FOR CAST({} AS INTEGER))",
                        gen.generate_expr(&args[0]),
                        gen.generate_expr(&args[1]),
                        gen.generate_expr(&args[2])
                    ))
                }
            },
        );
    }
    
    /// 注册数值函数
    fn register_numeric_functions(&mut self) {
        // ABS - 绝对值
        self.register_builtin(
            "ABS",
            FunctionMetadata {
                name: "ABS".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Absolute value".to_string(),
                category: FunctionCategory::Numeric,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("ABS({})", gen.generate_expr(&args[0]))),
        );
        
        // ROUND / CEIL / FLOOR
        self.register_builtin(
            "ROUND",
            FunctionMetadata {
                name: "ROUND".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Round to nearest integer".to_string(),
                category: FunctionCategory::Numeric,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("ROUND({})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "CEIL",
            FunctionMetadata {
                name: "CEIL".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Round up to nearest integer".to_string(),
                category: FunctionCategory::Numeric,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("CEILING({})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "FLOOR",
            FunctionMetadata {
                name: "FLOOR".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Round down to nearest integer".to_string(),
                category: FunctionCategory::Numeric,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("FLOOR({})", gen.generate_expr(&args[0]))),
        );
        
        // RAND - 随机数
        self.register_builtin(
            "RAND",
            FunctionMetadata {
                name: "RAND".to_string(),
                namespace: None,
                min_args: 0,
                max_args: 0,
                description: "Generate random number".to_string(),
                category: FunctionCategory::Numeric,
            },
            |_args| Ok(Expr::Term(Term::Variable("rand".to_string()))),
            |_args, _gen| Ok("RANDOM()".to_string()),
        );
    }
    
    /// 注册日期时间函数
    fn register_datetime_functions(&mut self) {
        // NOW - 当前时间
        self.register_builtin(
            "NOW",
            FunctionMetadata {
                name: "NOW".to_string(),
                namespace: None,
                min_args: 0,
                max_args: 0,
                description: "Current date and time".to_string(),
                category: FunctionCategory::DateTime,
            },
            |_args| Ok(Expr::Term(Term::Variable("now".to_string()))),
            |_args, _gen| Ok("CURRENT_TIMESTAMP".to_string()),
        );
        
        // YEAR / MONTH / DAY / HOURS / MINUTES / SECONDS
        self.register_builtin(
            "YEAR",
            FunctionMetadata {
                name: "YEAR".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Extract year from date".to_string(),
                category: FunctionCategory::DateTime,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("EXTRACT(YEAR FROM {})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "MONTH",
            FunctionMetadata {
                name: "MONTH".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Extract month from date".to_string(),
                category: FunctionCategory::DateTime,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("EXTRACT(MONTH FROM {})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "DAY",
            FunctionMetadata {
                name: "DAY".to_string(),
                namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                min_args: 1,
                max_args: 1,
                description: "Extract day from date".to_string(),
                category: FunctionCategory::DateTime,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("EXTRACT(DAY FROM {})", gen.generate_expr(&args[0]))),
        );
    }
    
    /// 注册布尔函数
    fn register_boolean_functions(&mut self) {
        // BOUND - 检查变量是否绑定
        self.register_builtin(
            "BOUND",
            FunctionMetadata {
                name: "BOUND".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "Check if variable is bound".to_string(),
                category: FunctionCategory::Boolean,
            },
            |_args| Ok(Expr::Term(Term::Variable("bound".to_string()))),
            |args, gen| Ok(format!("({} IS NOT NULL)", gen.generate_expr(&args[0]))),
        );
        
        // COALESCE - 返回第一个非空值
        self.register_builtin(
            "COALESCE",
            FunctionMetadata {
                name: "COALESCE".to_string(),
                namespace: None,
                min_args: 1,
                max_args: usize::MAX,
                description: "Return first non-null value".to_string(),
                category: FunctionCategory::Boolean,
            },
            |args| {
                if args.is_empty() {
                    return Err(FunctionError::InvalidArgumentCount {
                        expected: 1,
                        actual: 0,
                    });
                }
                Ok(args[0].clone())
            },
            |args, gen| {
                let parts: Vec<String> = args.iter()
                    .map(|a| gen.generate_expr(a))
                    .collect();
                Ok(format!("COALESCE({})", parts.join(", ")))
            },
        );
        
        // IF - 条件表达式
        self.register_builtin(
            "IF",
            FunctionMetadata {
                name: "IF".to_string(),
                namespace: None,
                min_args: 3,
                max_args: 3,
                description: "Conditional expression".to_string(),
                category: FunctionCategory::Boolean,
            },
            |args| Ok(args[1].clone()),
            |args, gen| {
                Ok(format!(
                    "CASE WHEN {} THEN {} ELSE {} END",
                    gen.generate_expr(&args[0]),
                    gen.generate_expr(&args[1]),
                    gen.generate_expr(&args[2])
                ))
            },
        );
    }
    
    /// 注册哈希函数
    fn register_hash_functions(&mut self) {
        // MD5
        self.register_builtin(
            "MD5",
            FunctionMetadata {
                name: "MD5".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "MD5 hash".to_string(),
                category: FunctionCategory::Hash,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("MD5({})", gen.generate_expr(&args[0]))),
        );
        
        // SHA1 / SHA256 / SHA384 / SHA512
        self.register_builtin(
            "SHA1",
            FunctionMetadata {
                name: "SHA1".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "SHA1 hash".to_string(),
                category: FunctionCategory::Hash,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("SHA1({})", gen.generate_expr(&args[0]))),
        );
        
        self.register_builtin(
            "SHA256",
            FunctionMetadata {
                name: "SHA256".to_string(),
                namespace: None,
                min_args: 1,
                max_args: 1,
                description: "SHA256 hash".to_string(),
                category: FunctionCategory::Hash,
            },
            |args| Ok(args[0].clone()),
            |args, gen| Ok(format!("SHA256({})", gen.generate_expr(&args[0]))),
        );
    }
    
    /// 注册类型转换函数
    fn register_cast_functions(&mut self) {
        // 类型转换函数注册为命名空间函数
        let types = vec![
            ("integer", "INTEGER"),
            ("decimal", "DECIMAL"),
            ("float", "REAL"),
            ("double", "DOUBLE PRECISION"),
            ("string", "TEXT"),
            ("boolean", "BOOLEAN"),
            ("dateTime", "TIMESTAMP"),
            ("date", "DATE"),
        ];
        
        for (sparql_type, sql_type) in types {
            let name = format!("{}", sparql_type);
            let sql_type = sql_type.to_string();
            
            self.register_builtin(
                &name,
                FunctionMetadata {
                    name: name.clone(),
                    namespace: Some("http://www.w3.org/2001/XMLSchema#".to_string()),
                    min_args: 1,
                    max_args: 1,
                    description: format!("Cast to {}", sparql_type),
                    category: FunctionCategory::Cast,
                },
                |args| Ok(args[0].clone()),
                move |args: &[Expr], gen: &dyn SqlExpressionGenerator| {
                    Ok(format!(
                        "CAST({} AS {})",
                        gen.generate_expr(&args[0]),
                        sql_type
                    ))
                },
            );
        }
    }
    
    /// 注册内置函数
    fn register_builtin<F, G>(
        &mut self,
        name: &str,
        metadata: FunctionMetadata,
        evaluator: F,
        sql_generator: G,
    )
    where
        F: Fn(&[Expr]) -> FunctionResult + Send + Sync + 'static,
        G: Fn(&[Expr], &dyn SqlExpressionGenerator) -> Result<String, FunctionError> + Send + Sync + 'static,
    {
        let handler = BuiltinFunctionHandler::new(metadata, evaluator, sql_generator);
        self.functions.insert(name.to_uppercase(), Box::new(handler));
    }
    
    /// 注册自定义函数
    pub fn register(&mut self, name: &str, handler: Box<dyn FunctionHandler>) {
        self.functions.insert(name.to_uppercase(), handler);
    }
    
    /// 查找函数
    pub fn lookup(&self, name: &str) -> Option<&dyn FunctionHandler> {
        self.functions.get(&name.to_uppercase()).map(|h| h.as_ref())
    }
    
    /// 检查函数是否存在
    pub fn contains(&self, name: &str) -> bool {
        self.functions.contains_key(&name.to_uppercase())
    }
    
    /// 评估函数调用
    pub fn evaluate(&self, name: &str, args: &[Expr]) -> FunctionResult {
        match self.lookup(name) {
            Some(handler) => {
                let meta = handler.metadata();
                if args.len() < meta.min_args || args.len() > meta.max_args {
                    return Err(FunctionError::InvalidArgumentCount {
                        expected: meta.min_args,
                        actual: args.len(),
                    });
                }
                handler.evaluate(args)
            }
            None => Err(FunctionError::UnknownFunction(name.to_string())),
        }
    }
    
    /// 生成函数 SQL
    pub fn to_sql(
        &self,
        name: &str,
        args: &[Expr],
        sql_generator: &dyn SqlExpressionGenerator,
    ) -> Result<String, FunctionError> {
        match self.lookup(name) {
            Some(handler) => handler.to_sql(args, sql_generator),
            None => Err(FunctionError::UnknownFunction(name.to_string())),
        }
    }
    
    /// 获取所有函数名称
    pub fn function_names(&self) -> Vec<&str> {
        self.functions.keys().map(|k| k.as_str()).collect()
    }
    
    /// 按分类获取函数
    pub fn functions_by_category(&self, category: FunctionCategory) -> Vec<&dyn FunctionHandler> {
        self.functions.values()
            .filter(|h| h.metadata().category == category)
            .map(|h| h.as_ref())
            .collect()
    }
}

impl Default for FunctionRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// 简单的 SQL 表达式生成器实现
pub struct SimpleSqlGenerator;

impl SqlExpressionGenerator for SimpleSqlGenerator {
    fn generate_expr(&self, expr: &Expr) -> String {
        match expr {
            Expr::Term(term) => term.to_string(),
            Expr::Function { name, args } => {
                let arg_strs: Vec<String> = args.iter()
                    .map(|a| self.generate_expr(a))
                    .collect();
                format!("{}({})", name, arg_strs.join(", "))
            }
            _ => format!("{:?}", expr),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_function_registry_creation() {
        let registry = FunctionRegistry::new();
        assert!(registry.contains("STR"));
        assert!(registry.contains("CONCAT"));
        assert!(registry.contains("ABS"));
        assert!(registry.contains("NOW"));
    }
    
    #[test]
    fn test_string_functions() {
        let registry = FunctionRegistry::new();
        
        // 测试 SQL 生成
        let sql_gen = SimpleSqlGenerator;
        let args = vec![
            Expr::Term(Term::Variable("name".to_string())),
        ];
        
        let sql = registry.to_sql("UCASE", &args, &sql_gen).expect("valid regex");
        assert!(sql.contains("UPPER"));
    }
    
    #[test]
    fn test_numeric_functions() {
        let registry = FunctionRegistry::new();
        
        let sql_gen = SimpleSqlGenerator;
        let args = vec![
            Expr::Term(Term::Variable("value".to_string())),
        ];
        
        let sql = registry.to_sql("ROUND", &args, &sql_gen).expect("valid regex");
        assert!(sql.contains("ROUND"));
    }
    
    #[test]
    fn test_unknown_function() {
        let registry = FunctionRegistry::new();
        let args: Vec<Expr> = vec![];
        
        let result = registry.evaluate("UNKNOWN_FUNCTION", &args);
        assert!(matches!(result, Err(FunctionError::UnknownFunction(_))));
    }
}
