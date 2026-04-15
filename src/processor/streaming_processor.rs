use crate::error::OntopError;
use crate::listener::database::streaming_client::StreamingResultSet;

#[derive(Debug, Default)]
pub struct StreamingProcessor;

impl StreamingProcessor {
    pub fn to_rows_json(&self, batch: &StreamingResultSet) -> Result<String, OntopError> {
        let rows: Vec<serde_json::Value> = batch
            .rows()
            .iter()
            .map(|row| {
                let mut obj = serde_json::Map::new();
                for (k, v) in row.iter_columns() {
                    obj.insert(k.clone(), serde_json::Value::String(v.clone().unwrap_or_default()));
                }
                serde_json::Value::Object(obj)
            })
            .collect();
        serde_json::to_string(&rows).map_err(OntopError::from)
    }
}
