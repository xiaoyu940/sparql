//! TBox Saturator for DL-Lite_R
//! 
//! Applies standard OWL 2 QL / DL-Lite inference rules to compute a saturated TBox,
//! ensuring completeness of reasoning during query rewriting.

use std::collections::HashSet;
use crate::reasoner::owl2ql::{IRI, TBox};

/// Produces a new saturated TBox containing all inferred axioms.
/// Implements R1 - R7 rules.
pub fn saturate_tbox(tbox: &TBox) -> TBox {
    let mut saturated = tbox.clone();
    let mut changed = true;

    // Helper: generate inverse property IRI convention
    fn inv(iri: &str) -> String {
        if iri.starts_with("INV_") {
            iri["INV_".len()..].to_string()
        } else {
            format!("INV_{}", iri)
        }
    }

    // Helper: extract existential restrictions (we treat Domain/Range as existentials internally for saturation)
    // Domain(R) = C => ∃R ⊑ C
    // Range(R) = C  => ∃inv(R) ⊑ C
    // This allows us to map existentials to regular subclass arrays using a prefix convention `∃_R`
    fn exist(iri: &str) -> String {
        format!("∃_{}", iri)
    }

    // Initialize existentials from Domain and Range
    for (prop, domain) in &tbox.domain_constraints {
        saturated.sub_class_of.push((exist(prop), domain.clone()));
    }
    for (prop, range) in &tbox.range_constraints {
        let inverse_prop = inv(prop);
        saturated.sub_class_of.push((exist(&inverse_prop), range.clone())); // ∃inv(R) ⊑ C
    }

    // Expand initial inverses from symmetric and explicit inversion
    for (prop, def) in &tbox.properties {
        if let Some(ref inverse) = def.inverse {
            saturated.sub_property_of.push((inv(prop), inverse.clone()));
            saturated.sub_property_of.push((inverse.clone(), inv(prop)));
        }
    }

    // Remove duplicates helper
    let deduplicate = |vec: &mut Vec<(IRI, IRI)>| {
        let set: HashSet<_> = vec.drain(..).collect();
        vec.extend(set);
    };

    while changed {
        changed = false;
        let mut new_sub_classes = Vec::new();
        let mut new_sub_props = Vec::new();

        // Ensure current structures are distinct to optimize looping
        deduplicate(&mut saturated.sub_class_of);
        deduplicate(&mut saturated.sub_property_of);

        let sub_classes = &saturated.sub_class_of;
        let sub_props = &saturated.sub_property_of;

        // R1, R2, R3 (Transitivity over classes and existentials)
        // If X ⊑ Y and Y ⊑ Z => X ⊑ Z
        for (x, y) in sub_classes {
            for (y_prime, z) in sub_classes {
                if y == y_prime && x != z {
                    // Check if already exists
                    if !sub_classes.contains(&(x.clone(), z.clone())) && !new_sub_classes.contains(&(x.clone(), z.clone())) {
                        new_sub_classes.push((x.clone(), z.clone()));
                        changed = true;
                    }
                }
            }
        }

        // R4: Property Subsumption Transitivity
        // P ⊑ Q, Q ⊑ R => P ⊑ R
        for (p, q) in sub_props {
            for (q_prime, r) in sub_props {
                if q == q_prime && p != r {
                    if !sub_props.contains(&(p.clone(), r.clone())) && !new_sub_props.contains(&(p.clone(), r.clone())) {
                        new_sub_props.push((p.clone(), r.clone()));
                        changed = true;
                    }
                }
            }
        }

        // Apply R7 (Inverse properties correlation)
        // If P ⊑ Q => inv(P) ⊑ inv(Q)
        for (p, q) in sub_props {
            let inv_p = inv(p);
            let inv_q = inv(q);
            if !sub_props.contains(&(inv_p.clone(), inv_q.clone())) && !new_sub_props.contains(&(inv_p.clone(), inv_q.clone())) {
                new_sub_props.push((inv_p.clone(), inv_q.clone()));
                changed = true;
            }
        }

        // Apply existentials expansion based on property inheritance (implicit R5, R6)
        // If P ⊑ Q, then ∃P ⊑ ∃Q and ∃inv(P) ⊑ ∃inv(Q)
        for (p, q) in sub_props {
            let exist_p = exist(p);
            let exist_q = exist(q);
            if !sub_classes.contains(&(exist_p.clone(), exist_q.clone())) && !new_sub_classes.contains(&(exist_p.clone(), exist_q.clone())) {
                new_sub_classes.push((exist_p.clone(), exist_q.clone()));
                changed = true;
            }

            let exist_inv_p = exist(&inv(p));
            let exist_inv_q = exist(&inv(q));
            if !sub_classes.contains(&(exist_inv_p.clone(), exist_inv_q.clone())) && !new_sub_classes.contains(&(exist_inv_p.clone(), exist_inv_q.clone())) {
                new_sub_classes.push((exist_inv_p.clone(), exist_inv_q.clone()));
                changed = true;
            }
        }

        // Append new facts
        if !new_sub_classes.is_empty() {
            saturated.sub_class_of.extend(new_sub_classes);
        }
        if !new_sub_props.is_empty() {
            saturated.sub_property_of.extend(new_sub_props);
        }
    }

    // Optionally extract the new domain and range constraints from the saturated existentials
    // A ⊑ B where A is ∃R and B is a regular class (not ∃) indicates a domain/range constraint
    for (sub, sup) in &saturated.sub_class_of {
        if sub.starts_with("∃_") && !sup.starts_with("∃_") {
            let prop_part = &sub["∃_".len()..];
            if prop_part.starts_with("INV_") {
                let actual_prop = &prop_part["INV_".len()..];
                saturated.range_constraints.insert(actual_prop.to_string(), sup.clone());
            } else {
                saturated.domain_constraints.insert(prop_part.to_string(), sup.clone());
            }
        }
    }

    saturated
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_saturation_subsumption_transitivity() {
        let mut tbox = TBox::new();
        // A ⊑ B, B ⊑ C
        tbox.add_sub_class_of("A".to_string(), "B".to_string());
        tbox.add_sub_class_of("B".to_string(), "C".to_string());
        
        let saturated = saturate_tbox(&tbox);
        assert!(saturated.sub_class_of.contains(&("A".to_string(), "C".to_string())));
    }

    #[test]
    fn test_saturation_domain_inheritance_r5() {
        let mut tbox = TBox::new();
        // worksWith ⊑ knows
        tbox.add_sub_property_of("worksWith".to_string(), "knows".to_string());
        // Domain(knows) = Person
        tbox.set_domain("knows".to_string(), "Person".to_string());
        
        let saturated = saturate_tbox(&tbox);
        // By R5, Domain(worksWith) = Person
        assert_eq!(saturated.domain_constraints.get("worksWith"), Some(&"Person".to_string()));
    }

    #[test]
    fn test_saturation_range_inheritance_r6() {
        let mut tbox = TBox::new();
        tbox.add_sub_property_of("managedBy".to_string(), "associatedWith".to_string());
        tbox.range_constraints.insert("associatedWith".to_string(), "Organization".to_string());
        
        let saturated = saturate_tbox(&tbox);
        assert_eq!(saturated.range_constraints.get("managedBy"), Some(&"Organization".to_string()));
    }

    #[test]
    fn test_saturation_inverse_properties() {
        let mut tbox = TBox::new();
        tbox.add_sub_property_of("manages".to_string(), "knows".to_string());
        
        let saturated = saturate_tbox(&tbox);
        let manages_inv = "INV_manages".to_string();
        let knows_inv = "INV_knows".to_string();
        
        assert!(saturated.sub_property_of.contains(&(manages_inv, knows_inv)));
    }
}
