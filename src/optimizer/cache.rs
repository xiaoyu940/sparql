use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};
use crate::ir::node::LogicNode;
use crate::optimizer::OptimizerContext;

/// 缓存的查询计划
#[derive(Debug, Clone)]
pub struct CachedPlan {
    pub optimized_query: LogicNode,
    pub generated_sql: String,
    pub estimated_cost: f64,
    pub created_at: u64,
    pub access_count: u64,
    pub last_accessed: u64,
}

impl CachedPlan {
    pub fn new(optimized_query: LogicNode, generated_sql: String, estimated_cost: f64) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        Self {
            optimized_query,
            generated_sql,
            estimated_cost,
            created_at: now,
            access_count: 1,
            last_accessed: now,
        }
    }
    
    /// 记录访问
    pub fn record_access(&mut self) {
        self.access_count += 1;
        self.last_accessed = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
    }
    
    /// 检查是否过期
    pub fn is_expired(&self, max_age_seconds: u64) -> bool {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        (now - self.created_at) > max_age_seconds
    }
    
    /// 获取访问频率（每秒访问次数）
    pub fn get_access_rate(&self) -> f64 {
        let age_seconds = (self.last_accessed - self.created_at).max(1);
        self.access_count as f64 / age_seconds as f64
    }
}

/// 查询计划缓存
#[derive(Debug, Clone)]
pub struct QueryPlanCache {
    cache: HashMap<String, CachedPlan>,
    max_size: usize,
    max_age_seconds: u64,
    total_hits: u64,
    total_misses: u64,
    evictions: u64,
}

impl QueryPlanCache {
    pub fn new(max_size: usize, max_age_seconds: u64) -> Self {
        Self {
            cache: HashMap::new(),
            max_size,
            max_age_seconds,
            total_hits: 0,
            total_misses: 0,
            evictions: 0,
        }
    }
    
    /// 生成查询的缓存键
    pub fn generate_cache_key(&self, sparql_query: &str, _ctx: &OptimizerContext) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        
        // 简化版本：只基于查询内容生成哈希
        sparql_query.hash(&mut hasher);
        
        format!("query_{:x}", hasher.finish())
    }
    
    /// 获取缓存的计划
    pub fn get(&mut self, cache_key: &str) -> Option<CachedPlan> {
        let plan_key = cache_key.to_string();
        
        if let Some(mut plan) = self.cache.remove(&plan_key) {
            if plan.is_expired(self.max_age_seconds) {
                // 过期的计划，返回 None
                self.total_misses += 1;
                return None;
            }
            
            // 记录访问
            plan.record_access();
            self.total_hits += 1;
            
            // 重新插入缓存
            self.cache.insert(plan_key.clone(), plan.clone());
            Some(plan)
        } else {
            self.total_misses += 1;
            None
        }
    }
    
    /// 插入新的计划到缓存
    pub fn insert(&mut self, cache_key: String, plan: CachedPlan) {
        // 如果缓存已满，执行清理
        if self.cache.len() >= self.max_size {
            self.evict_lru();
        }
        
        self.cache.insert(cache_key, plan);
    }
    
    /// 移除最少使用的计划
    fn evict_lru(&mut self) {
        if self.cache.is_empty() {
            return;
        }
        
        // 找到最少使用的计划
        let mut lru_key = None;
        let mut min_access_time = u64::MAX;
        
        for (key, plan) in &self.cache {
            if plan.last_accessed < min_access_time {
                min_access_time = plan.last_accessed;
                lru_key = Some(key.clone());
            }
        }
        
        if let Some(key) = lru_key {
            self.cache.remove(&key);
            self.evictions += 1;
        }
    }
    
    /// 基于访问频率的智能清理
    pub fn smart_eviction(&mut self) {
        if self.cache.len() <= self.max_size / 2 {
            return; // 缓存未满，无需清理
        }
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        // 收集所有计划的统计信息
        let mut plan_stats: Vec<_> = self.cache.iter()
            .map(|(key, plan)| {
                let age = now - plan.created_at;
                let access_rate = plan.get_access_rate();
                let score = self.calculate_plan_score(plan, age, access_rate);
                (key.clone(), score)
            })
            .collect();
        
        // 按分数排序，分数低的优先清理
        plan_stats.sort_by(|(_, score_a), (_, score_b)| {
            score_a.partial_cmp(score_b).unwrap_or(std::cmp::Ordering::Equal)
        });
        
        // 清理分数最低的计划，直到缓存大小为 max_size 的 75%
        let target_size = self.max_size * 3 / 4;
        let to_remove = self.cache.len() - target_size;
        
        for (key, _) in plan_stats.into_iter().take(to_remove) {
            self.cache.remove(&key);
            self.evictions += 1;
        }
    }
    
    /// 计算计划的综合分数（用于智能清理）
    fn calculate_plan_score(&self, plan: &CachedPlan, age_seconds: u64, access_rate: f64) -> f64 {
        // 分数 = 访问频率 * 年龄权重 - 成本权重
        let age_weight = (age_seconds as f64).ln_1p(); // ln(1 + age)
        let cost_weight = plan.estimated_cost.ln_1p();
        
        access_rate * age_weight - cost_weight * 0.1
    }
    
    /// 清理过期计划
    pub fn cleanup_expired(&mut self) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        let expired_keys: Vec<String> = self.cache.iter()
            .filter(|(_, plan)| (now - plan.created_at) > self.max_age_seconds)
            .map(|(key, _)| key.clone())
            .collect();
        
        for key in expired_keys {
            self.cache.remove(&key);
            self.evictions += 1;
        }
    }
    
    /// 获取缓存统计信息
    pub fn get_stats(&self) -> CacheStats {
        let total_requests = self.total_hits + self.total_misses;
        let hit_rate = if total_requests > 0 {
            self.total_hits as f64 / total_requests as f64
        } else {
            0.0
        };
        
        CacheStats {
            size: self.cache.len(),
            max_size: self.max_size,
            total_hits: self.total_hits,
            total_misses: self.total_misses,
            hit_rate,
            evictions: self.evictions,
        }
    }
    
    /// 清空缓存
    pub fn clear(&mut self) {
        self.cache.clear();
        self.total_hits = 0;
        self.total_misses = 0;
        self.evictions = 0;
    }
    
    /// 预热缓存（可选功能）
    pub fn warm_up(&mut self, common_queries: Vec<(String, LogicNode, String, f64)>) {
        for (cache_key, optimized_query, sql, cost) in common_queries {
            if !self.cache.contains_key(&cache_key) {
                let plan = CachedPlan::new(optimized_query, sql, cost);
                self.cache.insert(cache_key, plan);
            }
        }
    }
}

/// 缓存统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub size: usize,
    pub max_size: usize,
    pub total_hits: u64,
    pub total_misses: u64,
    pub hit_rate: f64,
    pub evictions: u64,
}

impl Default for QueryPlanCache {
    fn default() -> Self {
        Self::new(1000, 3600) // 默认缓存1000个计划，1小时过期
    }
}

/// 缓存配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub enabled: bool,
    pub max_size: usize,
    pub max_age_seconds: u64,
    pub cleanup_interval_seconds: u64,
    pub smart_eviction: bool,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_size: 1000,
            max_age_seconds: 3600,
            cleanup_interval_seconds: 300, // 5分钟清理一次
            smart_eviction: true,
        }
    }
}

/// 缓存管理器
#[derive(Debug, Clone)]
pub struct CacheManager {
    cache: QueryPlanCache,
    config: CacheConfig,
    last_cleanup: u64,
}

impl CacheManager {
    pub fn new(config: CacheConfig) -> Self {
        Self {
            cache: QueryPlanCache::new(config.max_size, config.max_age_seconds),
            config,
            last_cleanup: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        }
    }
    
    /// 生成缓存键
    pub fn generate_cache_key(&self, sparql_query: &str, ctx: &OptimizerContext) -> String {
        self.cache.generate_cache_key(sparql_query, ctx)
    }
    
    /// 获取或创建查询计划
    pub fn get_or_create<F>(&mut self, cache_key: &str, create_fn: F) -> Option<CachedPlan>
    where
        F: FnOnce() -> Option<CachedPlan>,
    {
        // 定期清理
        self.periodic_cleanup();
        
        // 尝试从缓存获取
        if let Some(cached_plan) = self.cache.get(cache_key) {
            return Some(cached_plan.clone());
        }
        
        // 缓存未命中，创建新计划
        if let Some(new_plan) = create_fn() {
            let key = cache_key.to_string();
            self.cache.insert(key, new_plan.clone());
            Some(new_plan)
        } else {
            None
        }
    }
    
    /// 定期清理
    fn periodic_cleanup(&mut self) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        if (now - self.last_cleanup) >= self.config.cleanup_interval_seconds {
            if self.config.smart_eviction {
                self.cache.smart_eviction();
            } else {
                self.cache.cleanup_expired();
            }
            self.last_cleanup = now;
        }
    }
    
    /// 获取缓存统计信息
    pub fn get_stats(&self) -> CacheStats {
        self.cache.get_stats()
    }
    
    /// 清空缓存
    pub fn clear(&mut self) {
        self.cache.clear();
    }
    
    /// 检查缓存是否启用
    pub fn is_enabled(&self) -> bool {
        self.config.enabled
    }
}

impl Default for CacheManager {
    fn default() -> Self {
        Self::new(CacheConfig::default())
    }
}
