use tiny_http::{Header, Request, Response, StatusCode};

use crate::error::OntopError;
use crate::listener::database::streaming_client::{StreamingResultSet, StreamingRow};

/// Buffered streaming response helper.
///
/// tiny_http does not expose a straightforward streaming writer API in this codebase,
/// so we keep chunk-by-chunk assembly and flush once at end_stream.
#[derive(Debug)]
pub struct ChunkedResponse {
    request: Option<Request>,
    body: String,
    headers_sent: bool,
    ended: bool,
}

#[derive(Debug)]
pub struct SparqlResultFormatter {
    has_written: bool,
}

impl ChunkedResponse {
    pub fn new(request: Request) -> Self {
        Self {
            request: Some(request),
            body: String::new(),
            headers_sent: false,
            ended: false,
        }
    }

    pub fn with_chunk_size(self, _chunk_size: usize) -> Self {
        self
    }

    pub fn start_stream(&mut self) -> Result<(), OntopError> {
        self.headers_sent = true;
        Ok(())
    }

    pub fn write_sparql_head(&mut self, vars: &[String]) -> Result<(), OntopError> {
        self.ensure_headers_sent()?;
        let var_json = serde_json::to_string(vars)?;
        self.body
            .push_str(&format!("{{\"head\":{{\"vars\":{}}},\"results\":{{\"bindings\":[", var_json));
        Ok(())
    }

    pub fn write_result_set(&mut self, result_set: &StreamingResultSet) -> Result<(), OntopError> {
        self.ensure_headers_sent()?;
        let mut formatter = SparqlResultFormatter::new();
        for row in result_set.rows() {
            if formatter.should_use_comma() {
                self.body.push(',');
            }
            self.body.push_str(&self.format_sparql_binding(row)?);
            formatter.mark_row_written();
        }
        Ok(())
    }

    pub fn write_sparql_tail(&mut self) -> Result<(), OntopError> {
        self.ensure_headers_sent()?;
        self.body.push_str("]}}");
        Ok(())
    }

    pub fn write_chunk(&mut self, data: &str) -> Result<(), OntopError> {
        self.ensure_headers_sent()?;
        self.body.push_str(data);
        Ok(())
    }

    pub fn write_error(&mut self, error: &OntopError) -> Result<(), OntopError> {
        self.ensure_headers_sent()?;
        self.body = format!("{{\"error\":\"{}\"}}", error);
        self.end_stream()
    }

    pub fn end_stream(&mut self) -> Result<(), OntopError> {
        if self.ended {
            return Ok(());
        }
        self.ended = true;

        if let Some(request) = self.request.take() {
            let response = Response::from_string(self.body.clone())
                .with_status_code(StatusCode(200))
                .with_header(
                    Header::from_bytes(
                        &b"Content-Type"[..],
                        &b"application/sparql-results+json; charset=utf-8"[..],
                    )
                    .map_err(|_| OntopError::HttpError("invalid response header".to_string()))?,
                );
            request
                .respond(response)
                .map_err(|e| OntopError::HttpError(e.to_string()))?;
        }
        Ok(())
    }

    fn ensure_headers_sent(&mut self) -> Result<(), OntopError> {
        if !self.headers_sent {
            self.start_stream()?;
        }
        Ok(())
    }

    fn format_sparql_binding(&self, row: &StreamingRow) -> Result<String, OntopError> {
        let mut binding = serde_json::Map::new();
        for (col_name, col_value) in row.iter_columns() {
            if let Some(value) = col_value {
                binding.insert(
                    col_name.clone(),
                    serde_json::json!({
                        "type": "literal",
                        "value": value,
                    }),
                );
            }
        }
        serde_json::to_string(&serde_json::Value::Object(binding)).map_err(OntopError::from)
    }
}

impl SparqlResultFormatter {
    pub fn new() -> Self {
        Self { has_written: false }
    }

    fn should_use_comma(&self) -> bool {
        self.has_written
    }

    fn mark_row_written(&mut self) {
        self.has_written = true;
    }
}

impl Drop for ChunkedResponse {
    fn drop(&mut self) {
        if self.headers_sent && !self.ended {
            let _ = self.end_stream();
        }
    }
}

#[derive(Debug)]
pub struct ChunkedResponseBuilder;

impl ChunkedResponseBuilder {
    pub fn new() -> Self {
        Self
    }

    pub fn build(self, request: Request) -> ChunkedResponse {
        ChunkedResponse::new(request)
    }
}

impl Default for ChunkedResponseBuilder {
    fn default() -> Self {
        Self::new()
    }
}
