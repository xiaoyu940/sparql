use std::time::Duration;

use pgrx::prelude::*;

use crate::error::OntopError;

/// Flow control for batched query fetching.
#[derive(Debug)]
pub struct StreamingClient {
    batch_size: i32,
    query_timeout: Duration,
}

/// Lightweight portal abstraction backed by LIMIT/OFFSET pagination.
#[derive(Debug)]
pub struct QueryPortal {
    sql: String,
    offset: i64,
    batch_size: i32,
    is_open: bool,
}

/// Represents a batch of rows emitted by a portal.
#[derive(Debug)]
pub struct StreamingResultSet {
    rows: Vec<StreamingRow>,
    is_last_batch: bool,
    batch_index: usize,
}

/// Simplified row holder for downstream JSON formatting.
#[derive(Debug, Clone)]
pub struct StreamingRow {
    columns: Vec<(String, Option<String>)>,
    row_index: usize,
}

impl StreamingClient {
    pub fn new() -> Self {
        Self {
            batch_size: 500,
            query_timeout: Duration::from_secs(30),
        }
    }

    pub fn with_batch_size(mut self, batch_size: i32) -> Self {
        self.batch_size = batch_size.max(1);
        self
    }

    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.query_timeout = timeout;
        self
    }

    pub fn execute_streaming_sql(&mut self, sql: &str) -> Result<QueryPortal, OntopError> {
        let timeout_ms = self.query_timeout.as_millis();
        let timeout_sql = format!("SET statement_timeout = '{}ms'", timeout_ms);
        Spi::run(&timeout_sql).map_err(|e| OntopError::SQLError(e.to_string()))?;

        Ok(QueryPortal {
            sql: sql.to_string(),
            offset: 0,
            batch_size: self.batch_size,
            is_open: true,
        })
    }
}

impl QueryPortal {
    pub fn fetch(&mut self) -> Result<Option<StreamingResultSet>, OntopError> {
        if !self.is_open {
            return Ok(None);
        }

        let page_sql = format!(
            "SELECT * FROM ({}) AS __stream LIMIT {} OFFSET {}",
            self.sql, self.batch_size, self.offset
        );

        let mut rows = Vec::new();
        let expected = self.batch_size as usize;
        Spi::connect(|client| {
            let table = client
                .select(&page_sql, None, None)
                .map_err(|e| OntopError::SQLError(e.to_string()))?;
            for (idx, row) in table.into_iter().enumerate() {
                if let Some(jsonb) = row
                    .get_by_name::<pgrx::JsonB, _>("ontop_query")
                    .map_err(|e| OntopError::SQLError(e.to_string()))?
                {
                    rows.push(StreamingRow::from_json_value(jsonb.0, idx));
                }
            }
            Ok::<(), OntopError>(())
        })?;

        let is_last_batch = rows.len() < expected;
        let batch_index = (self.offset / self.batch_size as i64) as usize;
        self.offset += self.batch_size as i64;
        if is_last_batch {
            self.is_open = false;
        }

        Ok(Some(StreamingResultSet {
            rows,
            is_last_batch,
            batch_index,
        }))
    }

    pub fn close(&mut self) -> Result<(), OntopError> {
        self.is_open = false;
        Ok(())
    }

    pub fn batch_size(&self) -> i32 {
        self.batch_size
    }
}

impl StreamingResultSet {
    pub fn row_count(&self) -> usize {
        self.rows.len()
    }

    pub fn rows(&self) -> &[StreamingRow] {
        &self.rows
    }

    pub fn is_last_batch(&self) -> bool {
        self.is_last_batch
    }

    pub fn batch_index(&self) -> usize {
        self.batch_index
    }
}

impl StreamingRow {
    fn from_json_value(value: serde_json::Value, row_index: usize) -> Self {
        let mut columns = Vec::new();
        match value {
            serde_json::Value::Object(map) => {
                for (k, v) in map {
                    columns.push((k, Some(value_to_string(v))));
                }
            }
            other => {
                columns.push(("value".to_string(), Some(value_to_string(other))));
            }
        }
        Self { columns, row_index }
    }

    pub fn get_column_by_name(&self, name: &str) -> Option<&Option<String>> {
        self.columns
            .iter()
            .find(|(col_name, _)| col_name == name)
            .map(|(_, value)| value)
    }

    pub fn iter_columns(&self) -> impl Iterator<Item = (&String, &Option<String>)> {
        self.columns.iter().map(|(name, value)| (name, value))
    }

    pub fn row_index(&self) -> usize {
        self.row_index
    }
}

fn value_to_string(value: serde_json::Value) -> String {
    match value {
        serde_json::Value::Null => "null".to_string(),
        serde_json::Value::Bool(v) => v.to_string(),
        serde_json::Value::Number(v) => v.to_string(),
        serde_json::Value::String(v) => v,
        other => other.to_string(),
    }
}

impl StreamingQueryBuilder {
    pub fn new() -> Self {
        Self {
            batch_size: 500,
            timeout: Duration::from_secs(30),
        }
    }

    pub fn batch_size(mut self, size: i32) -> Self {
        self.batch_size = size;
        self
    }

    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn build(self) -> StreamingClient {
        let mut client = StreamingClient::new();
        client.batch_size = self.batch_size.max(1);
        client.query_timeout = self.timeout;
        client
    }
}

impl Default for StreamingQueryBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug)]
pub struct StreamingQueryBuilder {
    batch_size: i32,
    timeout: Duration,
}
