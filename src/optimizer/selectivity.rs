//! Selectivity Estimator 
//!
//! Estimates filter selective fraction [0.0, 1.0] over expressions using 
//! base statistics. Used by DPSize and Cost Model.

use crate::optimizer::statistics::{TableStatistics, Statistics};
use crate::ir::expr::{Expr, Term, ComparisonOp, LogicalOp};

pub trait SelectivityEstimator {
    fn estimate_eq(&self, column: &str, value: &Term) -> f64;
    fn estimate_range(&self, column: &str, low: &Term, high: &Term) -> f64;
    fn estimate_like(&self, column: &str, pattern: &str) -> f64;
    fn estimate_expr(&self, expr: &Expr) -> f64;
}

pub struct BasicSelectivityEstimator<'a> {
    pub table_stats: Option<&'a TableStatistics>,
    pub global_stats: &'a Statistics,
}

impl<'a> BasicSelectivityEstimator<'a> {
    pub fn new(table_stats: Option<&'a TableStatistics>, global_stats: &'a Statistics) -> Self {
        Self { table_stats, global_stats }
    }

    fn extract_str(&self, term: &Term) -> String {
        match term {
            Term::Constant(c) | Term::Variable(c) | Term::BlankNode(c) => c.clone(),
            Term::Literal { value, .. } => value.clone(),
            Term::Column { table, column } => format!("{}.{}", table, column),
        }
    }
}

impl<'a> SelectivityEstimator for BasicSelectivityEstimator<'a> {
    fn estimate_eq(&self, column: &str, value: &Term) -> f64 {
        if let Some(ts) = self.table_stats {
            if let Some(col_stats) = ts.column_stats.get(column) {
                let val_str = self.extract_str(value);

                // 1. Check Most Common Values (MCV)
                for (mcv, freq) in &col_stats.most_common_values {
                    if mcv == &val_str {
                        return *freq;
                    }
                }

                // 2. Fallback to uniform distribution over the remaining distinct values
                let remaining_freq = 1.0 - col_stats.null_fraction - col_stats.most_common_values.iter().map(|(_, f)| f).sum::<f64>();
                let distinct_used = col_stats.most_common_values.len() as f64;
                let total_distinct = (col_stats.distinct_values as f64).max(1.0);
                
                let remaining_distinct = total_distinct - distinct_used;
                
                if remaining_distinct > 0.0 {
                    return (remaining_freq / remaining_distinct).max(0.0001);
                } else {
                    return 0.01;
                }
            }
        }
        // Default magic number for equality if no stats
        0.1
    }

    fn estimate_range(&self, _column: &str, _low: &Term, _high: &Term) -> f64 {
        // Simple magic number since histogram-based range scanning needs more logic.
        0.3 
    }

    fn estimate_like(&self, _column: &str, _pattern: &str) -> f64 {
        0.05
    }

    fn estimate_expr(&self, expr: &Expr) -> f64 {
        match expr {
            Expr::Compare { left, op, right } => {
                let (col_opt, term_opt) = match (left.as_ref(), right.as_ref()) {
                    (Expr::Term(Term::Variable(v)), Expr::Term(t)) => (Some(v.clone()), Some(t)),
                    (Expr::Term(t), Expr::Term(Term::Variable(v))) => (Some(v.clone()), Some(t)),
                    _ => (None, None),
                };

                match op {
                    ComparisonOp::Eq => {
                        if let (Some(col), Some(term)) = (col_opt, term_opt) {
                            self.estimate_eq(&col, term)
                        } else {
                            0.1 // join selectivity default
                        }
                    }
                    ComparisonOp::Lt | ComparisonOp::Lte | ComparisonOp::Gt | ComparisonOp::Gte => 0.33,
                    ComparisonOp::Neq => 0.9,
                    ComparisonOp::In => 0.5,
                    ComparisonOp::NotIn => 0.8,
                }
            }
            Expr::Logical { op, args } => {
                match op {
                    LogicalOp::And => args.iter().map(|a| self.estimate_expr(a)).fold(1.0, |acc, sel| acc * sel),
                    LogicalOp::Or => {
                        let mut fail_prob = 1.0;
                        for a in args {
                            fail_prob *= 1.0 - self.estimate_expr(a);
                        }
                        1.0 - fail_prob
                    }
                    LogicalOp::Not => 1.0 - self.estimate_expr(&args[0]),
                }
            }
            _ => 1.0, // Default to returning all rows
        }
    }
}
