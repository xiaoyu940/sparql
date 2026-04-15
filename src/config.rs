use serde::{Deserialize, Serialize};

/// 优化配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationConfig {
    /// 是否启用谓词下推
    pub enable_predicate_pushdown: bool,
    
    /// 是否启用并集提升
    pub enable_union_lifting: bool,
    
    /// 是否启用 Left-to-Inner 转换
    pub enable_left_to_inner: bool,
    
    /// 是否启用 Tree-Witness 重写
    pub enable_tree_witness: bool,
    
    /// 查询复杂度阈值（超过此阈值启用高级优化）
    pub advanced_optimization_threshold: usize,
    
    /// 最大优化时间（毫秒）
    pub max_optimization_time_ms: u64,
    
    /// 是否启用统计信息
    pub enable_statistics: bool,
    
    /// 缓存配置
    pub cache_config: CacheConfig,
}

impl Default for OptimizationConfig {
    fn default() -> Self {
        Self {
            enable_predicate_pushdown: true,
            enable_union_lifting: true,
            enable_left_to_inner: true,
            enable_tree_witness: false, // 默认关闭高级优化
            advanced_optimization_threshold: 10,
            max_optimization_time_ms: 5000,
            enable_statistics: true,
            cache_config: CacheConfig::default(),
        }
    }
}

/// 缓存配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    /// 是否启用查询计划缓存
    pub enable_plan_cache: bool,
    
    /// 缓存大小
    pub cache_size: usize,
    
    /// 缓存过期时间（秒）
    pub cache_ttl_seconds: u64,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            enable_plan_cache: true,
            cache_size: 1000,
            cache_ttl_seconds: 3600,
        }
    }
}

/// 全局配置管理器
pub struct ConfigManager {
    config: OptimizationConfig,
}

impl ConfigManager {
    pub fn new() -> Self {
        Self {
            config: Self::load_from_env(),
        }
    }
    
    pub fn get_config(&self) -> &OptimizationConfig {
        &self.config
    }
    
    pub fn update_config(&mut self, new_config: OptimizationConfig) {
        self.config = new_config;
    }
    
    fn load_from_env() -> OptimizationConfig {
        let mut config = OptimizationConfig::default();
        
        // 从环境变量加载配置
        if let Ok(val) = std::env::var("ONTOP_ENABLE_PREDICATE_PUSHDOWN") {
            config.enable_predicate_pushdown = val.parse().unwrap_or(true);
        }
        
        if let Ok(val) = std::env::var("ONTOP_ENABLE_UNION_LIFTING") {
            config.enable_union_lifting = val.parse().unwrap_or(true);
        }
        
        if let Ok(val) = std::env::var("ONTOP_ENABLE_LEFT_TO_INNER") {
            config.enable_left_to_inner = val.parse().unwrap_or(true);
        }
        
        if let Ok(val) = std::env::var("ONTOP_ENABLE_TREE_WITNESS") {
            config.enable_tree_witness = val.parse().unwrap_or(false);
        }
        
        if let Ok(val) = std::env::var("ONTOP_ADVANCED_THRESHOLD") {
            config.advanced_optimization_threshold = val.parse().unwrap_or(10);
        }
        
        if let Ok(val) = std::env::var("ONTOP_MAX_OPT_TIME_MS") {
            config.max_optimization_time_ms = val.parse().unwrap_or(5000);
        }
        
        config
    }
    
    #[allow(dead_code)]
    fn load_from_file() -> Result<OptimizationConfig, Box<dyn std::error::Error>> {
        let path = std::env::var("ONTOP_CONFIG_FILE")
            .unwrap_or_else(|_| "config/ontop_config.json".to_string());
        let content = std::fs::read_to_string(&path)?;
        let config: OptimizationConfig = serde_json::from_str(&content)?;
        Ok(config)
    }
    
    pub fn should_use_advanced_optimization(&self, query_complexity: usize) -> bool {
        query_complexity > self.config.advanced_optimization_threshold
    }
}

/// 查询复杂度分析器
pub struct QueryComplexityAnalyzer;

impl QueryComplexityAnalyzer {
    pub fn analyze_complexity(node: &crate::ir::node::LogicNode) -> usize {
        match node {
            crate::ir::node::LogicNode::Join { children, .. } => {
                1 + children.iter().map(|c| Self::analyze_complexity(c)).sum::<usize>()
            },
            crate::ir::node::LogicNode::Filter { child, .. } => {
                1 + Self::analyze_complexity(child)
            },
            crate::ir::node::LogicNode::Union(children) => {
                1 + children.iter().map(|c| Self::analyze_complexity(c)).sum::<usize>()
            },
            crate::ir::node::LogicNode::Construction { child, .. } => {
                1 + Self::analyze_complexity(child)
            },
            crate::ir::node::LogicNode::Aggregation { child, .. } => {
                2 + Self::analyze_complexity(child) // 聚合复杂度更高
            },
            _ => 1,
        }
    }
}

/// 性能监控配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    /// 是否启用性能监控
    pub enable_monitoring: bool,
    
    /// 是否记录优化统计
    pub record_optimization_stats: bool,
    
    /// 是否记录查询执行时间
    pub record_execution_time: bool,
    
    /// 统计信息保留时间（天）
    pub stats_retention_days: u32,
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            enable_monitoring: true,
            record_optimization_stats: true,
            record_execution_time: true,
            stats_retention_days: 7,
        }
    }
}

/// 调试配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugConfig {
    /// 是否启用调试日志
    pub enable_debug_log: bool,
    
    /// 是否打印优化过程
    pub print_optimization_steps: bool,
    
    /// 是否打印生成的 SQL
    pub print_generated_sql: bool,
    
    /// 日志级别
    pub log_level: LogLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogLevel {
    Error,
    Warn,
    Info,
    Debug,
    Trace,
}

impl Default for DebugConfig {
    fn default() -> Self {
        Self {
            enable_debug_log: false,
            print_optimization_steps: false,
            print_generated_sql: false,
            log_level: LogLevel::Info,
        }
    }
}
