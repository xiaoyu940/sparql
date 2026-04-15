use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use rio_turtle::{TurtleParser, TurtleError};
use rio_api::parser::{TriplesParser};
use rio_api::model::{Term, Subject};

/// Property types as defined in OWL 2.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum PropertyType {
    Object,
    Datatype,
}

/// Metadata about an Ontology Class (TBox).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OntologyClass {
    pub iri: String,
    pub label: Option<String>,
    pub comment: Option<String>,
    pub parent_classes: Vec<String>,
}

/// Metadata about an Ontology Property (TBox).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OntologyProperty {
    pub iri: String,
    pub label: Option<String>,
    pub comment: Option<String>,
    pub prop_type: PropertyType,
    pub is_functional: bool,
    pub domain: Option<String>,
    pub range: Option<String>,
    pub parent_properties: Vec<String>,
    pub inverse_of: Option<String>,
}

impl OntologyProperty {
    pub fn default_for(iri: String) -> Self {
        Self {
            iri, label: None, comment: None, prop_type: PropertyType::Datatype,
            is_functional: false, domain: None, range: None, parent_properties: vec![], inverse_of: None,
        }
    }
}

/// Mapping: Defines how a logic predicate relates to a physical table (ABox).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MappingRule {
    pub predicate: String,
    pub table_name: String,
    pub subject_template: Option<String>,
    pub position_to_column: HashMap<usize, String>,
}

/// Stores the whole TBox and its mappings.
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct MappingStore {
    pub classes: HashMap<String, OntologyClass>,
    pub properties: HashMap<String, OntologyProperty>,
    pub mappings: HashMap<String, Vec<MappingRule>>, // 改为 Vec 以支持多个映射
}

impl MappingStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert_mapping(&mut self, rule: MappingRule) {
        self.mappings.entry(rule.predicate.clone()).or_insert_with(Vec::new).push(rule);
    }

    pub fn add_class(&mut self, class: OntologyClass) {
        self.classes.insert(class.iri.clone(), class);
    }

    pub fn add_property(&mut self, prop: OntologyProperty) {
        self.properties.insert(prop.iri.clone(), prop);
    }

    /// High-level Turtle Loader: Parses W3C Turtle and populates TBox.
    pub fn load_turtle(&mut self, ttl: &str) -> anyhow::Result<()> {
        let mut parser = TurtleParser::new(ttl.as_bytes(), None);
        parser.parse_all(&mut |triple| {
            let s = match triple.subject {
                Subject::NamedNode(n) => n.iri.to_string(),
                _ => return Ok(()),
            };
            let p = triple.predicate.iri;
            let o = triple.object;

            match p {
                // Class Definitions
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" => {
                    if let Term::NamedNode(n) = o {
                        match n.iri {
                            "http://www.w3.org/2002/07/owl#Class" => {
                                self.classes.entry(s.clone()).or_insert_with(|| OntologyClass {
                                   iri: s, label: None, comment: None, parent_classes: vec![]
                                });
                            },
                            "http://www.w3.org/2002/07/owl#ObjectProperty" => {
                                let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                                prop.prop_type = PropertyType::Object;
                            },
                            "http://www.w3.org/2002/07/owl#DatatypeProperty" => {
                                let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                                prop.prop_type = PropertyType::Datatype;
                            },
                            "http://www.w3.org/2002/07/owl#FunctionalProperty" => {
                                let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                                prop.is_functional = true;
                            },
                            _ => {}
                        }
                    }
                },
                // Hierarchy
                "http://www.w3.org/2000/01/rdf-schema#subClassOf" => {
                    if let Term::NamedNode(n) = o {
                        let entry = self.classes.entry(s.clone()).or_insert_with(|| OntologyClass {
                            iri: s, label: None, comment: None, parent_classes: vec![]
                        });
                        entry.parent_classes.push(n.iri.to_string());
                    }
                },
                // Annotations
                "http://www.w3.org/2000/01/rdf-schema#label" => {
                    if let Term::Literal(l) = o {
                        let raw_label = l.to_string();
                        let label = raw_label.trim_matches('\"').to_string();
                        
                        if let Some(c) = self.classes.get_mut(&s) { c.label = Some(label.clone()); }
                        if let Some(pr) = self.properties.get_mut(&s) { pr.label = Some(label); }
                    }
                },
                "http://www.w3.org/2000/01/rdf-schema#comment" => {
                    if let Term::Literal(l) = o {
                        let raw_comment = l.to_string();
                        let comment = raw_comment.trim_matches('\"').to_string();
                        
                        if let Some(c) = self.classes.get_mut(&s) { c.comment = Some(comment.clone()); }
                        if let Some(pr) = self.properties.get_mut(&s) { pr.comment = Some(comment); }
                    }
                },
                // Domain/Range
                "http://www.w3.org/2000/01/rdf-schema#domain" => {
                    if let Term::NamedNode(n) = o {
                        let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                        prop.domain = Some(n.iri.to_string());
                    }
                },
                "http://www.w3.org/2000/01/rdf-schema#range" => {
                    if let Term::NamedNode(n) = o {
                        let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                        prop.range = Some(n.iri.to_string());
                    }
                },
                "http://www.w3.org/2000/01/rdf-schema#subPropertyOf" => {
                    if let Term::NamedNode(n) = o {
                        let prop = self
                            .properties
                            .entry(s.clone())
                            .or_insert_with(|| OntologyProperty::default_for(s.clone()));
                        prop.parent_properties.push(n.iri.to_string());
                    }
                },
                "http://www.w3.org/2002/07/owl#inverseOf" => {
                    if let Term::NamedNode(n) = o {
                        let prop = self.properties.entry(s.clone()).or_insert_with(|| OntologyProperty::default_for(s.clone()));
                        prop.inverse_of = Some(n.iri.to_string());
                    }
                },
                _ => {}
            }
            Ok::<(), TurtleError>(())
        })?;
        Ok(())
    }
}


pub mod manager_v2;
pub mod metadata;
pub mod cache;
pub mod r2rml_parser;
pub mod r2rml_loader;

pub use manager_v2::*;
pub use r2rml_parser::*;
pub use r2rml_loader::*;


