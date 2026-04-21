use pgrx::bgworkers::*;
use pgrx::prelude::*;
use spargebra::Query;
use std::io::Read;
use std::time::Duration;
use tiny_http::{Method, Response, Server, StatusCode};
use url::Url;

use crate::listener::{execute_ontop_query, format_sparql_response};

#[pg_guard]
#[no_mangle]
pub extern "C-unwind" fn ontop_robust_sparql_bgworker_main(_arg: pg_sys::Datum) {
    log!("rs-ontop-core: Starting Robust SPARQL Gateway Background Worker");

    BackgroundWorker::attach_signal_handlers(SignalWakeFlags::SIGHUP | SignalWakeFlags::SIGTERM);
    BackgroundWorker::connect_worker_to_spi(Some("rs_ontop_core"), None);

    let server = match Server::http("0.0.0.0:5820") {
        Ok(s) => s,
        Err(e) => {
            log!("rs-ontop-core: Failed to bind port 5820. Error: {}", e);
            return;
        }
    };

    log!("rs-ontop-core Robust SPARQL Listener successfully bound to http://0.0.0.0:5820");

    let mut consecutive_errors = 0;
    let max_consecutive_errors = 10;

    while BackgroundWorker::wait_latch(Some(Duration::from_millis(0))) {
        pgrx::check_for_interrupts!();

        match server.recv_timeout(Duration::from_millis(100)) {
            Ok(Some(request)) => {
                let path = request.url().to_string();
                consecutive_errors = 0;

                if path.starts_with("/ontology") {
                    handle_ontology_request(request);
                    continue;
                }

                if path.starts_with("/sparql") {
                    if let Err(e) = handle_sparql_request(request) {
                        log!("rs-ontop-core: Error handling SPARQL request: {}", e);
                        consecutive_errors += 1;
                    }
                    continue;
                }

                if path.starts_with("/health") {
                    handle_health_request(request);
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

    log!("rs-ontop-core: Robust SPARQL Gateway Background Worker cleanly stopped.");
}

fn handle_ontology_request(request: tiny_http::Request) {
    let body = BackgroundWorker::transaction(|| {
        Spi::get_one::<pgrx::JsonB>(
            r#"
            SELECT
              COALESCE(ontop_inspect_ontology(), '{}'::jsonb)
              || jsonb_build_object(
                   'mappings', jsonb_build_object(
                     'raw_sources', COALESCE((
                       SELECT jsonb_agg(
                         jsonb_build_object(
                           'id', id,
                           'name', name,
                           'ttl_length', length(ttl_content),
                           'ttl_content', ttl_content
                         )
                         ORDER BY id
                       )
                       FROM public.ontop_r2rml_mappings
                     ), '[]'::jsonb),
                     'rules', COALESCE((
                       SELECT jsonb_agg(
                         jsonb_build_object(
                           'target_triple', target_triple,
                           'sql_source', sql_source
                         )
                       )
                       FROM ontop_inspect_mappings()
                     ), '[]'::jsonb)
                   ),
                   'stats', jsonb_build_object(
                     'raw_source_count', COALESCE((SELECT count(*) FROM public.ontop_r2rml_mappings), 0),
                     'rule_count', COALESCE((SELECT count(*) FROM ontop_inspect_mappings()), 0)
                   )
                 )
            ;
        "#,
        )
    });

    match body {
        Ok(Some(json_ld)) => {
            let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();
            let response = Response::from_string(json_str).with_header(
                tiny_http::Header::from_bytes(
                    &b"Content-Type"[..],
                    &b"application/json; charset=utf-8"[..],
                )
                .expect("valid header"),
            );
            let _ = request.respond(response);
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
}

fn normalize_sparql_query_input(query: &str) -> String {
    let mut out = String::with_capacity(query.len());
    let mut in_angle = false;

    for ch in query.chars() {
        match ch {
            '<' => {
                in_angle = true;
                out.push('<');
            }
            '>' => {
                if in_angle {
                    while out
                        .chars()
                        .last()
                        .map(|c| c.is_whitespace() || c == '`')
                        .unwrap_or(false)
                    {
                        out.pop();
                    }
                }
                in_angle = false;
                out.push('>');
            }
            '`' if in_angle => {}
            _ if in_angle && out.ends_with('<') && ch.is_whitespace() => {}
            _ => out.push(ch),
        }
    }

    let normalized = out.replace('`', "");

    let mut compact = String::with_capacity(normalized.len());
    let mut chars = normalized.chars().peekable();
    while let Some(c) = chars.next() {
        compact.push(c);
        if c == '<' {
            while let Some(n) = chars.peek() {
                if n.is_whitespace() {
                    chars.next();
                } else {
                    break;
                }
            }
        }
    }

    compact
}

fn validate_sparql_syntax(sparql_query: &str) -> Result<(), String> {
    let trimmed = sparql_query.trim();
    if trimmed.is_empty() {
        return Err("SPARQL syntax error: empty query".to_string());
    }

    Query::parse(trimmed, None)
        .map(|_| ())
        .map_err(|e| format!("SPARQL syntax error: {}", e))
}

fn handle_sparql_request(mut request: tiny_http::Request) -> Result<(), String> {
    let method = request.method().clone();
    let path = request.url().to_string();

    if method == Method::Options {
        let response = Response::empty(StatusCode(204));
        let _ = request.respond(response);
        return Ok(());
    }

    let mut sparql_query = String::new();

    if method == Method::Post {
        let mut content = String::new();
        let _ = request.as_reader().read_to_string(&mut content);
        if content.starts_with("query=") {
            for (k, v) in url::form_urlencoded::parse(content.as_bytes()) {
                if k == "query" {
                    sparql_query = v.into_owned();
                    break;
                }
            }
        } else {
            sparql_query = content;
        }
    } else if method == Method::Get {
        if let Ok(url) = Url::parse(&format!("http://localhost{}", path)) {
            for (key, val) in url.query_pairs() {
                if key == "query" {
                    sparql_query = val.to_string();
                    break;
                }
            }
        }
    }

    if sparql_query.trim().is_empty() {
        let _ = request.respond(
            Response::from_string("{\"error\":\"Missing query parameter\"}")
                .with_status_code(StatusCode(400)),
        );
        return Ok(());
    }

    let normalized_query = normalize_sparql_query_input(&sparql_query);
    if normalized_query != sparql_query {
        sparql_query = normalized_query;
        log!("rs-ontop-core: Normalized incoming SPARQL query formatting");
    }

    if let Err(e) = validate_sparql_syntax(&sparql_query) {
        let safe_msg = e.replace('"', "'");
        let _ = request.respond(
            Response::from_string(format!(
                "{{\"error\":\"{}\",\"code\":\"SPARQL_SYNTAX_ERROR\",\"status_code\":400}}",
                safe_msg
            ))
            .with_status_code(StatusCode(400)),
        );
        return Ok(());
    }

    log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);

    let sparql_for_worker = sparql_query.clone();
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(move || {
        BackgroundWorker::transaction(|| execute_ontop_query(&sparql_for_worker))
    }));

    match result {
        Ok(Ok(rows)) => {
            let response_data = format_sparql_response(&sparql_query, rows);
            let response = Response::from_string(response_data.to_string())
                .with_header(
                    tiny_http::Header::from_bytes(
                        &b"Content-Type"[..],
                        &b"application/sparql-results+json"[..],
                    )
                    .expect("valid header"),
                )
                .with_status_code(StatusCode(200));
            let _ = request.respond(response);
            Ok(())
        }
        Ok(Err(e)) => {
            let error_data = serde_json::json!({
                "error": e,
                "query": sparql_query,
                "status_code": 500
            });
            let response = Response::from_string(error_data.to_string())
                .with_header(
                    tiny_http::Header::from_bytes(
                        &b"Content-Type"[..],
                        &b"application/json"[..],
                    )
                    .expect("valid header"),
                )
                .with_status_code(StatusCode(500));
            let _ = request.respond(response);
            Ok(())
        }
        Err(panic_info) => {
            let panic_msg = if let Some(s) = panic_info.downcast_ref::<&str>() {
                s.to_string()
            } else if let Some(s) = panic_info.downcast_ref::<String>() {
                s.clone()
            } else {
                "Unknown panic".to_string()
            };

            log!(
                "rs-ontop-core: SPARQL_REQUEST_PANIC: query='{}', panic='{}'",
                sparql_query,
                panic_msg
            );

            let error_data = serde_json::json!({
                "error": format!("Internal error: {}", panic_msg),
                "query": sparql_query,
                "status_code": 500,
                "error_code": "SPARQL_REQUEST_PANIC"
            });

            let response = Response::from_string(error_data.to_string())
                .with_header(
                    tiny_http::Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..])
                        .expect("valid header"),
                )
                .with_status_code(StatusCode(500));
            let _ = request.respond(response);
            Ok(())
        }
    }
}

fn handle_health_request(request: tiny_http::Request) {
    let health_data = serde_json::json!({
        "status": "healthy",
        "service": "rs-ontop-core SPARQL Gateway",
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "version": "0.3.0"
    });

    let response = Response::from_string(health_data.to_string())
        .with_header(
            tiny_http::Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..])
                .expect("valid header"),
        )
        .with_status_code(StatusCode(200));

    let _ = request.respond(response);
}
