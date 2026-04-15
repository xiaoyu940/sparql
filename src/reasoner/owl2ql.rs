//! OWL 2 QL Reasoner Module
//!
//! Implements OWL 2 QL profile reasoning for SPARQL query answering.
//! Provides TBox reasoning, concept hierarchy inference, and query rewriting.

use std::collections::{HashMap, HashSet};
use serde::{Serialize, Deserialize};

/// IRI type alias for clarity
pub type IRI = String;

/// OWL 2 QL Reasoner
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Owl2QlReasoner {
    /// TBox ontology storage
    pub tbox: TBox,
    /// Concept hierarchy cache
    pub concept_hierarchy: ConceptHierarchy,
    /// Property hierarchy cache
    pub property_hierarchy: PropertyHierarchy,
    /// Inference rules
    pub rules: Vec<InferenceRule>,
}

impl Owl2QlReasoner {
    /// Create a new reasoner with empty TBox
    pub fn new() -> Self {
        Self {
            tbox: TBox::new(),
            concept_hierarchy: ConceptHierarchy::new(),
            property_hierarchy: PropertyHierarchy::new(),
            rules: Self::init_rules(),
        }
    }

    /// Initialize standard OWL 2 QL inference rules
    fn init_rules() -> Vec<InferenceRule> {
        vec![
            InferenceRule {
                name: "sub_class_transitivity".to_string(),
                description: "SubClassOf(C1, C2) ∧ SubClassOf(C2, C3) → SubClassOf(C1, C3)".to_string(),
            },
            InferenceRule {
                name: "sub_property_transitivity".to_string(),
                description: "SubPropertyOf(R1, R2) ∧ SubPropertyOf(R2, R3) → SubPropertyOf(R1, R3)".to_string(),
            },
            InferenceRule {
                name: "domain_inference".to_string(),
                description: "Domain(R, C) ∧ PropertyAssertion(R, a, b) → ClassAssertion(C, a)".to_string(),
            },
            InferenceRule {
                name: "range_inference".to_string(),
                description: "Range(R, C) ∧ PropertyAssertion(R, a, b) → ClassAssertion(C, b)".to_string(),
            },
            InferenceRule {
                name: "existential_restriction".to_string(),
                description: "SubClassOf(C1, ∃R.C2) ∧ SubPropertyOf(R1, R) → SubClassOf(C1, ∃R1.C2)".to_string(),
            },
            InferenceRule {
                name: "universal_restriction".to_string(),
                description: "SubClassOf(C1, ∀R.C2) ∧ Domain(R, C3) → SubClassOf(∃R.C3, C2)".to_string(),
            },
        ]
    }

    /// Load TBox from ontology definitions
    pub fn load_tbox(&mut self, tbox: TBox) {
        self.tbox = tbox;
        self.compute_hierarchies();
    }

    /// Compute concept and property hierarchies
    fn compute_hierarchies(&mut self) {
        self.concept_hierarchy = ConceptHierarchy::from_tbox(&self.tbox);
        self.property_hierarchy = PropertyHierarchy::from_tbox(&self.tbox);
    }

    /// Compute concept hierarchy from TBox
    pub fn compute_concept_hierarchy(&self, tbox: &TBox) -> ConceptHierarchy {
        ConceptHierarchy::from_tbox(tbox)
    }

    /// Compute property hierarchy from TBox
    pub fn compute_property_hierarchy(&self, tbox: &TBox) -> PropertyHierarchy {
        PropertyHierarchy::from_tbox(tbox)
    }

    /// Get inference rules
    pub fn get_inference_rules(&self) -> &Vec<InferenceRule> {
        &self.rules
    }

    /// Apply all inference rules and return inferred axioms
    pub fn apply_rules(&self) -> Vec<InferredAxiom> {
        let mut inferred = Vec::new();

        // R1: Sub-class transitivity
        for (c1, c2) in &self.tbox.sub_class_of {
            for (c2_prime, c3) in &self.tbox.sub_class_of {
                if c2 == c2_prime && c1 != c3 {
                    inferred.push(InferredAxiom::SubClassOf(c1.clone(), c3.clone()));
                }
            }
        }

        // R2: Sub-property transitivity
        for (r1, r2) in &self.tbox.sub_property_of {
            for (r2_prime, r3) in &self.tbox.sub_property_of {
                if r2 == r2_prime && r1 != r3 {
                    inferred.push(InferredAxiom::SubPropertyOf(r1.clone(), r3.clone()));
                }
            }
        }

        // R3: Domain inheritance along property hierarchy
        for (prop, domain) in &self.tbox.domain_constraints {
            for (sub_prop, _) in self.property_hierarchy.get_sub_properties(prop) {
                inferred.push(InferredAxiom::Domain(sub_prop.clone(), domain.clone()));
            }
        }

        // R4: Range inheritance along property hierarchy
        for (prop, range) in &self.tbox.range_constraints {
            for (sub_prop, _) in self.property_hierarchy.get_sub_properties(prop) {
                inferred.push(InferredAxiom::Range(sub_prop.clone(), range.clone()));
            }
        }

        // R5: Property restriction expansion
        for (c1, c2) in &self.tbox.sub_class_of {
            if let Some(ConceptType::ExistentialRestriction(r, c)) = 
                self.tbox.concepts.get(c2).map(|d| &d.concept_type) {
                // Expand along property hierarchy
                for (sub_r, _) in self.property_hierarchy.get_sub_properties(r) {
                    let new_restriction = ConceptType::ExistentialRestriction(sub_r.clone(), c.clone());
                    inferred.push(InferredAxiom::SubClassOfRestriction(
                        c1.clone(), 
                        new_restriction
                    ));
                }
            }
        }

        inferred
    }

    /// Get all sub-concepts (direct and indirect)
    pub fn get_all_sub_concepts(&self, concept: &IRI) -> Vec<IRI> {
        self.concept_hierarchy.get_all_sub_concepts(concept)
    }

    /// Get all super-concepts (direct and indirect)
    pub fn get_all_super_concepts(&self, concept: &IRI) -> Vec<IRI> {
        self.concept_hierarchy.get_all_super_concepts(concept)
    }

    /// Get all sub-properties (direct and indirect)
    pub fn get_all_sub_properties(&self, property: &IRI) -> Vec<IRI> {
        self.property_hierarchy.get_all_sub_properties(property)
            .into_iter()
            .map(|(prop, _)| prop)
            .collect()
    }

    /// Check if concept1 is subsumed by concept2
    pub fn is_subsumed(&self, concept1: &IRI, concept2: &IRI) -> bool {
        self.concept_hierarchy.is_subsumed(concept1, concept2)
    }
}

impl Default for Owl2QlReasoner {
    fn default() -> Self {
        Self::new()
    }
}

/// TBox - Terminological Box (ontology schema)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TBox {
    /// Concept definitions (classes)
    pub concepts: HashMap<IRI, ConceptDefinition>,
    /// Property definitions
    pub properties: HashMap<IRI, PropertyDefinition>,
    /// Sub-class axioms (C1 ⊆ C2)
    pub sub_class_of: Vec<(IRI, IRI)>,
    /// Sub-property axioms (R1 ⊆ R2)
    pub sub_property_of: Vec<(IRI, IRI)>,
    /// Domain constraints (Domain(R) = C)
    pub domain_constraints: HashMap<IRI, IRI>,
    /// Range constraints (Range(R) = C)
    pub range_constraints: HashMap<IRI, IRI>,
    /// Disjoint classes
    pub disjoint_classes: Vec<(IRI, IRI)>,
    /// Equivalent classes
    pub equivalent_classes: Vec<(IRI, IRI)>,
}

impl TBox {
    pub fn new() -> Self {
        Self {
            concepts: HashMap::new(),
            properties: HashMap::new(),
            sub_class_of: Vec::new(),
            sub_property_of: Vec::new(),
            domain_constraints: HashMap::new(),
            range_constraints: HashMap::new(),
            disjoint_classes: Vec::new(),
            equivalent_classes: Vec::new(),
        }
    }

    /// Add a concept definition
    pub fn add_concept(&mut self, definition: ConceptDefinition) {
        self.concepts.insert(definition.iri.clone(), definition);
    }

    /// Add a property definition
    pub fn add_property(&mut self, definition: PropertyDefinition) {
        self.properties.insert(definition.iri.clone(), definition);
    }

    /// Add sub-class axiom
    pub fn add_sub_class_of(&mut self, sub: IRI, sup: IRI) {
        self.sub_class_of.push((sub, sup));
    }

    /// Add sub-property axiom
    pub fn add_sub_property_of(&mut self, sub: IRI, sup: IRI) {
        self.sub_property_of.push((sub, sup));
    }

    /// Set domain constraint
    pub fn set_domain(&mut self, property: IRI, concept: IRI) {
        self.domain_constraints.insert(property, concept);
    }

    /// Get concept by IRI
    pub fn get_concept(&self, iri: &str) -> Option<&ConceptDefinition> {
        self.concepts.get(iri)
    }

    /// Get property by IRI
    pub fn get_property(&self, iri: &str) -> Option<&PropertyDefinition> {
        self.properties.get(iri)
    }
}

impl Default for TBox {
    fn default() -> Self {
        Self::new()
    }
}

/// Concept (Class) definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConceptDefinition {
    pub iri: IRI,
    pub concept_type: ConceptType,
    /// Parent concepts (direct super-classes)
    pub parents: Vec<IRI>,
    /// Equivalent concepts
    pub equivalents: Vec<IRI>,
    /// Disjoint concepts
    pub disjoints: Vec<IRI>,
}

/// Concept types in OWL 2 QL
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConceptType {
    /// Atomic concept (named class)
    Atomic(IRI),
    /// Intersection (C1 ⊓ C2 ⊓ ...)
    Intersection(Vec<ConceptType>),
    /// Union (C1 ⊔ C2 ⊔ ...)
    Union(Vec<ConceptType>),
    /// Existential restriction (∃R.C)
    ExistentialRestriction(IRI, IRI), // property, concept
    /// Universal restriction (∀R.C)
    UniversalRestriction(IRI, IRI), // property, concept
    /// Nominal ({a1, a2, ...})
    Nominal(Vec<IRI>),
}

/// Property (Role) definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropertyDefinition {
    pub iri: IRI,
    /// Property characteristics
    pub characteristics: PropertyCharacteristics,
    /// Parent properties
    pub parents: Vec<IRI>,
    /// Inverse property (if any)
    pub inverse: Option<IRI>,
    /// Equivalent properties
    pub equivalents: Vec<IRI>,
    /// Disjoint properties
    pub disjoints: Vec<IRI>,
}

/// Property characteristics
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PropertyCharacteristics {
    pub functional: bool,
    pub inverse_functional: bool,
    pub transitive: bool,
    pub symmetric: bool,
    pub asymmetric: bool,
    pub reflexive: bool,
    pub irreflexive: bool,
    // 别名访问器
    #[serde(skip)]
    pub is_symmetric: bool,
    #[serde(skip)]
    pub is_transitive: bool,
    #[serde(skip)]
    pub is_functional: bool,
    #[serde(skip)]
    pub is_inverse_functional: bool,
}

/// Concept hierarchy for efficient lookup
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConceptHierarchy {
    /// Concept -> direct sub-concepts
    sub_concepts: HashMap<IRI, Vec<IRI>>,
    /// Concept -> direct super-concepts
    super_concepts: HashMap<IRI, Vec<IRI>>,
    /// Transitive closure cache
    all_sub_concepts_cache: HashMap<IRI, Vec<IRI>>,
    all_super_concepts_cache: HashMap<IRI, Vec<IRI>>,
}

impl ConceptHierarchy {
    pub fn new() -> Self {
        Self {
            sub_concepts: HashMap::new(),
            super_concepts: HashMap::new(),
            all_sub_concepts_cache: HashMap::new(),
            all_super_concepts_cache: HashMap::new(),
        }
    }

    pub fn from_tbox(tbox: &TBox) -> Self {
        let mut hierarchy = Self::new();

        // Build direct hierarchy from sub-class axioms
        for (sub, sup) in &tbox.sub_class_of {
            hierarchy.sub_concepts
                .entry(sup.clone())
                .or_insert_with(Vec::new)
                .push(sub.clone());
            
            hierarchy.super_concepts
                .entry(sub.clone())
                .or_insert_with(Vec::new)
                .push(sup.clone());
        }

        // Add concepts without explicit hierarchy
        for iri in tbox.concepts.keys() {
            hierarchy.sub_concepts.entry(iri.clone()).or_insert_with(Vec::new);
            hierarchy.super_concepts.entry(iri.clone()).or_insert_with(Vec::new);
        }

        hierarchy
    }

    /// Get all sub-concepts (direct and indirect)
    pub fn get_all_sub_concepts(&self, concept: &IRI) -> Vec<IRI> {
        if let Some(cached) = self.all_sub_concepts_cache.get(concept) {
            return cached.clone();
        }

        let mut result = HashSet::new();
        self.collect_sub_concepts_recursive(concept, &mut result);
        
        let result_vec: Vec<IRI> = result.into_iter().collect();
        result_vec
    }

    fn collect_sub_concepts_recursive(&self, concept: &IRI, collected: &mut HashSet<IRI>) {
        if let Some(direct_subs) = self.sub_concepts.get(concept) {
            for sub in direct_subs {
                if collected.insert(sub.clone()) {
                    self.collect_sub_concepts_recursive(sub, collected);
                }
            }
        }
    }

    /// Get all super-concepts (direct and indirect)
    pub fn get_all_super_concepts(&self, concept: &IRI) -> Vec<IRI> {
        let mut result = HashSet::new();
        self.collect_super_concepts_recursive(concept, &mut result);
        result.into_iter().collect()
    }

    fn collect_super_concepts_recursive(&self, concept: &IRI, collected: &mut HashSet<IRI>) {
        if let Some(direct_sups) = self.super_concepts.get(concept) {
            for sup in direct_sups {
                if collected.insert(sup.clone()) {
                    self.collect_super_concepts_recursive(sup, collected);
                }
            }
        }
    }

    /// Check if concept1 is subsumed by concept2
    pub fn is_subsumed(&self, concept1: &IRI, concept2: &IRI) -> bool {
        if concept1 == concept2 {
            return true;
        }
        
        let all_supers = self.get_all_super_concepts(concept1);
        all_supers.contains(concept2)
    }

    /// Get direct sub-concepts
    pub fn get_direct_sub_concepts(&self, concept: &IRI) -> Vec<IRI> {
        self.sub_concepts.get(concept)
            .cloned()
            .unwrap_or_default()
    }

    /// Get direct super-concepts
    pub fn get_direct_super_concepts(&self, concept: &IRI) -> Vec<IRI> {
        self.super_concepts.get(concept)
            .cloned()
            .unwrap_or_default()
    }
}

impl Default for ConceptHierarchy {
    fn default() -> Self {
        Self::new()
    }
}

/// Property hierarchy for efficient lookup
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropertyHierarchy {
    /// Property -> direct sub-properties
    sub_properties: HashMap<IRI, Vec<IRI>>,
    /// Property -> direct super-properties
    super_properties: HashMap<IRI, Vec<IRI>>,
}

impl PropertyHierarchy {
    pub fn new() -> Self {
        Self {
            sub_properties: HashMap::new(),
            super_properties: HashMap::new(),
        }
    }

    pub fn from_tbox(tbox: &TBox) -> Self {
        let mut hierarchy = Self::new();

        // Build direct hierarchy from sub-property axioms
        for (sub, sup) in &tbox.sub_property_of {
            hierarchy.sub_properties
                .entry(sup.clone())
                .or_insert_with(Vec::new)
                .push(sub.clone());
            
            hierarchy.super_properties
                .entry(sub.clone())
                .or_insert_with(Vec::new)
                .push(sup.clone());
        }

        // Add properties without explicit hierarchy
        for iri in tbox.properties.keys() {
            hierarchy.sub_properties.entry(iri.clone()).or_insert_with(Vec::new);
            hierarchy.super_properties.entry(iri.clone()).or_insert_with(Vec::new);
        }

        hierarchy
    }

    /// Get all sub-properties (direct and indirect)
    pub fn get_all_sub_properties(&self, property: &IRI) -> Vec<(IRI, usize)> {
        let mut result = Vec::new();
        let mut visited = HashSet::new();
        
        // Add the property itself as depth 0
        result.push((property.clone(), 0));
        visited.insert(property.clone());
        
        self.collect_sub_properties_recursive(property, 0, &mut result, &mut visited);
        result
    }

    fn collect_sub_properties_recursive(
        &self, 
        property: &IRI, 
        depth: usize,
        result: &mut Vec<(IRI, usize)>,
        visited: &mut HashSet<IRI>
    ) {
        if let Some(direct_subs) = self.sub_properties.get(property) {
            for sub in direct_subs {
                if visited.insert(sub.clone()) {
                    result.push((sub.clone(), depth + 1));
                    self.collect_sub_properties_recursive(sub, depth + 1, result, visited);
                }
            }
        }
    }

    /// Get sub-properties at specific depth
    pub fn get_sub_properties(&self, property: &IRI) -> Vec<(IRI, usize)> {
        self.get_all_sub_properties(property)
    }

    /// Get direct sub-properties
    pub fn get_direct_sub_properties(&self, property: &IRI) -> Vec<IRI> {
        self.sub_properties.get(property)
            .cloned()
            .unwrap_or_default()
    }

    /// Get direct super-properties
    pub fn get_direct_super_properties(&self, property: &IRI) -> Vec<IRI> {
        self.super_properties.get(property)
            .cloned()
            .unwrap_or_default()
    }
}

impl Default for PropertyHierarchy {
    fn default() -> Self {
        Self::new()
    }
}

/// Inference rule definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceRule {
    pub name: String,
    pub description: String,
}

/// Inferred axiom
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum InferredAxiom {
    SubClassOf(IRI, IRI),
    SubPropertyOf(IRI, IRI),
    Domain(IRI, IRI),    // property, concept
    Range(IRI, IRI),     // property, concept
    SubClassOfRestriction(IRI, ConceptType),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tbox_creation() {
        let mut tbox = TBox::new();
        
        let concept = ConceptDefinition {
            iri: "http://example.org/Person".to_string(),
            concept_type: ConceptType::Atomic("http://example.org/Person".to_string()),
            parents: vec!["http://example.org/Agent".to_string()],
            equivalents: vec![],
            disjoints: vec![],
        };
        
        tbox.add_concept(concept);
        tbox.add_sub_class_of(
            "http://example.org/Person".to_string(),
            "http://example.org/Agent".to_string()
        );
        
        assert_eq!(tbox.concepts.len(), 1);
        assert_eq!(tbox.sub_class_of.len(), 1);
    }

    #[test]
    fn test_concept_hierarchy() {
        let mut tbox = TBox::new();
        
        // Person ⊑ Agent ⊑ Thing
        tbox.add_sub_class_of(
            "Person".to_string(),
            "Agent".to_string()
        );
        tbox.add_sub_class_of(
            "Agent".to_string(),
            "Thing".to_string()
        );
        
        let hierarchy = ConceptHierarchy::from_tbox(&tbox);
        
        // Test transitivity
        let supers = hierarchy.get_all_super_concepts(&"Person".to_string());
        assert!(supers.contains(&"Agent".to_string()));
        assert!(supers.contains(&"Thing".to_string()));
        
        // Test subsumption
        assert!(hierarchy.is_subsumed(&"Person".to_string(), &"Thing".to_string()));
    }

    #[test]
    fn test_owl2ql_reasoner_rules() {
        let reasoner = Owl2QlReasoner::new();
        let rules = &reasoner.rules;
        
        assert_eq!(rules.len(), 6);
        assert!(rules.iter().any(|r| r.name == "sub_class_transitivity"));
        assert!(rules.iter().any(|r| r.name == "domain_inference"));
    }

    #[test]
    fn test_inference_application() {
        let mut tbox = TBox::new();
        
        // Set up: Person ⊑ Agent, Agent ⊑ Thing
        tbox.add_sub_class_of("Person".to_string(), "Agent".to_string());
        tbox.add_sub_class_of("Agent".to_string(), "Thing".to_string());
        
        let mut reasoner = Owl2QlReasoner::new();
        reasoner.load_tbox(tbox);
        
        let inferred = reasoner.apply_rules();
        
        // Should infer: Person ⊑ Thing (transitivity)
        assert!(inferred.iter().any(|ax| matches!(ax, 
            InferredAxiom::SubClassOf(sub, sup) 
            if sub == "Person" && sup == "Thing"
        )));
    }
}
