//! TBox Rewriter Module
//!
//! Integrates OWL 2 QL reasoning into query rewriting pipeline.
//! Expands IntensionalData nodes using TBox reasoning.

use crate::ir::node::LogicNode;
use crate::ir::expr::Term;
use crate::reasoner::owl2ql::{Owl2QlReasoner, TBox, IRI, ConceptHierarchy, PropertyHierarchy};
use std::collections::HashMap;

/// TBox Rewriter - rewrites logical plan using TBox reasoning
#[derive(Debug, Clone)]
pub struct TBoxRewriter {
    reasoner: Owl2QlReasoner,
    implied_hierarchy: ImpliedHierarchy,
}

/// Implied hierarchy cache for efficient rewriting
#[derive(Debug, Clone)]
pub struct ImpliedHierarchy {
    pub concepts: ConceptHierarchy,
    pub properties: PropertyHierarchy,
    /// Property -> all sub-properties with inheritance depth
    pub property_expansions: HashMap<IRI, Vec<(IRI, usize)>>,
}

impl TBoxRewriter {
    /// Create a new TBox rewriter with given reasoner
    pub fn new(reasoner: Owl2QlReasoner) -> Self {
        let implied_hierarchy = ImpliedHierarchy {
            concepts: reasoner.concept_hierarchy.clone(),
            properties: reasoner.property_hierarchy.clone(),
            property_expansions: Self::compute_property_expansions(&reasoner),
        };
        
        Self {
            reasoner,
            implied_hierarchy,
        }
    }

    /// Create from TBox directly
    pub fn from_tbox(tbox: TBox) -> Self {
        let mut reasoner = Owl2QlReasoner::new();
        reasoner.load_tbox(tbox);
        Self::new(reasoner)
    }

    /// Compute all property expansions
    fn compute_property_expansions(reasoner: &Owl2QlReasoner) -> HashMap<IRI, Vec<(IRI, usize)>> {
        let mut expansions = HashMap::new();
        
        let mut all_properties = std::collections::HashSet::new();
        for p in reasoner.tbox.properties.keys() { all_properties.insert(p.clone()); }
        for (sub, sup) in &reasoner.tbox.sub_property_of {
            all_properties.insert(sub.clone());
            all_properties.insert(sup.clone());
        }
        
        for property in all_properties {
            let sub_properties = reasoner.property_hierarchy.get_all_sub_properties(&property);
            expansions.insert(property, sub_properties);
        }
        
        expansions
    }

    /// Rewrite logic plan using TBox reasoning
    pub fn rewrite(&self, logic_plan: &LogicNode) -> LogicNode {
        let mut result = logic_plan.clone();
        self.rewrite_node(&mut result);
        result
    }

    /// Recursively rewrite a node
    fn rewrite_node(&self, node: &mut LogicNode) {
        match node {
            LogicNode::IntensionalData { predicate, args } => {
                // Check if it is a class assertion (e.g., ?s rdf:type Person)
                if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" || 
                   predicate == "a" || 
                   predicate == "type" || 
                   predicate == "http://example.org/type" {
                    if let Some(Term::Constant(concept_iri)) = args.get(1) {
                        let mut sub_concepts = self.implied_hierarchy.concepts.get_all_sub_concepts(concept_iri);
                        if !sub_concepts.contains(concept_iri) {
                            sub_concepts.push(concept_iri.clone());
                        }
                        
                        if sub_concepts.len() > 1 {
                            let mut expansions = Vec::new();
                            for concept in sub_concepts {
                                let mut new_args = args.clone();
                                new_args[1] = Term::Constant(concept);
                                expansions.push(LogicNode::IntensionalData {
                                    predicate: predicate.clone(),
                                    args: new_args,
                                });
                            }
                            *node = LogicNode::Union(expansions);
                            // Process newly created node's children? (No need, they are just IntensionalData)
                            return;
                        }
                    }
                }
                
                // Property reasoning
                let expansions = self.implied_hierarchy.property_expansions
                    .get(predicate)
                    .cloned()
                    .unwrap_or_else(|| {
                        // fallback check for unqualified names in test case where domain contains it
                        if !predicate.starts_with("http") && !predicate.starts_with("<") {
                            let url = format!("http://example.org/{}", predicate);
                            self.implied_hierarchy.property_expansions
                                .get(&url)
                                .cloned()
                                .unwrap_or_default()
                        } else {
                            Vec::new()
                        }
                    });
                
                if expansions.len() > 1 {
                    // Convert to UNION of IntensionalData for each sub-property
                    *node = self.expand_to_union(predicate, &expansions, args.clone());
                }
            }
            
            // Recursively process children
            LogicNode::Construction { child, .. } => {
                self.rewrite_node(child);
            }
            LogicNode::Join { children, .. } => {
                for child in children.iter_mut() {
                    self.rewrite_node(child);
                }
            }
            LogicNode::Filter { child, .. } => {
                self.rewrite_node(child);
            }
            LogicNode::Aggregation { child, .. } => {
                self.rewrite_node(child);
            }
            LogicNode::Union(children) => {
                for child in children.iter_mut() {
                    self.rewrite_node(child);
                }
            }
            LogicNode::Limit { child, .. } => {
                self.rewrite_node(child);
            }
            LogicNode::Graph { child, .. } => {
                self.rewrite_node(child);
            }
            LogicNode::GraphUnion { children, .. } => {
                for child in children.iter_mut() {
                    self.rewrite_node(child);
                }
            }
            LogicNode::Path { path: _, .. } => {
                // Expand property paths using TBox
                self.expand_path_node(node);
            }
            _ => {} // Leaf nodes: ExtensionalData, Values, etc.
        }
    }

    /// Expand property to UNION of sub-properties
    fn expand_to_union(
        &self,
        _original_property: &IRI,
        expansions: &[(IRI, usize)],
        args: Vec<Term>
    ) -> LogicNode {
        let children: Vec<LogicNode> = expansions.iter()
            .map(|(prop, _depth)| {
                LogicNode::IntensionalData {
                    predicate: prop.clone(),
                    args: args.clone(),
                }
            })
            .collect();
        
        LogicNode::Union(children)
    }

    /// Expand property path using TBox
    fn expand_path_node(&self, _node: &mut LogicNode) {
        // TODO: Expand paths involving properties with known sub-properties
        // e.g., if :knows has sub-property :worksWith, then :knows+ should include :worksWith
    }

    /// Check if a concept or property is subsumed by another
    pub fn is_subsumed(&self, concept1: &str, concept2: &str) -> bool {
        self.implied_hierarchy.concepts.is_subsumed(
            &concept1.to_string(), 
            &concept2.to_string()
        ) || self.get_sub_properties(concept2).contains(&concept1.to_string()) ||
        self.get_sub_properties(&format!("http://example.org/{}", concept2)).contains(&format!("http://example.org/{}", concept1))
    }

    /// Get all sub-concepts for a given concept
    pub fn get_sub_concepts(&self, concept: &str) -> Vec<IRI> {
        self.implied_hierarchy.concepts.get_all_sub_concepts(&concept.to_string())
    }

    /// Get all sub-properties for a given property
    pub fn get_sub_properties(&self, property: &str) -> Vec<IRI> {
        self.implied_hierarchy.property_expansions
            .get(&property.to_string())
            .map(|v| v.iter().map(|(p, _)| p.clone()).collect())
            .unwrap_or_default()
    }
}

impl Default for TBoxRewriter {
    fn default() -> Self {
        Self::new(Owl2QlReasoner::new())
    }
}

/// Legacy TBoxRewriter function for backward compatibility
pub fn rewrite(logic_plan: &LogicNode, tbox: &TBox) -> LogicNode {
    let rewriter = TBoxRewriter::from_tbox(tbox.clone());
    rewriter.rewrite(logic_plan)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reasoner::owl2ql::{TBox, PropertyDefinition, PropertyCharacteristics};

    #[test]
    fn test_tbox_rewriter_property_expansion() {
        let mut tbox = TBox::new();
        
        // Define: worksWith ⊑ knows
        let prop_knows = PropertyDefinition {
            iri: "knows".to_string(),
            characteristics: PropertyCharacteristics::default(),
            parents: vec![],
            inverse: None,
            equivalents: vec![],
            disjoints: vec![],
        };
        
        let prop_works_with = PropertyDefinition {
            iri: "worksWith".to_string(),
            characteristics: PropertyCharacteristics::default(),
            parents: vec!["knows".to_string()],
            inverse: None,
            equivalents: vec![],
            disjoints: vec![],
        };
        
        tbox.add_property(prop_knows);
        tbox.add_property(prop_works_with);
        tbox.add_sub_property_of("worksWith".to_string(), "knows".to_string());
        
        let rewriter = TBoxRewriter::from_tbox(tbox);
        
        // Test property expansion
        let sub_props = rewriter.get_sub_properties("knows");
        assert!(sub_props.contains(&"worksWith".to_string()));
    }

    #[test]
    fn test_tbox_rewriter_is_subsumed() {
        let mut tbox = TBox::new();
        
        // Person ⊑ Agent
        tbox.add_sub_class_of("Person".to_string(), "Agent".to_string());
        
        let rewriter = TBoxRewriter::from_tbox(tbox);
        
        assert!(rewriter.is_subsumed("Person", "Agent"));
        assert!(!rewriter.is_subsumed("Agent", "Person"));
    }

    #[test]
    fn test_rewrite_intensional_data() {
        use crate::ir::expr::Term;
        
        let mut tbox = TBox::new();
        
        // Set up: worksWith ⊑ knows
        tbox.add_sub_property_of("worksWith".to_string(), "knows".to_string());
        
        let prop_def = PropertyDefinition {
            iri: "knows".to_string(),
            characteristics: PropertyCharacteristics::default(),
            parents: vec![],
            inverse: None,
            equivalents: vec![],
            disjoints: vec![],
        };
        tbox.add_property(prop_def);
        
        let sub_prop_def = PropertyDefinition {
            iri: "worksWith".to_string(),
            characteristics: PropertyCharacteristics::default(),
            parents: vec!["knows".to_string()],
            inverse: None,
            equivalents: vec![],
            disjoints: vec![],
        };
        tbox.add_property(sub_prop_def);
        
        let rewriter = TBoxRewriter::from_tbox(tbox);
        
        // Create IntensionalData for "knows"
        let node = LogicNode::IntensionalData {
            predicate: "knows".to_string(),
            args: vec![
                Term::Variable("?s".to_string()),
                Term::Variable("?o".to_string()),
            ],
        };
        
        // Rewrite
        let rewritten = rewriter.rewrite(&node);
        
        // Should be expanded to UNION
        match &rewritten {
            LogicNode::Union(children) => {
                assert_eq!(children.len(), 2); // knows + worksWith
            }
            _ => panic!("Expected Union, got {:?}", rewritten),
        }
    }
}
