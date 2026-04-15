use crate::benchmark::benchmark_suite::{Benchmark, BenchmarkCategory, ComplexityLevel};
use crate::ir::node::{LogicNode, JoinType};
use crate::ir::expr::{Expr, Term, ComparisonOp, LogicalOp};
use std::collections::HashMap;
use std::sync::Arc;

// ============================================
// 表名常量 - 避免硬编码 (规则1)
// ============================================
const TABLE_USERS: &str = "users";
const TABLE_DEPARTMENTS: &str = "departments";
const TABLE_COMPANIES: &str = "companies";
const TABLE_SALES: &str = "sales";
const TABLE_TRANSACTIONS: &str = "transactions";

// ============================================
// 列名常量 - 避免硬编码 (规则2)
// ============================================
const COL_ID: &str = "id";
const COL_NAME: &str = "name";
const COL_EMAIL: &str = "email";
const COL_AGE: &str = "age";
const COL_SALARY: &str = "salary";
const COL_DEPT_ID: &str = "dept_id";
const COL_COMPANY_ID: &str = "company_id";
const COL_PRODUCT_ID: &str = "product_id";
const COL_AMOUNT: &str = "amount";
const COL_DATE: &str = "date";
const COL_REGION: &str = "region";
const COL_TYPE: &str = "type";
const COL_STATUS: &str = "status";
const COL_INDUSTRY: &str = "industry";
const COL_YEAR: &str = "year";

/// 创建标准基准测试套件
pub fn create_standard_benchmark_suite() -> Vec<Benchmark> {
    let mut benchmarks = Vec::new();
    
    // 简单查询基准测试
    benchmarks.push(create_simple_table_scan_benchmark());
    benchmarks.push(create_simple_filter_benchmark());
    benchmarks.push(create_simple_projection_benchmark());
    
    // JOIN 优化基准测试
    benchmarks.push(create_two_table_join_benchmark());
    benchmarks.push(create_multi_table_join_benchmark());
    benchmarks.push(create_complex_join_benchmark());
    
    // 过滤器优化基准测试
    benchmarks.push(create_multiple_filters_benchmark());
    benchmarks.push(create_complex_filter_benchmark());
    benchmarks.push(create_nested_filter_benchmark());
    
    // 聚合基准测试
    benchmarks.push(create_simple_aggregation_benchmark());
    benchmarks.push(create_group_by_benchmark());
    benchmarks.push(create_complex_aggregation_benchmark());
    
    // UNION 优化基准测试
    benchmarks.push(create_simple_union_benchmark());
    benchmarks.push(create_complex_union_benchmark());
    
    // 复杂查询基准测试
    benchmarks.push(create_complex_query_benchmark());
    benchmarks.push(create_stress_test_benchmark());
    
    benchmarks
}

/// 简单表扫描基准测试
fn create_simple_table_scan_benchmark() -> Benchmark {
    Benchmark {
        name: "Simple Table Scan".to_string(),
        description: "Basic table scan with no filters".to_string(),
        category: BenchmarkCategory::SimpleQuery,
        query_generator: Box::new(|| {
            LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_EMAIL])),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Low,
    }
}

/// 简单过滤器基准测试
fn create_simple_filter_benchmark() -> Benchmark {
    Benchmark {
        name: "Simple Filter".to_string(),
        description: "Single equality filter".to_string(),
        category: BenchmarkCategory::FilterOptimization,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_EMAIL])),
            };
            
            LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("1".to_string()))),
                    op: ComparisonOp::Eq,
                },
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Low,
    }
}

/// 简单投影基准测试
fn create_simple_projection_benchmark() -> Benchmark {
    Benchmark {
        name: "Simple Projection".to_string(),
        description: "Basic column projection".to_string(),
        category: BenchmarkCategory::SimpleQuery,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_EMAIL])),
            };
            
            LogicNode::Construction {
                projected_vars: vec![COL_NAME.to_string(), COL_EMAIL.to_string()],
                bindings: HashMap::new(),
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Low,
    }
}

/// 两表 JOIN 基准测试
fn create_two_table_join_benchmark() -> Benchmark {
    Benchmark {
        name: "Two Table Join".to_string(),
        description: "Inner join between two tables".to_string(),
        category: BenchmarkCategory::JoinOptimization,
        query_generator: Box::new(|| {
            let users_table = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_DEPT_ID])),
            };
            
            let departments_table = LogicNode::ExtensionalData {
                table_name: TABLE_DEPARTMENTS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_DEPARTMENTS, vec![COL_ID, COL_NAME])),
            };
            
            LogicNode::Join {
                children: vec![users_table, departments_table],
                condition: Some(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_DEPT_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    op: ComparisonOp::Eq,
                }),
                join_type: JoinType::Inner,
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Medium,
    }
}

/// 多表 JOIN 基准测试
fn create_multi_table_join_benchmark() -> Benchmark {
    Benchmark {
        name: "Multi Table Join".to_string(),
        description: "Join across multiple tables".to_string(),
        category: BenchmarkCategory::JoinOptimization,
        query_generator: Box::new(|| {
            let users_table = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_DEPT_ID])),
            };
            
            let departments_table = LogicNode::ExtensionalData {
                table_name: TABLE_DEPARTMENTS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_DEPARTMENTS, vec![COL_ID, COL_NAME, COL_COMPANY_ID])),
            };
            
            let companies_table = LogicNode::ExtensionalData {
                table_name: TABLE_COMPANIES.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_COMPANIES, vec![COL_ID, COL_NAME])),
            };
            
            let join1 = LogicNode::Join {
                children: vec![users_table, departments_table],
                condition: Some(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_DEPT_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    op: ComparisonOp::Eq,
                }),
                join_type: JoinType::Inner,
            };
            
            LogicNode::Join {
                children: vec![join1, companies_table],
                condition: Some(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_COMPANY_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    op: ComparisonOp::Eq,
                }),
                join_type: JoinType::Inner,
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::High,
    }
}

/// 复杂 JOIN 基准测试
fn create_complex_join_benchmark() -> Benchmark {
    Benchmark {
        name: "Complex Join".to_string(),
        description: "Multiple joins with complex conditions".to_string(),
        category: BenchmarkCategory::JoinOptimization,
        query_generator: Box::new(|| {
            let table1 = create_test_table("table1", 10);
            let table2 = create_test_table("table2", 10);
            let table3 = create_test_table("table3", 10);
            let table4 = create_test_table("table4", 10);
            
            // 创建复杂的连接条件
            let complex_condition = Expr::Logical {
                op: LogicalOp::And,
                args: vec![
                    Expr::Compare {
                        left: Box::new(Expr::Term(Term::Variable("table1.id".to_string()))),
                        right: Box::new(Expr::Term(Term::Variable("table2.id".to_string()))),
                        op: ComparisonOp::Eq,
                    },
                    Expr::Compare {
                        left: Box::new(Expr::Term(Term::Variable("table2.id".to_string()))),
                        right: Box::new(Expr::Term(Term::Variable("table3.id".to_string()))),
                        op: ComparisonOp::Eq,
                    },
                    Expr::Compare {
                        left: Box::new(Expr::Term(Term::Variable("table3.id".to_string()))),
                        right: Box::new(Expr::Term(Term::Variable("table4.id".to_string()))),
                        op: ComparisonOp::Eq,
                    },
                ],
            };
            
            LogicNode::Join {
                children: vec![table1, table2, table3, table4],
                condition: Some(complex_condition),
                join_type: JoinType::Inner,
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::VeryHigh,
    }
}

/// 多重过滤器基准测试
fn create_multiple_filters_benchmark() -> Benchmark {
    Benchmark {
        name: "Multiple Filters".to_string(),
        description: "Chain of filter operations".to_string(),
        category: BenchmarkCategory::FilterOptimization,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_AGE, COL_EMAIL])),
            };
            
            let filter1 = LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_AGE.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("25".to_string()))),
                    op: ComparisonOp::Gt,
                },
                child: Box::new(table_scan),
            };
            
            let filter2 = LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_NAME.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("John".to_string()))),
                    op: ComparisonOp::Eq,
                },
                child: Box::new(filter1),
            };
            
            LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_EMAIL.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("test@example.com".to_string()))),
                    op: ComparisonOp::Neq,
                },
                child: Box::new(filter2),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Medium,
    }
}

/// 复杂过滤器基准测试
fn create_complex_filter_benchmark() -> Benchmark {
    Benchmark {
        name: "Complex Filter".to_string(),
        description: "Filter with complex logical expressions".to_string(),
        category: BenchmarkCategory::FilterOptimization,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_AGE, COL_SALARY, "dept"])),
            };
            
            let complex_condition = Expr::Logical {
                op: LogicalOp::Or,
                args: vec![
                    Expr::Logical {
                        op: LogicalOp::And,
                        args: vec![
                            Expr::Compare {
                                left: Box::new(Expr::Term(Term::Variable(COL_AGE.to_string()))),
                                right: Box::new(Expr::Term(Term::Constant("30".to_string()))),
                                op: ComparisonOp::Gt,
                            },
                            Expr::Compare {
                                left: Box::new(Expr::Term(Term::Variable(COL_SALARY.to_string()))),
                                right: Box::new(Expr::Term(Term::Constant("50000".to_string()))),
                                op: ComparisonOp::Gt,
                            },
                        ],
                    },
                    Expr::Logical {
                        op: LogicalOp::And,
                        args: vec![
                            Expr::Compare {
                                left: Box::new(Expr::Term(Term::Variable("dept".to_string()))),
                                right: Box::new(Expr::Term(Term::Constant("engineering".to_string()))),
                                op: ComparisonOp::Eq,
                            },
                            Expr::Compare {
                                left: Box::new(Expr::Term(Term::Variable(COL_AGE.to_string()))),
                                right: Box::new(Expr::Term(Term::Constant("25".to_string()))),
                                op: ComparisonOp::Lt,
                            },
                        ],
                    },
                ],
            };
            
            LogicNode::Filter {
                expression: complex_condition,
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::High,
    }
}

/// 嵌套过滤器基准测试
fn create_nested_filter_benchmark() -> Benchmark {
    Benchmark {
        name: "Nested Filter".to_string(),
        description: "Deeply nested filter expressions".to_string(),
        category: BenchmarkCategory::FilterOptimization,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_TRANSACTIONS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_TRANSACTIONS, vec![COL_ID, COL_AMOUNT, COL_DATE, COL_TYPE, COL_STATUS])),
            };
            
            // 创建深度嵌套的逻辑表达式
            let nested_condition = create_nested_filter_condition(5);
            
            LogicNode::Filter {
                expression: nested_condition,
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::VeryHigh,
    }
}

/// 简单聚合基准测试
fn create_simple_aggregation_benchmark() -> Benchmark {
    Benchmark {
        name: "Simple Aggregation".to_string(),
        description: "Basic COUNT aggregation".to_string(),
        category: BenchmarkCategory::Aggregation,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_AGE])),
            };
            
            LogicNode::Aggregation { having: None,
                group_by: vec![],
                aggregates: {
                    let mut agg = HashMap::new();
                    agg.insert("count".to_string(), Expr::Function {
                        name: "COUNT".to_string(),
                        args: vec![Expr::Term(Term::Variable("*".to_string()))],
                    });
                    agg
                },
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Medium,
    }
}

/// GROUP BY 基准测试
fn create_group_by_benchmark() -> Benchmark {
    Benchmark {
        name: "Group By".to_string(),
        description: "Aggregation with GROUP BY".to_string(),
        category: BenchmarkCategory::Aggregation,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_SALES.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_SALES, vec![COL_ID, COL_PRODUCT_ID, COL_AMOUNT, COL_DATE])),
            };
            
            LogicNode::Aggregation { having: None,
                group_by: vec![COL_PRODUCT_ID.to_string()],
                aggregates: {
                    let mut agg = HashMap::new();
                    agg.insert("total_amount".to_string(), Expr::Function {
                        name: "SUM".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_AMOUNT.to_string()))],
                    });
                    agg.insert("count".to_string(), Expr::Function {
                        name: "COUNT".to_string(),
                        args: vec![Expr::Term(Term::Variable("*".to_string()))],
                    });
                    agg
                },
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::High,
    }
}

/// 复杂聚合基准测试
fn create_complex_aggregation_benchmark() -> Benchmark {
    Benchmark {
        name: "Complex Aggregation".to_string(),
        description: "Multiple aggregation functions with GROUP BY".to_string(),
        category: BenchmarkCategory::Aggregation,
        query_generator: Box::new(|| {
            let table_scan = LogicNode::ExtensionalData {
                table_name: TABLE_SALES.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_SALES, vec![COL_ID, COL_PRODUCT_ID, COL_AMOUNT, COL_DATE, COL_REGION])),
            };
            
            LogicNode::Aggregation { having: None,
                group_by: vec![COL_PRODUCT_ID.to_string(), COL_REGION.to_string()],
                aggregates: {
                    let mut agg = HashMap::new();
                    agg.insert("total_amount".to_string(), Expr::Function {
                        name: "SUM".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_AMOUNT.to_string()))],
                    });
                    agg.insert("avg_amount".to_string(), Expr::Function {
                        name: "AVG".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_AMOUNT.to_string()))],
                    });
                    agg.insert("max_amount".to_string(), Expr::Function {
                        name: "MAX".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_AMOUNT.to_string()))],
                    });
                    agg.insert("min_amount".to_string(), Expr::Function {
                        name: "MIN".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_AMOUNT.to_string()))],
                    });
                    agg
                },
                child: Box::new(table_scan),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::VeryHigh,
    }
}

/// 简单 UNION 基准测试
fn create_simple_union_benchmark() -> Benchmark {
    Benchmark {
        name: "Simple Union".to_string(),
        description: "Basic UNION operation".to_string(),
        category: BenchmarkCategory::UnionOptimization,
        query_generator: Box::new(|| {
            let table1 = LogicNode::ExtensionalData {
                table_name: "users_2022".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata("users_2022", vec![COL_ID, COL_NAME, COL_EMAIL])),
            };
            
            let table2 = LogicNode::ExtensionalData {
                table_name: "users_2023".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata("users_2023", vec![COL_ID, COL_NAME, COL_EMAIL])),
            };
            
            LogicNode::Union(vec![table1, table2])
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::Medium,
    }
}

/// 复杂 UNION 基准测试
fn create_complex_union_benchmark() -> Benchmark {
    Benchmark {
        name: "Complex Union".to_string(),
        description: "Multiple UNION operations with filters".to_string(),
        category: BenchmarkCategory::UnionOptimization,
        query_generator: Box::new(|| {
            let table1 = LogicNode::ExtensionalData {
                table_name: "users_2021".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata("users_2021", vec![COL_ID, COL_NAME, COL_EMAIL, COL_YEAR])),
            };
            
            let table2 = LogicNode::ExtensionalData {
                table_name: "users_2022".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata("users_2022", vec![COL_ID, COL_NAME, COL_EMAIL, COL_YEAR])),
            };
            
            let table3 = LogicNode::ExtensionalData {
                table_name: "users_2023".to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata("users_2023", vec![COL_ID, COL_NAME, COL_EMAIL, COL_YEAR])),
            };
            
            let filtered_table1 = LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_YEAR.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("2021".to_string()))),
                    op: ComparisonOp::Eq,
                },
                child: Box::new(table1),
            };
            
            let filtered_table2 = LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_YEAR.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("2022".to_string()))),
                    op: ComparisonOp::Eq,
                },
                child: Box::new(table2),
            };
            
            let filtered_table3 = LogicNode::Filter {
                expression: Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_YEAR.to_string()))),
                    right: Box::new(Expr::Term(Term::Constant("2023".to_string()))),
                    op: ComparisonOp::Eq,
                },
                child: Box::new(table3),
            };
            
            LogicNode::Union(vec![filtered_table1, filtered_table2, filtered_table3])
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::High,
    }
}

/// 复杂查询基准测试
fn create_complex_query_benchmark() -> Benchmark {
    Benchmark {
        name: "Complex Query".to_string(),
        description: "Complex query with joins, filters, and aggregations".to_string(),
        category: BenchmarkCategory::ComplexQuery,
        query_generator: Box::new(|| {
            let users_table = LogicNode::ExtensionalData {
                table_name: TABLE_USERS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_USERS, vec![COL_ID, COL_NAME, COL_DEPT_ID, COL_AGE, COL_SALARY])),
            };
            
            let departments_table = LogicNode::ExtensionalData {
                table_name: TABLE_DEPARTMENTS.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_DEPARTMENTS, vec![COL_ID, COL_NAME, COL_COMPANY_ID])),
            };
            
            let companies_table = LogicNode::ExtensionalData {
                table_name: TABLE_COMPANIES.to_string(),
                column_mapping: HashMap::new(),
                metadata: Arc::new(create_test_metadata(TABLE_COMPANIES, vec![COL_ID, COL_NAME, COL_INDUSTRY])),
            };
            
            // 创建复杂的查询结构
            let join1 = LogicNode::Join {
                children: vec![users_table, departments_table],
                condition: Some(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_DEPT_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    op: ComparisonOp::Eq,
                }),
                join_type: JoinType::Inner,
            };
            
            let join2 = LogicNode::Join {
                children: vec![join1, companies_table],
                condition: Some(Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(COL_COMPANY_ID.to_string()))),
                    right: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
                    op: ComparisonOp::Eq,
                }),
                join_type: JoinType::Inner,
            };
            
            let filter1 = LogicNode::Filter {
                expression: Expr::Logical {
                    op: LogicalOp::And,
                    args: vec![
                        Expr::Compare {
                            left: Box::new(Expr::Term(Term::Variable(COL_AGE.to_string()))),
                            right: Box::new(Expr::Term(Term::Constant("25".to_string()))),
                            op: ComparisonOp::Gt,
                        },
                        Expr::Compare {
                            left: Box::new(Expr::Term(Term::Variable(COL_SALARY.to_string()))),
                            right: Box::new(Expr::Term(Term::Constant("50000".to_string()))),
                            op: ComparisonOp::Gt,
                        },
                    ],
                },
                child: Box::new(join2),
            };
            
            LogicNode::Aggregation { having: None,
                group_by: vec![COL_INDUSTRY.to_string()],
                aggregates: {
                    let mut agg = HashMap::new();
                    agg.insert("avg_salary".to_string(), Expr::Function {
                        name: "AVG".to_string(),
                        args: vec![Expr::Term(Term::Variable(COL_SALARY.to_string()))],
                    });
                    agg.insert("count".to_string(), Expr::Function {
                        name: "COUNT".to_string(),
                        args: vec![Expr::Term(Term::Variable("*".to_string()))],
                    });
                    agg
                },
                child: Box::new(filter1),
            }
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::VeryHigh,
    }
}

/// 压力测试基准测试
fn create_stress_test_benchmark() -> Benchmark {
    Benchmark {
        name: "Stress Test".to_string(),
        description: "Large query for stress testing".to_string(),
        category: BenchmarkCategory::StressTest,
        query_generator: Box::new(|| {
            create_large_complex_query()
        }),
        setup_fn: None,
        expected_complexity: ComplexityLevel::VeryHigh,
    }
}

// 辅助函数

/// 创建测试表元数据
fn create_test_metadata(table_name: &str, columns: Vec<&str>) -> crate::metadata::TableMetadata {
    crate::metadata::TableMetadata {
        table_name: table_name.to_string(),
        columns: columns.iter().map(|s| s.to_string()).collect(),
        primary_keys: vec![COL_ID.to_string()],
        foreign_keys: vec![],
        unique_constraints: vec![],
        check_constraints: vec![],
        not_null_columns: columns.iter().map(|s| s.to_string()).collect(),
    }
}

/// 创建测试表
fn create_test_table(name: &str, column_count: usize) -> LogicNode {
    let columns: Vec<String> = (0..column_count).map(|i| format!("col{}", i)).collect();
    
    LogicNode::ExtensionalData {
        table_name: name.to_string(),
        column_mapping: HashMap::new(),
        metadata: Arc::new(create_test_metadata(name, columns.iter().map(|s| s.as_str()).collect())),
    }
}

/// 创建嵌套过滤器条件
fn create_nested_filter_condition(depth: usize) -> Expr {
    if depth == 0 {
        Expr::Compare {
            left: Box::new(Expr::Term(Term::Variable(COL_ID.to_string()))),
            right: Box::new(Expr::Term(Term::Constant("1".to_string()))),
            op: ComparisonOp::Eq,
        }
    } else {
        Expr::Logical {
            op: LogicalOp::And,
            args: vec![
                create_nested_filter_condition(depth - 1),
                Expr::Compare {
                    left: Box::new(Expr::Term(Term::Variable(format!("col{}", depth)))),
                    right: Box::new(Expr::Term(Term::Constant("value".to_string()))),
                    op: ComparisonOp::Eq,
                },
            ],
        }
    }
}

/// 创建大型复杂查询
fn create_large_complex_query() -> LogicNode {
    let mut tables = Vec::new();
    
    // 创建多个表
    for i in 0..10 {
        tables.push(create_test_table(&format!("table{}", i), 5));
    }
    
    // 创建多个 JOIN
    let mut current = tables.remove(0);
    for (i, table) in tables.into_iter().enumerate() {
        current = LogicNode::Join {
            children: vec![current, table],
            condition: Some(Expr::Compare {
                left: Box::new(Expr::Term(Term::Variable(format!("table{}.id", i)))),
                right: Box::new(Expr::Term(Term::Variable(format!("table{}.id", i + 1)))),
                op: ComparisonOp::Eq,
            }),
            join_type: JoinType::Inner,
        };
    }
    
    // 添加多个过滤器
    for i in 0..5 {
        current = LogicNode::Filter {
            expression: Expr::Compare {
                left: Box::new(Expr::Term(Term::Variable(format!("col{}", i)))),
                right: Box::new(Expr::Term(Term::Constant(format!("value{}", i)))),
                op: ComparisonOp::Eq,
            },
            child: Box::new(current),
        };
    }
    
    // 添加聚合
    LogicNode::Aggregation { having: None,
        group_by: vec!["col0".to_string(), "col1".to_string()],
        aggregates: {
            let mut agg = HashMap::new();
            for i in 0..3 {
                agg.insert(format!("agg{}", i), Expr::Function {
                    name: "SUM".to_string(),
                    args: vec![Expr::Term(Term::Variable(format!("col{}", i + 2)))],
                });
            }
            agg
        },
        child: Box::new(current),
    }
}
