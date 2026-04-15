use std::fmt;
use serde::{Serialize, Deserialize};
use crate::parser::sparql_parser_v2::TriplePattern;

/// RDF Term, which could be a constant (IRI/Literal) or a variable.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Term {
    Variable(String),
    Constant(String),
    Literal {
        value: String,
        datatype: Option<String>,
        language: Option<String>,
    },
    Column {
        table: String,
        column: String,
    },
    BlankNode(String),
}

impl fmt::Display for Term {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Term::Variable(v) => write!(f, "?{}", v),
            Term::Constant(c) => write!(f, "<{}>", c),
            Term::Literal { value, datatype, language } => {
                if let Some(lang) = language {
                    write!(f, "\"{}\"@{}", value.escape_default(), lang)
                } else if let Some(dt) = datatype {
                    write!(f, "\"{}\"^^{}", value.escape_default(), dt)
                } else {
                    write!(f, "\"{}\"", value.escape_default())
                }
            }
            Term::Column { table, column } => write!(f, "{}.{}", table, column),
            Term::BlankNode(b) => write!(f, "_:{}", b),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum ComparisonOp {
    Eq, Neq, Lt, Lte, Gt, Gte, In, NotIn,
}

impl fmt::Display for ComparisonOp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ComparisonOp::Eq => write!(f, "="),
            ComparisonOp::Neq => write!(f, "<>"),
            ComparisonOp::Lt => write!(f, "<"),
            ComparisonOp::Lte => write!(f, "<="),
            ComparisonOp::Gt => write!(f, ">"),
            ComparisonOp::Gte => write!(f, ">="),
            ComparisonOp::In => write!(f, "IN"),
            ComparisonOp::NotIn => write!(f, "NOT IN"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum LogicalOp {
    And, Or, Not,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum ArithmeticOp {
    Add, Sub, Mul, Div,
}

impl fmt::Display for ArithmeticOp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ArithmeticOp::Add => write!(f, "+"),
            ArithmeticOp::Sub => write!(f, "-"),
            ArithmeticOp::Mul => write!(f, "*"),
            ArithmeticOp::Div => write!(f, "/"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Expr {
    Term(Term),
    Compare {
        left: Box<Expr>,
        op: ComparisonOp,
        right: Box<Expr>,
    },
    Logical {
        op: LogicalOp,
        args: Vec<Expr>,
    },
    Function {
        name: String,
        args: Vec<Expr>,
    },
    Arithmetic {
        left: Box<Expr>,
        op: ArithmeticOp,
        right: Box<Expr>,
    },
    /// EXISTS subquery expression - stores triple patterns for lazy SQL generation
    Exists {
        patterns: Vec<TriplePattern>,
        correlated_vars: Vec<String>,
        filters: Vec<String>,
    },
    /// NOT EXISTS subquery expression
    NotExists {
        patterns: Vec<TriplePattern>,
        correlated_vars: Vec<String>,
        filters: Vec<String>,
    },
}

impl fmt::Display for Expr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Expr::Term(t) => write!(f, "{}", t),
            Expr::Compare { left, op, right } => write!(f, "{} {} {}", left, op, right),
            Expr::Logical { op, args } => {
                let op_str = match op {
                    LogicalOp::And => " AND ",
                    LogicalOp::Or => " OR ",
                    LogicalOp::Not => "NOT ",
                };
                if matches!(op, LogicalOp::Not) {
                    write!(f, "NOT ({})", args[0])
                } else {
                    let parts: Vec<String> = args.iter().map(|a| a.to_string()).collect();
                    write!(f, "({})", parts.join(op_str))
                }
            }
            Expr::Function { name, args } => {
                let parts: Vec<String> = args.iter().map(|a| a.to_string()).collect();
                write!(f, "{}({})", name, parts.join(", "))
            }
            Expr::Arithmetic { left, op, right } => {
                write!(f, "({} {} {})", left, op, right)
            }
            Expr::Exists { patterns, .. } => {
                write!(f, "EXISTS ({} patterns)", patterns.len())
            }
            Expr::NotExists { patterns, .. } => {
                write!(f, "NOT EXISTS ({} patterns)", patterns.len())
            }
        }
    }
}
