use std::collections::{HashMap, HashSet};

#[derive(Debug, Default)]
pub struct AliasManagerV2 {
    used: HashSet<String>,
    map: HashMap<String, String>,
}

impl AliasManagerV2 {
    pub fn allocate(&mut self, table_name: &str) -> String {
        if let Some(a) = self.map.get(table_name) {
            return a.clone();
        }

        let base = table_name
            .chars()
            .filter(|c| c.is_ascii_alphabetic())
            .take(3)
            .collect::<String>()
            .to_lowercase();
        let base = if base.is_empty() { "t" } else { &base };

        let mut alias = base.to_string();
        let mut idx = 1;
        while self.used.contains(&alias) {
            alias = format!("{}_{}", base, idx);
            idx += 1;
        }

        self.used.insert(alias.clone());
        self.map.insert(table_name.to_string(), alias.clone());
        alias
    }
}
