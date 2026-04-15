use std::collections::HashMap;
use crate::ir::expr::{Term, Expr};
use crate::ir::node::LogicNode;

/// Substitution: Maps variables (String names) to other terms (Variables, Constants, or Literals).
#[derive(Default, Debug, Clone, PartialEq, Eq)]
pub struct Substitution {
    pub mapping: HashMap<String, Term>,
}

impl Substitution {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, variable: String, term: Term) {
        self.mapping.insert(variable, term);
    }

    pub fn get(&self, variable: &str) -> Option<&Term> {
        self.mapping.get(variable)
    }

    pub fn is_empty(&self) -> bool {
        self.mapping.is_empty()
    }

    /// Recursively apply the substitution to resolve a term if it's a variable.
    pub fn resolve_term(&self, term: &Term) -> Term {
        match term {
            Term::Variable(v) => {
                if let Some(t) = self.get(v) {
                    // Follow the variable chain if necessary (can also be iterative).
                    self.resolve_term(t)
                } else {
                    term.clone()
                }
            }
            _ => term.clone(),
        }
    }

    /// Compose this substitution with another: s1.compose(s2) = s1 ∘ s2
    /// 1. Apply s2 to all terms in s1.
    /// 2. Add mappings from s2 that aren't in s1.
    pub fn compose(&mut self, s2: &Substitution) {
        for term in self.mapping.values_mut() {
            *term = s2.resolve_term(term);
        }
        for (var, term) in &s2.mapping {
            if !self.mapping.contains_key(var) {
                self.mapping.insert(var.clone(), term.clone());
            }
        }
    }

    /// Try to unify two terms and update this substitution.
    /// Returns true if unification succeeded.
    pub fn unify(&mut self, t1: &Term, t2: &Term) -> bool {
        let rt1 = self.resolve_term(t1);
        let rt2 = self.resolve_term(t2);

        if rt1 == rt2 {
            return true;
        }

        match (rt1, rt2) {
            (Term::Variable(v1), any) => {
                self.insert(v1, any);
                true
            }
            (any, Term::Variable(v2)) => {
                self.insert(v2, any);
                true
            }
            _ => false, // Constants or Literals that don't match
        }
    }
}

/// Trait for objects that can have a Substitution applied to them (Immutable).
pub trait ApplySubstitution {
    fn apply(&self, sub: &Substitution) -> Self;
}

/// Trait for objects that can have a Substitution applied to them in-place (Mutable).
pub trait ApplySubstitutionMut {
    fn apply_mut(&mut self, sub: &Substitution);
}

impl ApplySubstitution for Term {
    fn apply(&self, sub: &Substitution) -> Self {
        sub.resolve_term(self)
    }
}

impl ApplySubstitutionMut for Term {
    fn apply_mut(&mut self, sub: &Substitution) {
        *self = sub.resolve_term(self);
    }
}

impl ApplySubstitution for Expr {
    fn apply(&self, sub: &Substitution) -> Self {
        let mut cloned = self.clone();
        cloned.apply_mut(sub);
        cloned
    }
}

impl ApplySubstitutionMut for Expr {
    fn apply_mut(&mut self, sub: &Substitution) {
        match self {
            Expr::Term(t) => t.apply_mut(sub),
            Expr::Compare { left, right, .. } => {
                left.apply_mut(sub);
                right.apply_mut(sub);
            }
            Expr::Logical { args, .. } => {
                for arg in args {
                    arg.apply_mut(sub);
                }
            }
            Expr::Function { args, .. } => {
                for arg in args {
                    arg.apply_mut(sub);
                }
            }
            Expr::Arithmetic { left, right, .. } => {
                left.apply_mut(sub);
                right.apply_mut(sub);
            }
            Expr::Exists { .. } | Expr::NotExists { .. } => {
                // EXISTS subqueries don't need substitution at the expression level
                // The subquery SQL is already built
            }
        }
    }
}

impl ApplySubstitution for LogicNode {
    fn apply(&self, sub: &Substitution) -> Self {
        let mut cloned = self.clone();
        cloned.apply_mut(sub);
        cloned
    }
}

impl ApplySubstitutionMut for LogicNode {
    fn apply_mut(&mut self, sub: &Substitution) {
        match self {
            LogicNode::Construction {
                bindings,
                child,
                ..
            } => {
                for expr in bindings.values_mut() {
                    expr.apply_mut(sub);
                }
                child.apply_mut(sub);
            }
            LogicNode::Join {
                children,
                condition,
                ..
            } => {
                for child in children {
                    child.apply_mut(sub);
                }
                if let Some(cond) = condition {
                    cond.apply_mut(sub);
                }
            }
            LogicNode::Filter { expression, child } => {
                expression.apply_mut(sub);
                child.apply_mut(sub);
            }
            LogicNode::Union(children) => {
                for child in children {
                    child.apply_mut(sub);
                }
            }
            LogicNode::Aggregation { group_by, aggregates, child, .. } => {
                child.apply_mut(sub);
                for v_name in group_by.iter_mut() {
                    match sub.resolve_term(&Term::Variable(v_name.clone())) {
                        Term::Variable(new_v_name) => {
                            *v_name = new_v_name;
                        }
                        _ => {}
                    }
                }
                for expr in aggregates.values_mut() {
                    expr.apply_mut(sub);
                }
            }
            LogicNode::ExtensionalData {
                column_mapping,
                ..
            } => {
                let mut new_mapping = HashMap::new();
                for (var, col) in column_mapping.iter() {
                    match sub.resolve_term(&Term::Variable(var.clone())) {
                        Term::Variable(new_var) => {
                            new_mapping.insert(new_var, col.clone());
                        }
                        _ => {
                            new_mapping.insert(var.clone(), col.clone());
                        }
                    }
                }
                *column_mapping = new_mapping;
            }
            LogicNode::IntensionalData { args, .. } => {
                for arg in args {
                    arg.apply_mut(sub);
                }
            }
            LogicNode::Limit { child, .. } => {
                child.apply_mut(sub);
            }
            LogicNode::Values { variables, rows } => {
                for v_name in variables.iter_mut() {
                    match sub.resolve_term(&Term::Variable(v_name.clone())) {
                        Term::Variable(new_v_name) => {
                            *v_name = new_v_name;
                        }
                        _ => {}
                    }
                }
                for row in rows.iter_mut() {
                    for term in row.iter_mut() {
                        term.apply_mut(sub);
                    }
                }
            }
            LogicNode::Path { subject, object, .. } => {
                subject.apply_mut(sub);
                object.apply_mut(sub);
            }
            LogicNode::Graph { graph_name, child, .. } => {
                graph_name.apply_mut(sub);
                child.apply_mut(sub);
            }
            LogicNode::GraphUnion { graph_var, children } => {
                // Apply substitution to graph variable if it matches
                match sub.resolve_term(&Term::Variable(graph_var.clone())) {
                    Term::Variable(new_var) => *graph_var = new_var,
                    _ => {}
                }
                for child in children {
                    child.apply_mut(sub);
                }
            }
            LogicNode::Service { inner_plan, .. } => {
                inner_plan.apply_mut(sub);
            }
            LogicNode::SubQuery { inner, .. } => {
                inner.apply_mut(sub);
            }
            LogicNode::CorrelatedJoin { outer, inner, condition } => {
                outer.apply_mut(sub);
                inner.apply_mut(sub);
                condition.apply_mut(sub);
            }
            LogicNode::RecursivePath { base_path, recursive_path, subject, object, .. } => {
                base_path.apply_mut(sub);
                recursive_path.apply_mut(sub);
                subject.apply_mut(sub);
                object.apply_mut(sub);
            }
        }
    }
}
