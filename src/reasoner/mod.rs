//! OWL 2 QL Reasoner and TBox Rewriter Module
//!
//! Provides ontology reasoning capabilities for SPARQL query answering:
//! - OWL 2 QL profile reasoning
//! - TBox management and inference
//! - Query rewriting based on concept/property hierarchies

pub mod owl2ql;
pub mod tbox_rewriter;
pub mod saturator;

pub use owl2ql::{
    Owl2QlReasoner,
    TBox,
    ConceptDefinition,
    ConceptType,
    PropertyDefinition,
    PropertyCharacteristics,
    ConceptHierarchy,
    PropertyHierarchy,
    InferenceRule,
    InferredAxiom,
    IRI,
};

pub use tbox_rewriter::{
    TBoxRewriter,
    ImpliedHierarchy,
    rewrite,
};

pub use saturator::saturate_tbox;
