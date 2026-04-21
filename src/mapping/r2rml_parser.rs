use crate::mapping::{MappingRule, MappingStore};
use rio_api::model::{NamedNode, Subject, Term, Triple};
use rio_api::parser::TriplesParser;
use rio_turtle::{TurtleError, TurtleParser};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum R2RmlError {
    #[error("Parse error: {0}")]
    ParseError(#[from] TurtleError),
    #[error("Invalid R2RML: {0}")]
    InvalidR2Rml(String),
}

/// LogicalTable representation in R2RML
#[derive(Debug, Clone, Default)]
pub struct R2RmlLogicalTable {
    pub table_name: Option<String>,
    pub sql_query: Option<String>,
}

/// SubjectMap representation
#[derive(Debug, Clone, Default)]
pub struct R2RmlSubjectMap {
    pub template: Option<String>,
    pub column: Option<String>,
    pub class: Vec<String>,
}

/// ObjectMap representation
#[derive(Debug, Clone, Default)]
pub struct R2RmlObjectMap {
    pub column: Option<String>,
    pub template: Option<String>,
    pub constant: Option<String>,
}

/// PredicateObjectMap representation
#[derive(Debug, Clone)]
pub struct R2RmlPredicateObjectMap {
    pub predicates: Vec<String>,
    pub object_maps: Vec<R2RmlObjectMap>,
}

/// TriplesMap representation in R2RML
#[derive(Debug, Clone, Default)]
pub struct R2RmlTriplesMap {
    pub iri: String,
    pub logical_table: R2RmlLogicalTable,
    pub subject_map: R2RmlSubjectMap,
    pub predicate_object_maps: Vec<R2RmlPredicateObjectMap>,
}

pub trait MappingConverter {
    fn to_internal_mapping(&self) -> Result<Vec<MappingRule>, R2RmlError>;
}

impl MappingConverter for R2RmlTriplesMap {
    fn to_internal_mapping(&self) -> Result<Vec<MappingRule>, R2RmlError> {
        let table_name = self.logical_table.table_name.clone().unwrap_or_else(|| {
            self.logical_table.sql_query.clone().unwrap_or_default()
        });

        if table_name.is_empty() {
            return Err(R2RmlError::InvalidR2Rml("TriplesMap lacks a valid rr:tableName or rr:sqlQuery".into()));
        }

        let mut rules = Vec::new();

        // 1. Convert rr:class assertions in the SubjectMap
        for _class_iri in &self.subject_map.class {
            let position_to_column = HashMap::new();
            // If the subject is built from a column, we wouldn't easily store it in position_to_column unless we adapt MappingRule.
            // For now, RS Ontop Core's MappingRule uses `subject_template` to format the subject.
            
            rules.push(MappingRule {
                predicate: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type".to_string(),
                table_name: table_name.clone(),
                subject_template: self.subject_map.template.clone().or(self.subject_map.column.clone()),
                object_constant: Some(_class_iri.clone()),
                position_to_column,
                // Notice: In the current design, the object of a class assertion is known (the class),
                // the `position_to_column` is empty, which implies we should either adapt MappingRule to store `object_constant`, 
                // or we rely on the TBox query unrolling.
            });
        }

        // 2. Convert each PredicateObjectMap
        for pom in &self.predicate_object_maps {
            for pred in &pom.predicates {
                for obj_map in &pom.object_maps {
                    let mut position_to_column = HashMap::new();
                    
                    if let Some(col) = &obj_map.column {
                        // Position 1 means the Object
                        position_to_column.insert(1, col.clone());
                    }

                    rules.push(MappingRule {
                        predicate: pred.clone(),
                        table_name: table_name.clone(),
                        subject_template: self.subject_map.template.clone().or(self.subject_map.column.clone()),
                        object_constant: None,
                        position_to_column,
                    });
                }
            }
        }

        Ok(rules)
    }
}

/// Parses an R2RML file in Turtle format and returns all TriplesMaps
pub fn parse_r2rml(ttl_content: &str) -> Result<Vec<R2RmlTriplesMap>, R2RmlError> {
    let mut parser = TurtleParser::new(ttl_content.as_bytes(), None);
    
    // As Turtle is parsed triple by triple, we must gather properties into an intermediate structure.
    let mut triples_maps: HashMap<String, R2RmlTriplesMap> = HashMap::new();
    
    // Intermediate maps for blank nodes or nested resources
    let mut _logical_tables: HashMap<String, R2RmlLogicalTable> = HashMap::new();
    let mut _subject_maps: HashMap<String, R2RmlSubjectMap> = HashMap::new();
    let mut _obj_maps: HashMap<String, R2RmlObjectMap> = HashMap::new();
    
    // We will do a multi-pass or just build a graph. Given Rio reads sequentially,
    // let's just collect all triples into a basic graph structure first, then extract R2RML shapes.
    let mut graph: HashMap<String, Vec<(String, String)>> = HashMap::new();

    parser.parse_all(&mut |triple| {
        let s = extract_id(&triple.subject);
        let p = triple.predicate.iri.to_string();
        let o = extract_term_value(&triple.object);

        graph.entry(s).or_default().push((p, o));
        Ok::<_, TurtleError>(())
    })?;

    // Now extract TriplesMaps. Any subject with type rr:TriplesMap is a TriplesMap.
    for (subject_id, pairs) in &graph {
        let mut is_triples_map = false;
        for (p, o) in pairs {
            if p == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" && o == "http://www.w3.org/ns/r2rml#TriplesMap" {
                is_triples_map = true;
                break;
            }
        }

        if is_triples_map {
            let mut tm = R2RmlTriplesMap {
                iri: subject_id.clone(),
                ..Default::default()
            };

            for (p, o) in pairs {
                match p.as_str() {
                    "http://www.w3.org/ns/r2rml#logicalTable" => {
                        tm.logical_table = build_logical_table(&graph, o);
                    }
                    "http://www.w3.org/ns/r2rml#subjectMap" => {
                        tm.subject_map = build_subject_map(&graph, o);
                    }
                    "http://www.w3.org/ns/r2rml#predicateObjectMap" => {
                        tm.predicate_object_maps.push(build_pom(&graph, o));
                    }
                    _ => {}
                }
            }
            triples_maps.insert(subject_id.clone(), tm);
        }
    }

    Ok(triples_maps.into_values().collect())
}

fn extract_id(subject: &Subject) -> String {
    match subject {
        Subject::NamedNode(n) => n.iri.to_string(),
        Subject::BlankNode(b) => format!("_:{b}"),
        _ => "unknown".to_string(),
    }
}

fn extract_term_value(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => n.iri.to_string(),
        Term::BlankNode(b) => format!("_:{b}"),
        Term::Literal(l) => {
            // Rio's display wraps string literals in quotes, we want the raw string here
            match l {
                rio_api::model::Literal::Simple { value } => value.to_string(),
                rio_api::model::Literal::LanguageTaggedString { value, .. } => value.to_string(),
                rio_api::model::Literal::Typed { value, .. } => value.to_string(),
            }
        }
        _ => "unknown".to_string(),
    }
}

fn build_logical_table(graph: &HashMap<String, Vec<(String, String)>>, node_id: &str) -> R2RmlLogicalTable {
    let mut lt = R2RmlLogicalTable::default();
    if let Some(pairs) = graph.get(node_id) {
        for (p, o) in pairs {
            if p == "http://www.w3.org/ns/r2rml#tableName" {
                lt.table_name = Some(o.clone());
            } else if p == "http://www.w3.org/ns/r2rml#sqlQuery" {
                lt.sql_query = Some(o.clone());
            }
        }
    }
    lt
}

fn build_subject_map(graph: &HashMap<String, Vec<(String, String)>>, node_id: &str) -> R2RmlSubjectMap {
    let mut sm = R2RmlSubjectMap::default();
    if let Some(pairs) = graph.get(node_id) {
        for (p, o) in pairs {
            match p.as_str() {
                "http://www.w3.org/ns/r2rml#template" => sm.template = Some(o.clone()),
                "http://www.w3.org/ns/r2rml#column" => sm.column = Some(o.clone()),
                "http://www.w3.org/ns/r2rml#class" => sm.class.push(o.clone()),
                _ => {}
            }
        }
    }
    sm
}

fn build_pom(graph: &HashMap<String, Vec<(String, String)>>, node_id: &str) -> R2RmlPredicateObjectMap {
    let mut pom = R2RmlPredicateObjectMap {
        predicates: vec![],
        object_maps: vec![],
    };
    if let Some(pairs) = graph.get(node_id) {
        for (p, o) in pairs {
            match p.as_str() {
                "http://www.w3.org/ns/r2rml#predicate" => pom.predicates.push(o.clone()),
                "http://www.w3.org/ns/r2rml#objectMap" => {
                    pom.object_maps.push(build_object_map(graph, o));
                }
                _ => {}
            }
        }
    }
    pom
}

fn build_object_map(graph: &HashMap<String, Vec<(String, String)>>, node_id: &str) -> R2RmlObjectMap {
    let mut om = R2RmlObjectMap::default();
    if let Some(pairs) = graph.get(node_id) {
        for (p, o) in pairs {
            match p.as_str() {
                "http://www.w3.org/ns/r2rml#column" => om.column = Some(o.clone()),
                "http://www.w3.org/ns/r2rml#template" => om.template = Some(o.clone()),
                "http://www.w3.org/ns/r2rml#constant" => om.constant = Some(o.clone()),
                _ => {}
            }
        }
    }
    om
}
