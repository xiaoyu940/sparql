//! Query Cache 模块 (Sprint 9 P2)
//!
//! 提供查询结果缓存，减少重复解析和SQL生成

use std::collections::HashMap;
use std::time::{Duration, Instant};
use std::sync::RwLock;

use crate::ir::node::LogicNode;

/// 缓存配置
#[derive(Debug, Clone)]
pub struct CacheConfig {
    /// 解析缓存大小
    pub parse_cache_size: usize,
    /// 优化缓存大小
    pub optimize_cache_size: usize,
    /// SQL 缓存大小
    pub sql_cache_size: usize,
    /// 结果缓存大小
    pub result_cache_size: usize,
    /// 默认 TTL
    pub default_ttl: Duration,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            parse_cache_size: 1000,
            optimize_cache_size: 500,
            sql_cache_size: 500,
            result_cache_size: 200,
            default_ttl: Duration::from_secs(1800), // 30 分钟
        }
    }
}

/// 带 TTL 的缓存条目
#[derive(Debug, Clone)]
struct CacheEntry<V> {
    value: V,
    created_at: Instant,
    ttl: Duration,
}

impl<V> CacheEntry<V> {
    fn new(value: V, ttl: Duration) -> Self {
        Self {
            value,
            created_at: Instant::now(),
            ttl,
        }
    }
    
    fn is_expired(&self) -> bool {
        self.created_at.elapsed() > self.ttl
    }
}

/// 缓存统计
#[derive(Debug, Default, Clone)]
pub struct CacheStats {
    pub parse_hits: u64,
    pub parse_misses: u64,
    pub sql_hits: u64,
    pub sql_misses: u64,
}

/// 查询缓存
pub struct QueryCache {
    /// SPARQL 解析缓存: SPARQL string -> IR
    parse_cache: RwLock<HashMap<String, CacheEntry<LogicNode>>>,
    parse_cache_ttl: Duration,
    
    /// SQL 生成缓存: IR hash -> SQL
    sql_cache: RwLock<HashMap<u64, CacheEntry<String>>>,
    sql_cache_ttl: Duration,
    
    /// 统计信息
    stats: RwLock<CacheStats>,
}

impl QueryCache {
    /// 创建新的查询缓存
    pub fn new(config: CacheConfig) -> Self {
        Self {
            parse_cache: RwLock::new(HashMap::with_capacity(config.parse_cache_size)),
            parse_cache_ttl: config.default_ttl,
            sql_cache: RwLock::new(HashMap::with_capacity(config.sql_cache_size)),
            sql_cache_ttl: config.default_ttl,
            stats: RwLock::new(CacheStats::default()),
        }
    }
    
    /// 获取解析缓存
    pub fn get_parse_result(&self, sparql: &str) -> Option<LogicNode> {
        let cache = self.parse_cache.read().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner());
        
        if let Some(entry) = cache.get(sparql) {
            if !entry.is_expired() {
                let mut stats = self.stats.write().unwrap_or_else(|_| RwLock::new(CacheStats::default()).into_inner());
                stats.parse_hits += 1;
                return Some(entry.value.clone());
            }
        }
        
        let mut stats = self.stats.write().unwrap_or_else(|_| RwLock::new(CacheStats::default()).into_inner());
        stats.parse_misses += 1;
        None
    }
    
    /// 设置解析缓存
    pub fn set_parse_result(&self, sparql: &str, ir: LogicNode) {
        let mut cache = self.parse_cache.write().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner());
        let entry = CacheEntry::new(ir, self.parse_cache_ttl);
        cache.insert(sparql.to_string(), entry);
    }
    
    /// 获取 SQL 缓存
    pub fn get_sql(&self, ir_hash: u64) -> Option<String> {
        let cache = self.sql_cache.read().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner());
        
        if let Some(entry) = cache.get(&ir_hash) {
            if !entry.is_expired() {
                let mut stats = self.stats.write().unwrap_or_else(|_| RwLock::new(CacheStats::default()).into_inner());
                stats.sql_hits += 1;
                return Some(entry.value.clone());
            }
        }
        
        let mut stats = self.stats.write().unwrap_or_else(|_| RwLock::new(CacheStats::default()).into_inner());
        stats.sql_misses += 1;
        None
    }
    
    /// 设置 SQL 缓存
    pub fn set_sql(&self, ir_hash: u64, sql: String) {
        let mut cache = self.sql_cache.write().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner());
        let entry = CacheEntry::new(sql, self.sql_cache_ttl);
        cache.insert(ir_hash, entry);
    }
    
    /// 计算 IR 哈希值
    pub fn compute_ir_hash(ir: &LogicNode) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        // 使用IR的字符串表示计算哈希
        let serialized = format!("{:?}", ir);
        serialized.hash(&mut hasher);
        hasher.finish()
    }
    
    /// 获取缓存统计
    pub fn get_stats(&self) -> CacheStats {
        self.stats.read().unwrap_or_else(|_| RwLock::new(CacheStats::default()).into_inner()).clone()
    }
    
    /// 清空所有缓存
    pub fn clear_all(&self) {
        self.parse_cache.write().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner()).clear();
        self.sql_cache.write().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner()).clear();
    }
    
    /// 使特定 SPARQL 查询缓存失效
    pub fn invalidate_parse(&self, sparql: &str) {
        self.parse_cache.write().unwrap_or_else(|_| RwLock::new(HashMap::new()).into_inner()).remove(sparql);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_cache_basic() {
        let cache = QueryCache::new(CacheConfig::default());
        let sparql = "SELECT ?s WHERE { ?s a :Person }";
        
        // 首次 miss
        assert!(cache.get_parse_result(sparql).is_none());
        
        // 设置缓存
        let ir = LogicNode::Union(vec![]);
        cache.set_parse_result(sparql, ir.clone());
        
        // 再次 hit
        assert!(cache.get_parse_result(sparql).is_some());
        
        let stats = cache.get_stats();
        assert_eq!(stats.parse_hits, 1);
        assert_eq!(stats.parse_misses, 1);
    }
    
    #[test]
    fn test_sql_cache() {
        let cache = QueryCache::new(CacheConfig::default());
        let ir = LogicNode::Union(vec![]);
        let hash = QueryCache::compute_ir_hash(&ir);
        
        // 首次 miss
        assert!(cache.get_sql(hash).is_none());
        
        // 设置缓存
        cache.set_sql(hash, "SELECT * FROM employees".to_string());
        
        // 再次 hit
        assert_eq!(cache.get_sql(hash).expect("should get SQL"), "SELECT * FROM employees");
    }
}
