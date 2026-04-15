//! 错误类型定义
//! 
//! 统一的错误类型，用于 V2.0 改造

/// 统一的错误类型
#[derive(Debug, Clone)]
pub enum OntopError {
    /// IO 错误
    IoError(String),
    /// HTTP 错误
    HttpError(String),
    /// 序列化错误
    SerializationError(String),
    /// SQL 错误
    SQLError(String),
    /// 数据库错误
    DatabaseError(String),
    /// IR 错误
    IRError(String),
    /// 优化错误
    OptimizationError(String),
    /// 配置错误
    ConfigError(String),
    /// 元数据缺失错误
    MissingMetadata(String),
    /// 其他错误
    Other(String),
}

impl std::fmt::Display for OntopError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OntopError::IoError(msg) => write!(f, "IO Error: {}", msg),
            OntopError::HttpError(msg) => write!(f, "HTTP Error: {}", msg),
            OntopError::SerializationError(msg) => write!(f, "Serialization Error: {}", msg),
            OntopError::SQLError(msg) => write!(f, "SQL Error: {}", msg),
            OntopError::DatabaseError(msg) => write!(f, "Database Error: {}", msg),
            OntopError::IRError(msg) => write!(f, "IR Error: {}", msg),
            OntopError::OptimizationError(msg) => write!(f, "Serialization Error: {}", msg),
            OntopError::ConfigError(msg) => write!(f, "Config Error: {}", msg),
            OntopError::MissingMetadata(msg) => write!(f, "Missing Metadata: {}", msg),
            OntopError::Other(msg) => write!(f, "Other Error: {}", msg),
        }
    }
}

impl std::error::Error for OntopError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }
}

impl From<std::io::Error> for OntopError {
    fn from(err: std::io::Error) -> Self {
        OntopError::IoError(err.to_string())
    }
}

impl From<serde_json::Error> for OntopError {
    fn from(err: serde_json::Error) -> Self {
        OntopError::SerializationError(err.to_string())
    }
}


pub mod handler_v2;
pub mod classifier;

pub use handler_v2::*;
pub use classifier::*;
