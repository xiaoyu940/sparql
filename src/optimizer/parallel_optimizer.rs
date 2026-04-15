use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerPass, OptimizerContext};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

/// 并行优化配置
#[derive(Debug, Clone)]
pub struct ParallelConfig {
    pub enabled: bool,
    pub max_threads: usize,
    pub min_nodes_for_parallel: usize,
    pub chunk_size: usize,
    pub enable_work_stealing: bool,
}

impl Default for ParallelConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_threads: num_cpus::get(),
            min_nodes_for_parallel: 10,
            chunk_size: 4,
            enable_work_stealing: true,
        }
    }
}

/// 并行优化统计信息
#[derive(Debug, Clone, Default)]
pub struct ParallelStats {
    pub total_optimizations: u64,
    pub parallel_optimizations: u64,
    pub sequential_optimizations: u64,
    pub total_time_ms: u64,
    pub parallel_time_ms: u64,
    pub sequential_time_ms: u64,
    pub threads_used: usize,
    pub work_stealing_events: u64,
}

/// 并行优化器
#[derive(Debug)]
pub struct ParallelOptimizer {
    config: ParallelConfig,
    stats: Arc<Mutex<ParallelStats>>,
    #[allow(dead_code)]
    thread_pool: rayon::ThreadPool,
}

impl ParallelOptimizer {
    pub fn new(config: ParallelConfig) -> Self {
        let thread_pool = rayon::ThreadPoolBuilder::new()
            .num_threads(config.max_threads)
            .build()
            .unwrap_or_else(|_| rayon::ThreadPoolBuilder::new().build().expect("should build thread pool"));
        
        Self {
            config,
            stats: Arc::new(Mutex::new(ParallelStats {
                total_optimizations: 0,
                parallel_optimizations: 0,
                sequential_optimizations: 0,
                total_time_ms: 0,
                parallel_time_ms: 0,
                sequential_time_ms: 0,
                threads_used: 0,
                work_stealing_events: 0,
            })),
            thread_pool,
        }
    }
    
    /// 并行优化查询树
    pub fn optimize_parallel(&mut self, node: &mut LogicNode, passes: &[Box<dyn OptimizerPass>], ctx: &OptimizerContext) {
        let start_time = Instant::now();
        
        // 计算节点数量
        let node_count = self.count_nodes(node);
        
        // 决定是否使用并行优化
        if self.config.enabled && node_count >= self.config.min_nodes_for_parallel {
            self.optimize_parallel_internal(node, passes, ctx);
        } else {
            self.optimize_sequential(node, passes, ctx);
        }
        
        let elapsed = start_time.elapsed();
        self.update_stats(elapsed);
    }
    
    /// 内部并行优化实现
    fn optimize_parallel_internal(&mut self, node: &mut LogicNode, passes: &[Box<dyn OptimizerPass>], ctx: &OptimizerContext) {
        let start_time = Instant::now();
        
        // 简化版本：直接应用优化规则（真正的并行需要更复杂的实现）
        for pass in passes {
            pass.apply(node, ctx);
        }
        
        let elapsed = start_time.elapsed();
        self.record_parallel_optimization(elapsed);
    }
    
    /// 并行应用优化规则
    #[allow(dead_code)]
    fn apply_passes_parallel(&mut self, node: &mut LogicNode, passes: &[&dyn OptimizerPass], ctx: &OptimizerContext) {
        // 方法1: 按规则并行应用（适用于独立的规则）
        if passes.len() > 2 {
            self.apply_passes_independent_parallel(node, passes, ctx);
        } else {
            // 方法2: 按子树并行应用（适用于复杂的规则）
            self.apply_subtree_parallel(node, passes, ctx);
        }
    }
    
    /// 独立规则并行应用
    #[allow(dead_code)]
    fn apply_passes_independent_parallel(&mut self, node: &mut LogicNode, passes: &[&dyn OptimizerPass], ctx: &OptimizerContext) {
        // 简化版本：顺序应用规则（真正的并行需要更复杂的同步机制）
        for pass in passes {
            pass.apply(node, ctx);
        }
    }
    
    /// 子树并行应用
    #[allow(dead_code)]
    fn apply_subtree_parallel(&mut self, node: &mut LogicNode, passes: &[&dyn OptimizerPass], ctx: &OptimizerContext) {
        // 简化版本：递归优化子树
        self.optimize_subtree_parallel(node, passes, ctx);
    }
    
    /// 递归并行优化子树
    #[allow(dead_code)]
    fn optimize_subtree_parallel(&mut self, node: &mut LogicNode, passes: &[&dyn OptimizerPass], ctx: &OptimizerContext) {
        match node {
            LogicNode::Join { children, .. } => {
                // 优化子节点
                for child in children.iter_mut() {
                    self.optimize_subtree_parallel(child, passes, ctx);
                }
                
                // 应用当前节点的优化规则
                for pass in passes {
                    pass.apply(node, ctx);
                }
            },
            LogicNode::Union(children) => {
                // 优化 UNION 的所有子节点
                for child in children.iter_mut() {
                    self.optimize_subtree_parallel(child, passes, ctx);
                }
                
                // 应用当前节点的优化规则
                for pass in passes {
                    pass.apply(node, ctx);
                }
            },
            LogicNode::Filter { child, .. } => {
                // 先优化子节点，再应用规则
                self.optimize_subtree_parallel(child, passes, ctx);
                
                for pass in passes {
                    pass.apply(node, ctx);
                }
            },
            LogicNode::Construction { child, .. } => {
                // 先优化子节点，再应用规则
                self.optimize_subtree_parallel(child, passes, ctx);
                
                for pass in passes {
                    pass.apply(node, ctx);
                }
            },
            LogicNode::Aggregation { child, .. } => {
                // 先优化子节点，再应用规则
                self.optimize_subtree_parallel(child, passes, ctx);
                
                for pass in passes {
                    pass.apply(node, ctx);
                }
            },
            _ => {
                // 叶子节点，直接应用规则
                for pass in passes {
                    pass.apply(node, ctx);
                }
            }
        }
    }
    
    /// 顺序优化
    fn optimize_sequential(&mut self, node: &mut LogicNode, passes: &[Box<dyn OptimizerPass>], ctx: &OptimizerContext) {
        let start_time = Instant::now();
        
        for pass in passes {
            pass.apply(node, ctx);
        }
        
        let elapsed = start_time.elapsed();
        self.record_sequential_optimization(elapsed);
    }
    
    /// 计算节点数量
    fn count_nodes(&self, node: &LogicNode) -> usize {
        match node {
            LogicNode::Join { children, .. } => {
                1 + children.iter().map(|child| self.count_nodes(child)).sum::<usize>()
            },
            LogicNode::Union(children) => {
                1 + children.iter().map(|child| self.count_nodes(child)).sum::<usize>()
            },
            LogicNode::Filter { child, .. } => 1 + self.count_nodes(child),
            LogicNode::Construction { child, .. } => 1 + self.count_nodes(child),
            LogicNode::Aggregation { child, .. } => 1 + self.count_nodes(child),
            LogicNode::ExtensionalData { .. } => 1,
            LogicNode::IntensionalData { .. } => 1,
            LogicNode::Limit { child, .. } => 1 + self.count_nodes(child),
            LogicNode::Values { .. } => 1,
            LogicNode::Path { .. } => 1,
            LogicNode::Graph { child, .. } => 1 + self.count_nodes(child),  // [S5-P0-2]
            LogicNode::GraphUnion { children, .. } => {
                1 + children.iter().map(|child| self.count_nodes(child)).sum::<usize>()  // [S5-P0-2]
            }
            LogicNode::Service { inner_plan, .. } => 1 + self.count_nodes(inner_plan),  // [S6-P1-2]
            LogicNode::SubQuery { inner, .. } => 1 + self.count_nodes(inner),  // [S8-P0-4]
            LogicNode::CorrelatedJoin { outer, inner, .. } => {
                1 + self.count_nodes(outer) + self.count_nodes(inner)  // [S8-P0-4]
            }
            LogicNode::RecursivePath { base_path, recursive_path, .. } => {
                1 + self.count_nodes(base_path) + self.count_nodes(recursive_path)  // [S9-P2]
            }
        }
    }
    
    /// 记录并行优化统计
    fn record_parallel_optimization(&mut self, elapsed: Duration) {
        if let Ok(mut stats) = self.stats.lock() {
            stats.total_optimizations += 1;
            stats.parallel_optimizations += 1;
            stats.total_time_ms += elapsed.as_millis() as u64;
            stats.parallel_time_ms += elapsed.as_millis() as u64;
            stats.threads_used = self.config.max_threads;
        }
    }
    
    /// 记录顺序优化统计
    fn record_sequential_optimization(&mut self, elapsed: Duration) {
        if let Ok(mut stats) = self.stats.lock() {
            stats.total_optimizations += 1;
            stats.sequential_optimizations += 1;
            stats.total_time_ms += elapsed.as_millis() as u64;
            stats.sequential_time_ms += elapsed.as_millis() as u64;
        }
    }
    
    /// 更新统计信息
    fn update_stats(&mut self, elapsed: Duration) {
        if let Ok(mut stats) = self.stats.lock() {
            stats.total_time_ms += elapsed.as_millis() as u64;
        }
    }
    
    /// 获取统计信息
    pub fn get_stats(&self) -> ParallelStats {
        self.stats.lock().unwrap_or_else(|poisoned| poisoned.into_inner()).clone()
    }
    
    /// 重置统计信息
    pub fn reset_stats(&mut self) {
        if let Ok(mut stats) = self.stats.lock() {
            *stats = ParallelStats {
                total_optimizations: 0,
                parallel_optimizations: 0,
                sequential_optimizations: 0,
                total_time_ms: 0,
                parallel_time_ms: 0,
                sequential_time_ms: 0,
                threads_used: 0,
                work_stealing_events: 0,
            };
        }
    }
    
    /// 动态调整配置
    pub fn adjust_config(&mut self, node_count: usize) {
        // 根据节点数量动态调整并行策略
        if node_count < 10 {
            self.config.enabled = false;
        } else if node_count < 50 {
            self.config.max_threads = (self.config.max_threads / 2).max(1);
            self.config.chunk_size = 2;
        } else {
            self.config.max_threads = num_cpus::get();
            self.config.chunk_size = 4;
        }
    }
}

impl Default for ParallelOptimizer {
    fn default() -> Self {
        Self::new(ParallelConfig::default())
    }
}

/// 工作窃取队列
pub struct WorkStealingQueue {
    tasks: Arc<Mutex<Vec<Box<dyn FnOnce() + Send>>>>,
    #[allow(dead_code)]
    workers: Vec<thread::JoinHandle<()>>,
}

impl WorkStealingQueue {
    pub fn new(num_workers: usize) -> Self {
        let tasks: Arc<Mutex<Vec<Box<dyn FnOnce() + Send>>>> = Arc::new(Mutex::new(Vec::new()));
        let mut workers = Vec::new();
        
        for _ in 0..num_workers {
            let tasks_clone = Arc::clone(&tasks);
            let worker = thread::spawn(move || {
                loop {
                    let task = {
                        let mut tasks_guard = tasks_clone.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                        tasks_guard.pop()
                    };
                    
                    match task {
                        Some(task) => task(),
                        None => {
                            // 没有任务，短暂休眠
                            thread::sleep(Duration::from_millis(1));
                        }
                    }
                }
            });
            workers.push(worker);
        }
        
        Self { tasks, workers }
    }
    
    pub fn add_task(&self, task: Box<dyn FnOnce() + Send>) {
        let mut tasks_guard = self.tasks.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        tasks_guard.push(task);
    }
}

/// 并行性能分析器
#[derive(Debug, Clone)]
pub struct ParallelPerformanceAnalyzer {
    pub optimization_times: Vec<u64>,
    pub speedup_ratios: Vec<f64>,
    pub efficiency_scores: Vec<f64>,
}

impl ParallelPerformanceAnalyzer {
    pub fn new() -> Self {
        Self {
            optimization_times: Vec::new(),
            speedup_ratios: Vec::new(),
            efficiency_scores: Vec::new(),
        }
    }
    
    /// 记录优化性能
    pub fn record_optimization(&mut self, parallel_time: u64, sequential_time: u64, num_threads: usize) {
        self.optimization_times.push(parallel_time);
        
        if sequential_time > 0 {
            let speedup = sequential_time as f64 / parallel_time as f64;
            let efficiency = speedup / num_threads as f64;
            
            self.speedup_ratios.push(speedup);
            self.efficiency_scores.push(efficiency);
        }
    }
    
    /// 计算平均加速比
    pub fn average_speedup(&self) -> f64 {
        if self.speedup_ratios.is_empty() {
            return 0.0;
        }
        self.speedup_ratios.iter().sum::<f64>() / self.speedup_ratios.len() as f64
    }
    
    /// 计算平均效率
    pub fn average_efficiency(&self) -> f64 {
        if self.efficiency_scores.is_empty() {
            return 0.0;
        }
        self.efficiency_scores.iter().sum::<f64>() / self.efficiency_scores.len() as f64
    }
    
    /// 获取性能报告
    pub fn performance_report(&self) -> String {
        format!(
            "Parallel Optimization Performance:\n\
             Average Speedup: {:.2}x\n\
             Average Efficiency: {:.2}%\n\
             Total Optimizations: {}",
            self.average_speedup(),
            self.average_efficiency() * 100.0,
            self.optimization_times.len()
        )
    }
}

impl Default for ParallelPerformanceAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}
