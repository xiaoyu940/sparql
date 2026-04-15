use std::collections::HashMap;

#[derive(Debug, Default)]
pub struct MappingCache {
    data: HashMap<String, String>,
}

impl MappingCache {
    pub fn put(&mut self, key: String, val: String) { self.data.insert(key, val); }
    pub fn get(&self, key: &str) -> Option<&String> { self.data.get(key) }
}
