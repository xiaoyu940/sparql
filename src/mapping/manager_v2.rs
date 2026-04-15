use std::collections::HashMap;

use crate::mapping::MappingRule;

#[derive(Debug, Default)]
pub struct MappingManagerV2 {
    mappings: HashMap<String, MappingRule>,
}

impl MappingManagerV2 {
    pub fn insert(&mut self, rule: MappingRule) {
        self.mappings.insert(rule.predicate.clone(), rule);
    }

    pub fn find_mapping(&self, predicate: &str) -> Option<&MappingRule> {
        self.mappings.get(predicate)
    }
}
