use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Debug, Default)]
pub struct MetricsRegistry {
    pub translated_queries: AtomicU64,
    pub failed_translations: AtomicU64,
}

impl MetricsRegistry {
    pub fn inc_translated(&self) { self.translated_queries.fetch_add(1, Ordering::Relaxed); }
    pub fn inc_failed(&self) { self.failed_translations.fetch_add(1, Ordering::Relaxed); }
}
