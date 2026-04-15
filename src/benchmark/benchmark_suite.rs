use crate::ir::node::LogicNode;
use crate::optimizer::{OptimizerContext, OptimizerPass};
use crate::codegen::enhanced_generator::EnhancedSqlGenerator;
use std::collections::HashMap;
use std::time::{Duration, Instant};
use std::sync::Arc;
use serde::{Serialize, Deserialize};

/// 性能基准测试套件
#[derive(Debug)]
pub struct BenchmarkSuite {
    pub benchmarks: Vec<Benchmark>,
    pub results: Vec<BenchmarkResult>,
    pub config: BenchmarkConfig,
}

/// 基准测试配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkConfig {
    pub warmup_iterations: usize,
    pub measurement_iterations: usize,
    pub timeout_seconds: u64,
    pub enable_profiling: bool,
    pub memory_tracking: bool,
    pub statistical_analysis: bool,
}

impl Default for BenchmarkConfig {
    fn default() -> Self {
        Self {
            warmup_iterations: 3,
            measurement_iterations: 10,
            timeout_seconds: 30,
            enable_profiling: false,
            memory_tracking: true,
            statistical_analysis: true,
        }
    }
}

/// 单个基准测试
pub struct Benchmark {
    pub name: String,
    pub description: String,
    pub category: BenchmarkCategory,
    pub query_generator: Box<dyn Fn() -> LogicNode>,
    pub setup_fn: Option<Box<dyn Fn() -> OptimizerContext>>,
    pub expected_complexity: ComplexityLevel,
}

impl std::fmt::Debug for Benchmark {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Benchmark")
            .field("name", &self.name)
            .field("description", &self.description)
            .field("category", &self.category)
            .field("expected_complexity", &self.expected_complexity)
            .finish()
    }
}

/// 基准测试类别
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BenchmarkCategory {
    SimpleQuery,
    JoinOptimization,
    FilterOptimization,
    Aggregation,
    UnionOptimization,
    ComplexQuery,
    StressTest,
}

/// 复杂度级别
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ComplexityLevel {
    Low,
    Medium,
    High,
    VeryHigh,
}

/// 基准测试结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub benchmark_name: String,
    pub category: BenchmarkCategory,
    pub execution_times: Vec<Duration>,
    pub memory_usage: Vec<usize>,
    pub statistics: BenchmarkStatistics,
    pub success: bool,
    pub error_message: Option<String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// 基准测试统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkStatistics {
    pub mean_time: Duration,
    pub median_time: Duration,
    pub min_time: Duration,
    pub max_time: Duration,
    pub std_deviation: f64,
    pub percentile_95: Duration,
    pub percentile_99: Duration,
    pub mean_memory: usize,
    pub memory_peak: usize,
    pub throughput_qps: f64,
}

impl BenchmarkSuite {
    pub fn new() -> Self {
        Self {
            benchmarks: Vec::new(),
            results: Vec::new(),
            config: BenchmarkConfig::default(),
        }
    }
    
    /// 添加基准测试
    pub fn add_benchmark(&mut self, benchmark: Benchmark) {
        self.benchmarks.push(benchmark);
    }
    
    /// 运行所有基准测试
    pub fn run_all(&mut self) -> &Vec<BenchmarkResult> {
        println!("Running {} benchmarks...", self.benchmarks.len());
        println!("Configuration: {:?}", self.config);
        println!("========================================");
        
        self.results.clear();
        
        for benchmark in &self.benchmarks {
            println!("Running benchmark: {}", benchmark.name);
            let result = self.run_single_benchmark(benchmark);
            self.results.push(result);
            
            // 打印即时结果
            if let Some(last_result) = self.results.last() {
                self.print_benchmark_result(last_result);
            }
        }
        
        println!("========================================");
        println!("All benchmarks completed!");
        
        &self.results
    }
    
    /// 运行单个基准测试
    pub fn run_single_benchmark(&self, benchmark: &Benchmark) -> BenchmarkResult {
        let mut execution_times = Vec::new();
        let mut memory_usage = Vec::new();
        let mut success = true;
        let mut error_message = None;
        
        // 设置优化上下文
        let ctx = if let Some(setup_fn) = &benchmark.setup_fn {
            setup_fn()
        } else {
            self.create_default_context()
        };
        
        // 预热运行
        for _ in 0..self.config.warmup_iterations {
            let query = (benchmark.query_generator)();
            if self.execute_single_run(&query, &ctx).is_err() {
                success = false;
                error_message = Some("Warmup failed".to_string());
                break;
            }
        }
        
        if success {
            // 正式测量
            for _ in 0..self.config.measurement_iterations {
                let query = (benchmark.query_generator)();
                
                let start_time = Instant::now();
                let start_memory = if self.config.memory_tracking {
                    self.get_memory_usage()
                } else {
                    0
                };
                
                match self.execute_single_run(&query, &ctx) {
                    Ok(_) => {
                        let elapsed = start_time.elapsed();
                        let end_memory = if self.config.memory_tracking {
                            self.get_memory_usage()
                        } else {
                            0
                        };
                        
                        execution_times.push(elapsed);
                        memory_usage.push(end_memory.saturating_sub(start_memory));
                    },
                    Err(e) => {
                        success = false;
                        error_message = Some(e);
                        break;
                    }
                }
            }
        }
        
        // 计算统计信息
        let statistics = if success && !execution_times.is_empty() {
            self.calculate_statistics(&execution_times, &memory_usage)
        } else {
            BenchmarkStatistics {
                mean_time: Duration::ZERO,
                median_time: Duration::ZERO,
                min_time: Duration::ZERO,
                max_time: Duration::ZERO,
                std_deviation: 0.0,
                percentile_95: Duration::ZERO,
                percentile_99: Duration::ZERO,
                mean_memory: 0,
                memory_peak: 0,
                throughput_qps: 0.0,
            }
        };
        
        BenchmarkResult {
            benchmark_name: benchmark.name.clone(),
            category: benchmark.category.clone(),
            execution_times,
            memory_usage,
            statistics,
            success,
            error_message,
            timestamp: chrono::Utc::now(),
        }
    }
    
    /// 执行单次运行
    fn execute_single_run(&self, query: &LogicNode, ctx: &OptimizerContext) -> Result<(), String> {
        // 创建优化规则
        let passes: Vec<Box<dyn OptimizerPass>> = vec![
            Box::new(crate::optimizer::rules::PredicatePushdownPass::new()),
            Box::new(crate::optimizer::rules::UnionLiftingPass::new()),
            Box::new(crate::optimizer::rules::LeftToInnerJoinPass::new()),
        ];
        
        // 克隆查询以避免修改原始查询
        let mut optimized_query = query.clone();
        
        // 应用优化
        for pass in &passes {
            pass.apply(&mut optimized_query, ctx);
        }
        
        // 生成 SQL
        let mut generator = EnhancedSqlGenerator::new();
        let _sql = generator.generate(&optimized_query);
        
        Ok(())
    }
    
    /// 计算统计信息
    fn calculate_statistics(&self, times: &[Duration], memory: &[usize]) -> BenchmarkStatistics {
        if times.is_empty() {
            return BenchmarkStatistics {
                mean_time: Duration::ZERO,
                median_time: Duration::ZERO,
                min_time: Duration::ZERO,
                max_time: Duration::ZERO,
                std_deviation: 0.0,
                percentile_95: Duration::ZERO,
                percentile_99: Duration::ZERO,
                mean_memory: 0,
                memory_peak: 0,
                throughput_qps: 0.0,
            };
        }
        
        let mut sorted_times: Vec<Duration> = times.to_vec();
        sorted_times.sort();
        
        let mean_time = times.iter().sum::<Duration>() / times.len() as u32;
        let median_time = sorted_times[sorted_times.len() / 2];
        let min_time = sorted_times[0];
        let max_time = sorted_times[sorted_times.len() - 1];
        
        // 计算标准差
        let mean_time_secs = mean_time.as_secs_f64();
        let variance: f64 = times.iter()
            .map(|t| {
                let diff = t.as_secs_f64() - mean_time_secs;
                diff * diff
            })
            .sum::<f64>() / times.len() as f64;
        let std_deviation = variance.sqrt();
        
        // 计算百分位数
        let percentile_95 = sorted_times[(sorted_times.len() as f64 * 0.95) as usize];
        let percentile_99 = sorted_times[(sorted_times.len() as f64 * 0.99) as usize];
        
        // 内存统计
        let mean_memory = if memory.is_empty() { 0 } else {
            memory.iter().sum::<usize>() / memory.len()
        };
        let memory_peak = memory.iter().max().copied().unwrap_or(0);
        
        // 吞吐量 (QPS)
        let throughput_qps = if mean_time.as_secs_f64() > 0.0 {
            1.0 / mean_time.as_secs_f64()
        } else {
            0.0
        };
        
        BenchmarkStatistics {
            mean_time,
            median_time,
            min_time,
            max_time,
            std_deviation,
            percentile_95,
            percentile_99,
            mean_memory,
            memory_peak,
            throughput_qps,
        }
    }
    
    /// 获取内存使用量
    fn get_memory_usage(&self) -> usize {
        // 简化版本：返回模拟的内存使用量
        // 在实际实现中，可以使用系统调用获取真实内存使用量
        use std::collections::HashMap;
        let mut map = HashMap::new();
        map.insert("dummy", "value");
        map.len() * 8 // 模拟内存使用
    }
    
    /// 创建默认优化上下文
    fn create_default_context(&self) -> OptimizerContext {
        OptimizerContext {
            mappings: Arc::new(crate::mapping::MappingStore {
                classes: HashMap::new(),
                properties: HashMap::new(),
                mappings: HashMap::new(),
            }),
            metadata: HashMap::new(),
            stats: crate::optimizer::Statistics::default(),
        }
    }
    
    /// 打印基准测试结果
    fn print_benchmark_result(&self, result: &BenchmarkResult) {
        if result.success {
            println!("✅ {} - {:?}", result.benchmark_name, result.category);
            println!("   Mean: {:.2}ms", result.statistics.mean_time.as_secs_f64() * 1000.0);
            println!("   Median: {:.2}ms", result.statistics.median_time.as_secs_f64() * 1000.0);
            println!("   StdDev: {:.2}ms", result.statistics.std_deviation * 1000.0);
            println!("   Memory: {}KB", result.statistics.mean_memory / 1024);
            println!("   Throughput: {:.2} QPS", result.statistics.throughput_qps);
        } else {
            println!("❌ {} - FAILED", result.benchmark_name);
            if let Some(msg) = &result.error_message {
                println!("   Error: {}", msg);
            }
        }
        println!();
    }
    
    /// 生成性能报告
    pub fn generate_report(&self) -> BenchmarkReport {
        let mut successful_results = Vec::new();
        let mut failed_results = Vec::new();
        
        for result in &self.results {
            if result.success {
                successful_results.push(result.clone());
            } else {
                failed_results.push(result.clone());
            }
        }
        
        let overall_stats = self.calculate_overall_statistics(&successful_results);
        
        BenchmarkReport {
            total_benchmarks: self.benchmarks.len(),
            successful_benchmarks: successful_results.len(),
            failed_benchmarks: failed_results.len(),
            overall_statistics: overall_stats,
            category_breakdown: self.calculate_category_breakdown(&successful_results),
            results: self.results.clone(),
            generated_at: chrono::Utc::now(),
        }
    }
    
    /// 计算总体统计信息
    fn calculate_overall_statistics(&self, results: &[BenchmarkResult]) -> OverallStatistics {
        if results.is_empty() {
            return OverallStatistics {
                total_execution_time: Duration::ZERO,
                average_throughput: 0.0,
                total_memory_usage: 0,
                fastest_benchmark: String::new(),
                slowest_benchmark: String::new(),
                most_memory_intensive: String::new(),
            };
        }
        
        let total_execution_time: Duration = results.iter()
            .map(|r| r.statistics.mean_time)
            .sum();
        
        let average_throughput: f64 = results.iter()
            .map(|r| r.statistics.throughput_qps)
            .sum::<f64>() / results.len() as f64;
        
        let total_memory_usage: usize = results.iter()
            .map(|r| r.statistics.mean_memory)
            .sum::<usize>() / results.len();
        
        let fastest_benchmark = results.iter()
            .min_by_key(|r| r.statistics.mean_time)
            .map(|r| r.benchmark_name.clone())
            .unwrap_or_default();
        
        let slowest_benchmark = results.iter()
            .max_by_key(|r| r.statistics.mean_time)
            .map(|r| r.benchmark_name.clone())
            .unwrap_or_default();
        
        let most_memory_intensive = results.iter()
            .max_by_key(|r| r.statistics.mean_memory)
            .map(|r| r.benchmark_name.clone())
            .unwrap_or_default();
        
        OverallStatistics {
            total_execution_time,
            average_throughput,
            total_memory_usage,
            fastest_benchmark,
            slowest_benchmark,
            most_memory_intensive,
        }
    }
    
    /// 计算类别分解
    fn calculate_category_breakdown(&self, results: &[BenchmarkResult]) -> HashMap<BenchmarkCategory, CategoryStats> {
        let mut breakdown = HashMap::new();
        
        for result in results {
            let entry = breakdown.entry(result.category.clone()).or_insert_with(|| CategoryStats {
                count: 0,
                total_time: Duration::ZERO,
                average_time: Duration::ZERO,
                total_memory: 0,
                average_memory: 0,
            });
            
            entry.count += 1;
            entry.total_time += result.statistics.mean_time;
            entry.total_memory += result.statistics.mean_memory;
        }
        
        // 计算平均值
        for stats in breakdown.values_mut() {
            if stats.count > 0 {
                stats.average_time = stats.total_time / stats.count as u32;
                stats.average_memory = stats.total_memory / stats.count;
            }
        }
        
        breakdown
    }
    
    /// 保存结果到文件
    pub fn save_results(&self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let report = self.generate_report();
        let json = serde_json::to_string_pretty(&report)?;
        std::fs::write(filename, json)?;
        Ok(())
    }
    
    /// 从文件加载结果
    pub fn load_results(&mut self, filename: &str) -> Result<(), Box<dyn std::error::Error>> {
        let json = std::fs::read_to_string(filename)?;
        let report: BenchmarkReport = serde_json::from_str(&json)?;
        self.results = report.results;
        Ok(())
    }
}

/// 基准测试报告
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkReport {
    pub total_benchmarks: usize,
    pub successful_benchmarks: usize,
    pub failed_benchmarks: usize,
    pub overall_statistics: OverallStatistics,
    pub category_breakdown: HashMap<BenchmarkCategory, CategoryStats>,
    pub results: Vec<BenchmarkResult>,
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

/// 总体统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverallStatistics {
    pub total_execution_time: Duration,
    pub average_throughput: f64,
    pub total_memory_usage: usize,
    pub fastest_benchmark: String,
    pub slowest_benchmark: String,
    pub most_memory_intensive: String,
}

/// 类别统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryStats {
    pub count: usize,
    pub total_time: Duration,
    pub average_time: Duration,
    pub total_memory: usize,
    pub average_memory: usize,
}

impl Default for BenchmarkSuite {
    fn default() -> Self {
        Self::new()
    }
}
