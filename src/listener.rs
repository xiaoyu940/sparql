use pgrx::bgworkers::*;
use pgrx::prelude::*;
use regex::Regex;
use std::time::Duration;
use tiny_http::{Header, Method, Response, Server, StatusCode};
use url::Url;

use crate::ir::builder::IRBuilder;
use crate::ir::node::LogicNode;
use crate::parser::SparqlParserV2;
use crate::sql::flat_generator::FlatSQLGenerator;
use crate::ENGINE;

pub mod database;
pub mod http;
pub mod robust;

#[pg_guard]
#[no_mangle]
pub extern "C-unwind" fn ontop_sparql_bgworker_main(_arg: pg_sys::Datum) {
    log!("rs-ontop-core: Starting SPARQL Gateway Background Worker");

    BackgroundWorker::attach_signal_handlers(SignalWakeFlags::SIGHUP | SignalWakeFlags::SIGTERM);
    BackgroundWorker::connect_worker_to_spi(Some("rs_ontop_core"), None);

    // [CRITICAL] Initialize engine in bgworker process (ENGINE is process-local)
    log!("rs-ontop-core: Initializing engine in bgworker...");
    let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        BackgroundWorker::transaction(|| {
            Spi::connect(|mut client| {
                crate::refresh_engine_from_spi(&mut client);
                Ok::<(), pgrx::spi::SpiError>(())
            })
        })
    }));
    log!("rs-ontop-core: Engine initialization attempted in bgworker");

    let server = match Server::http("0.0.0.0:5820") {
        Ok(s) => s,
        Err(e) => {
            log!("rs-ontop-core: Failed to bind port 5820. Error: {}", e);
            return;
        }
    };

    log!("rs-ontop-core SPARQL Listener successfully bound to http://0.0.0.0:5820");

    let mut consecutive_errors = 0;
    let max_consecutive_errors = 10;

    while BackgroundWorker::wait_latch(Some(Duration::from_millis(0))) {
        pgrx::check_for_interrupts!();

        match server.recv_timeout(Duration::from_millis(100)) {
            Ok(Some(mut request)) => {
                let path = request.url().to_string();
                let method = request.method().clone();
                consecutive_errors = 0;

                  if method == Method::Options {
                      let _ = request.respond(with_cors_headers(
                          Response::from_string("")
                              .with_status_code(StatusCode(204)),
                      ));
                      continue;
                  }

                if path.starts_with("/ontology") {
                    let body = BackgroundWorker::transaction(|| {
                        Spi::get_one::<pgrx::JsonB>("SELECT ontop_inspect_ontology();")
                    });

                    match body {
                        Ok(Some(json_ld)) => {
                            let json_str = match serde_json::to_string(&json_ld.0) {
                                Ok(s) => s,
                                Err(e) => {
                                    log!("[listener] JSON serialize: Failed | Error: {}", e);
                                    let header = match tiny_http::Header::from_bytes(
                                        &b"Content-Type"[..],
                                        &b"application/json; charset=utf-8"[..],
                                    ) {
                                        Ok(h) => h,
                                        Err(e) => {
                                            log!("[listener] Header create: Failed | Error: {:?}", e);
                                            let _ = request.respond(
                                                Response::from_string("{\"error\":\"Internal server error\"}")
                                                    .with_status_code(StatusCode(500)),
                                            );
                                            continue;
                                        }
                                    };
                                    let response = Response::from_string(format!("{{\"error\":\"JSON serialization failed: {}\"}}", e))
                                        .with_header(header);
                                    let _ = request.respond(with_cors_headers(response));
                                    continue;
                                }
                            };
                            let header = match tiny_http::Header::from_bytes(
                                &b"Content-Type"[..],
                                &b"application/json; charset=utf-8"[..],
                            ) {
                                Ok(h) => h,
                                Err(e) => {
                                    log!("[listener] Header create: Failed | Error: {:?}", e);
                                    let _ = request.respond(
                                        Response::from_string("{\"error\":\"Internal server error\"}")
                                            .with_status_code(StatusCode(500)),
                                    );
                                    continue;
                                }
                            };
                            let response = Response::from_string(json_str)
                                .with_header(header);
                            let _ = request.respond(with_cors_headers(response));
                        }
                        Ok(None) => {
                            let _ = request.respond(
                                Response::from_string("{\"error\":\"Engine not initialized\"}")
                                    .with_status_code(StatusCode(503)),
                            );
                        }
                        Err(e) => {
                            let _ = request.respond(
                                Response::from_string(format!("{{\"error\":\"{}\"}}", e))
                                    .with_status_code(StatusCode(500)),
                            );
                        }
                    }
                    continue;
                }

                if path.starts_with("/sparql") {
                    let mut sparql_query = String::new();

                    if method == Method::Post {
                        let mut content = String::new();
                        let _ = request.as_reader().read_to_string(&mut content);
                        if content.starts_with("query=") {
                            let mut decoded_query = None;
                            for (k, v) in url::form_urlencoded::parse(content.as_bytes()) {
                                if k == "query" {
                                    decoded_query = Some(v.into_owned());
                                    break;
                                }
                            }
                            if let Some(q) = decoded_query {
                                sparql_query = q;
                            } else {
                                sparql_query = content;
                            }
                        } else {
                            sparql_query = content;
                        }
                    } else if method == Method::Get {
                        if let Ok(url) = Url::parse(&format!("http://localhost{}", path)) {
                            for (key, val) in url.query_pairs() {
                                if key == "query" {
                                    sparql_query = val.to_string();
                                }
                            }
                        }
                    }

                    if sparql_query.is_empty() {
                        let _ = request.respond(
                            Response::from_string("{\"error\":\"Missing query parameter\"}")
                                .with_status_code(StatusCode(400)),
                        );
                        continue;
                    }

                    log!("rs-ontop-core: [SPARQL_REQUEST_BEGIN]\n{}\n[SPARQL_REQUEST_END]", sparql_query);

                    if let Err(e) = validate_query_stability(&sparql_query) {
                        log!("rs-ontop-core: {}", e);
                        let error_response = serde_json::json!({
                            "error": e,
                            "status_code": 400,
                            "query": sparql_query
                        });
                        let _ = request.respond(with_cors_headers(
                            Response::from_string(error_response.to_string())
                                .with_status_code(StatusCode(400)),
                        ));
                        continue;
                    }

                    let sparql_for_worker = sparql_query.clone();
                    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(move || {
                        BackgroundWorker::transaction(|| execute_ontop_query(&sparql_for_worker))
                    }));

                    match result {
                        Ok(Ok(bindings)) => {
                            let out = format_sparql_response(&sparql_query, bindings);
                            let response = Response::from_string(out.to_string())
                                .with_chunked_threshold(0)
                                .with_header(
                                    tiny_http::Header::from_bytes(
                                        &b"Content-Type"[..],
                                        &b"application/sparql-results+json; charset=utf-8"[..],
                                    )
                                    .expect("should create header"),
                                );
                            let _ = request.respond(with_cors_headers(response));
                        }
                        Ok(Err(e)) => {
                            let error_msg = format!("Query error: {}", e);
                            let sqlstate = extract_sqlstate(&error_msg);
                            log!("rs-ontop-core: [SPARQL_REQUEST_ERROR]
error={}
sqlstate={:?}
[SPARQL_REQUEST_BEGIN]
{}
[SPARQL_REQUEST_END]", error_msg, sqlstate, sparql_query);
                            let status_code = determine_error_status_code(&error_msg, sqlstate.as_deref());
                            let error_response = build_error_response(
                                &error_msg,
                                status_code,
                                &sparql_query,
                                sqlstate.as_deref(),
                            );
                            let _ = request.respond(with_cors_headers(
                                Response::from_string(error_response.to_string())
                                    .with_status_code(StatusCode(status_code)),
                            ));
                        }
                        Err(panic_info) => {
                            let error_msg = if let Some(s) = panic_info.downcast_ref::<&str>() {
                                format!("Internal error: {}", s)
                            } else if let Some(s) = panic_info.downcast_ref::<String>() {
                                format!("Internal error: {}", s)
                            } else {
                                "Internal error: Unknown panic".to_string()
                            };
                            log!("rs-ontop-core: [SPARQL_REQUEST_PANIC]\nerror={}\n[SPARQL_REQUEST_BEGIN]\n{}\n[SPARQL_REQUEST_END]", error_msg, sparql_query);
                            let error_response = build_error_response(
                                &error_msg,
                                500,
                                &sparql_query,
                                Some("XX000"),
                            );
                            let _ = request.respond(with_cors_headers(
                                Response::from_string(error_response.to_string())
                                    .with_status_code(StatusCode(500)),
                            ));
                        }
                    }
                    continue;
                }

                let _ = request.respond(
                    Response::from_string("{\"error\":\"Not Found\"}")
                        .with_status_code(StatusCode(404)),
                );
            }
            Ok(None) => {
                consecutive_errors = 0;
            }
            Err(e) => {
                log!("rs-ontop-core HTTP error: {}", e);
                consecutive_errors += 1;
                if consecutive_errors >= max_consecutive_errors {
                    log!(
                        "rs-ontop-core: Too many consecutive errors ({}), waiting before retry",
                        consecutive_errors
                    );
                    std::thread::sleep(Duration::from_secs(1));
                    consecutive_errors = 0;
                }
            }
        }
    }

    log!("rs-ontop-core: SPARQL Gateway Background Worker cleanly stopped.");
}

fn with_cors_headers<R: std::io::Read + Send + 'static>(response: Response<R>) -> Response<R> {
    response
        .with_header(
            Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..])
                .expect("should create CORS header"),
        )
        .with_header(
            Header::from_bytes(
                &b"Access-Control-Allow-Methods"[..],
                &b"GET, POST, OPTIONS"[..],
            )
            .expect("should create CORS header"),
        )
        .with_header(
            Header::from_bytes(
                &b"Access-Control-Allow-Headers"[..],
                &b"Content-Type, Accept, Authorization"[..],
            )
            .expect("should create CORS header"),
        )
}

fn validate_query_stability(sparql_query: &str) -> Result<(), String> {
    // Layer-1 only: input legality checks (no feature-level blocking).
    const MAX_QUERY_BYTES: usize = 256 * 1024;

    if sparql_query.as_bytes().len() > MAX_QUERY_BYTES {
        return Err(format!(
            "Query is too large ({} bytes). Maximum allowed is {} bytes.",
            sparql_query.as_bytes().len(),
            MAX_QUERY_BYTES
        ));
    }

    if sparql_query.contains('\0') {
        return Err("Query contains NUL byte, which is not allowed.".to_string());
    }

    if sparql_query
        .chars()
        .any(|ch| ch.is_control() && ch != '\n' && ch != '\r' && ch != '\t')
    {
        return Err(
            "Query contains unsupported control characters (only tab/newline are allowed)."
                .to_string(),
        );
    }

    // Reject markdown/backtick artifacts early (common copy/paste issue).
    if sparql_query.contains('`') {
        return Err(
            "Query contains illegal markdown backtick character (`). Use plain SPARQL syntax."
                .to_string(),
        );
    }

    Ok(())
}

fn extract_sqlstate(error_msg: &str) -> Option<String> {
    let patterns = [
        r"SQLSTATE[:=\s]+([A-Z0-9]{5})",
        r"SqlState\((?:E)?([A-Z0-9]{5})\)",
        r"\[([A-Z0-9]{5})\]",
    ];
    for pat in patterns {
        if let Ok(re) = Regex::new(pat) {
            if let Some(caps) = re.captures(error_msg) {
                if let Some(m) = caps.get(1) {
                    return Some(m.as_str().to_string());
                }
            }
        }
    }
    None
}

fn determine_error_status_code(error_msg: &str, sqlstate: Option<&str>) -> u16 {
    if let Some(code) = sqlstate {
        if code.len() == 5 {
            let class = &code[0..2];
            return match class {
                "08" => 503,
                "22" | "23" | "28" | "42" => 400,
                "40" => 409,
                "53" | "54" | "55" | "57" | "58" => 503,
                "XX" => 500,
                _ => 500,
            };
        }
    }

    if error_msg.contains("column") && error_msg.contains("does not exist") {
        400
    } else if error_msg.contains("syntax error") {
        400
    } else if error_msg.to_ascii_lowercase().contains("invalid generated sql") {
        400
    } else if error_msg.contains("Database error")
        && (error_msg.contains("does not exist")
            || error_msg.contains("unmapped")
            || error_msg.contains("undefined"))
    {
        400
    } else if error_msg.contains("timeout") {
        408
    } else if error_msg.contains("connection") {
        503
    } else {
        500
    }
}

fn build_error_response(
    error_msg: &str,
    status_code: u16,
    sparql_query: &str,
    sqlstate: Option<&str>,
) -> serde_json::Value {
    serde_json::json!({
        "error": error_msg,
        "status_code": status_code,
        "sqlstate": sqlstate,
        "query": sparql_query,
    })
}


fn execute_ontop_query(sparql_query: &str) -> Result<Vec<serde_json::Value>, String> {
    // Single SPI frame: do not invoke SQL `ontop_query()` from inside `Spi::connect`
    // (that would nest SPI and SIGSEGV the backend when the inner frame calls SPI_finish).
    let mut inner: Option<Result<Vec<serde_json::Value>, String>> = None;
    if let Err(e) = Spi::connect(|mut client| {
        inner = Some(crate::spi_execute_sparql_json_rows(
            &mut client,
            sparql_query,
        ));
        Ok::<(), pgrx::spi::SpiError>(())
    }) {
        return Err(format!("SPI connect failed: {}", e));
    }
    inner.unwrap_or_else(|| Err("ontop query produced no result".to_string()))
}

#[allow(dead_code)]
fn build_logic_plan(sparql_query: &str) -> Result<LogicNode, String> {
    log!("[listener] Logic plan build: Started | SPARQL length: {}", sparql_query.len());

    let parser = SparqlParserV2::default();
    let parsed = parser
        .parse(sparql_query)
        .map_err(|e| format!("SPARQL parse failed: {}", e))?;

    // 从全局ENGINE获取元数据和映射
    let guard = ENGINE
        .lock()
        .map_err(|e| format!("Engine lock failed: {}", e))?;
    
    let engine = guard.as_ref().ok_or_else(|| {
        "Engine not initialized. Run SELECT ontop_start_sparql_server();".to_string()
    })?;

    // 使用引擎中的元数据和映射
    let builder = IRBuilder::new();
    builder
        .build_with_mappings(
            &parsed, 
            &engine.metadata, 
            Some(&engine.mappings)
        )
        .map_err(|e| format!("IR build failed: {}", e))
}

#[allow(dead_code)]
fn generate_flat_sql(logic_plan: &LogicNode) -> Result<String, String> {
    let mut generator = FlatSQLGenerator::new();
    generator
        .generate(logic_plan)
        .map_err(|e| format!("SQL generation failed: {}", e))
}

#[allow(dead_code)]
fn extract_variables_from_sparql(sparql_query: &str) -> Vec<String> {
    let re = match regex::Regex::new(r"\?(\w+)") {
        Ok(r) => r,
        Err(e) => {
            log!("[listener] Regex compile: Failed | Error: {}", e);
            return Vec::new();
        }
    };
    let mut vars: std::collections::HashSet<String> = std::collections::HashSet::new();

    for cap in re.captures_iter(sparql_query) {
        if let Some(var) = cap.get(1) {
            vars.insert(var.as_str().to_string());
        }
    }

    vars.into_iter().collect()
}

fn to_sparql_term(v: serde_json::Value) -> serde_json::Value {
    match v {
        serde_json::Value::Null => serde_json::json!({"type":"literal","value":""}),
        serde_json::Value::Bool(b) => serde_json::json!({
            "type":"literal",
            "value": b.to_string(),
            "datatype":"http://www.w3.org/2001/XMLSchema#boolean"
        }),
        serde_json::Value::Number(n) => {
            if n.is_i64() || n.is_u64() {
                serde_json::json!({
                    "type":"literal",
                    "value": n.to_string(),
                    "datatype":"http://www.w3.org/2001/XMLSchema#integer"
                })
            } else {
                serde_json::json!({
                    "type":"literal",
                    "value": n.to_string(),
                    "datatype":"http://www.w3.org/2001/XMLSchema#decimal"
                })
            }
        }
        serde_json::Value::String(s) => {
            if s.starts_with("http://") || s.starts_with("https://") {
                serde_json::json!({"type":"uri","value":s})
            } else {
                serde_json::json!({"type":"literal","value":s})
            }
        }
        other => serde_json::json!({"type":"literal","value":other.to_string()}),
    }
}

pub fn format_sparql_response(sparql_query: &str, bindings: Vec<serde_json::Value>) -> serde_json::Value {
    let upper = sparql_query.trim().to_ascii_uppercase();
    let is_ask = upper.starts_with("ASK")
        || upper.contains(" ASK ")
        || upper.contains("\nASK ")
        || (upper.starts_with("PREFIX") && upper.contains("ASK {"));
    if is_ask {
        return serde_json::json!({ "boolean": !bindings.is_empty() });
    }

    let parser = SparqlParserV2::default();
    let mut vars = parser
        .parse(sparql_query)
        .ok()
        .map(|p| {
            let mut seen = std::collections::HashSet::new();
            p.projected_vars
                .into_iter()
                .map(|v| v.trim_start_matches('?').to_string())
                .filter(|v| seen.insert(v.clone()))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    if vars.is_empty() {
        if let Some(serde_json::Value::Object(first)) = bindings.first() {
            vars = first.keys().cloned().collect();
            vars.sort();
        }
    }

    let normalize = |s: &str| -> String {
        s.chars()
            .filter(|c| *c != '_')
            .flat_map(|c| c.to_lowercase())
            .collect::<String>()
    };

    let formatted_bindings = bindings
        .into_iter()
        .map(|row| {
            let mut obj = serde_json::Map::new();
            if let serde_json::Value::Object(map) = row {
                if vars.is_empty() {
                    for (k, v) in map {
                        obj.insert(k, to_sparql_term(v));
                    }
                } else {
                    for var in &vars {
                        if let Some(v) = map.get(var) {
                            obj.insert(var.clone(), to_sparql_term(v.clone()));
                            continue;
                        }
                        let col_name = format!("col_{}", var);
                        if let Some(v) = map.get(&col_name) {
                            obj.insert(var.clone(), to_sparql_term(v.clone()));
                            continue;
                        }

                        let var_norm = normalize(var);
                        if let Some((_, v)) = map.iter().find(|(k, _)| {
                            let k_trimmed = k.strip_prefix("col_").unwrap_or(k);
                            normalize(k_trimmed) == var_norm
                        }) {
                            obj.insert(var.clone(), to_sparql_term(v.clone()));
                        }
                    }
                }
            }
            serde_json::Value::Object(obj)
        })
        .collect::<Vec<_>>();

    serde_json::json!({
        "head": { "vars": vars },
        "results": { "bindings": formatted_bindings }
    })
}

#[cfg(test)]
mod tests {
    use super::format_sparql_response;

    #[test]
    fn formats_select_response_with_head_and_bindings() {
        let rows = vec![serde_json::json!({"col_s":"http://ex/s1","col_o":"alice","col_p":"ignore"})];
        let out = format_sparql_response("SELECT ?s ?o WHERE { ?s ?p ?o }", rows);
        assert_eq!(out["head"]["vars"], serde_json::json!(["s", "o"]));
        assert!(out["results"]["bindings"][0].get("p").is_none());
        assert_eq!(out["results"]["bindings"][0]["s"]["type"], "uri");
        assert_eq!(out["results"]["bindings"][0]["o"]["type"], "literal");
    }

    #[test]
    fn formats_ask_response_as_boolean() {
        let rows = vec![serde_json::json!({"x":1})];
        let out = format_sparql_response("ASK { ?s ?p ?o }", rows);
        assert_eq!(out["boolean"], serde_json::json!(true));
    }
}
