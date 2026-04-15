use pgrx::bgworkers::*;
use pgrx::prelude::*;
use std::time::Duration;
use tiny_http::{Server, Response, Method, StatusCode};
use url::Url;
use chrono;

use crate::listener::{format_sparql_response};

/// 鲁棒的SPARQL监听器 - 改进错误处理，防止单个查询失败导致服务关闭
#[pg_guard]
#[no_mangle]
pub extern "C-unwind" fn ontop_robust_sparql_bgworker_main(_arg: pg_sys::Datum) {
    log!("rs-ontop-core: Starting Robust SPARQL Gateway Background Worker");

    // Step 1: Attach signal handlers so SIGTERM works correctly
    BackgroundWorker::attach_signal_handlers(SignalWakeFlags::SIGHUP | SignalWakeFlags::SIGTERM);

    // Step 2: Connect to the database BEFORE entering any transaction
    BackgroundWorker::connect_worker_to_spi(Some("rs_ontop_core"), None);

    // Step 3: Bind the HTTP port OUTSIDE of any transaction  
    let server = match Server::http("0.0.0.0:5820") {
        Ok(s) => s,
        Err(e) => {
            log!("rs-ontop-core: Failed to bind port 5820. Error: {}", e);
            return;
        }
    };

    log!("rs-ontop-core Robust SPARQL Listener successfully bound to http://0.0.0.0:5820");

    // Step 4: Main HTTP event loop with robust error handling
    let mut consecutive_errors = 0;
    let max_consecutive_errors = 10;
    
    while BackgroundWorker::wait_latch(Some(Duration::from_millis(0))) {
        pgrx::check_for_interrupts!();

        match server.recv_timeout(Duration::from_millis(100)) {
            Ok(Some(request)) => {
                let path = request.url().to_string();

                // 重置错误计数器
                consecutive_errors = 0;

                // --- Route: /ontology (expose JSON-LD TBox) ---
                if path.starts_with("/ontology") {
                    handle_ontology_request(request);
                    continue;
                }

                // --- Route: /sparql (execute SPARQL query) ---
                if path.starts_with("/sparql") {
                    if let Err(e) = handle_sparql_request(request) {
                        log!("rs-ontop-core: Error handling SPARQL request: {}", e);
                        consecutive_errors += 1;
                    }
                    continue;
                }

                // --- Route: /health (health check) ---
                if path.starts_with("/health") {
                    handle_health_request(request);
                    continue;
                }

                // --- Default: 404 ---
                let _ = request.respond(
                    Response::from_string("{\"error\":\"Not Found\"}").with_status_code(StatusCode(404))
                );
            },
            Ok(None) => {
                // Timeout, reset error counter
                consecutive_errors = 0;
                continue;
            },
            Err(e) => {
                log!("rs-ontop-core HTTP error: {}", e);
                consecutive_errors += 1;
                
                // 如果连续错误太多，等待一段时间再重试
                if consecutive_errors >= max_consecutive_errors {
                    log!("rs-ontop-core: Too many consecutive errors ({}), waiting before retry", consecutive_errors);
                    std::thread::sleep(Duration::from_secs(1));
                    consecutive_errors = 0; // 重置计数器
                }
            }
        }
    }

    log!("rs-ontop-core: Robust SPARQL Gateway Background Worker cleanly stopped.");
}

/// 处理ontology请求
fn handle_ontology_request(request: tiny_http::Request) {
    // Each SPI call needs its own transaction
    let body = BackgroundWorker::transaction(|| {
        Spi::get_one::<pgrx::JsonB>("SELECT ontop_inspect_ontology();")
    });

    match body {
        Ok(Some(json_ld)) => {
            let json_str = serde_json::to_string(&json_ld.0).unwrap_or_default();
            let response = Response::from_string(json_str)
                .with_header(tiny_http::Header::from_bytes(
                    &b"Content-Type"[..],
                    &b"application/json; charset=utf-8"[..],
                ).expect("valid regex"));
            let _ = request.respond(response);
        },
        Ok(None) => {
            let _ = request.respond(
                Response::from_string("{\"error\":\"Engine not initialized\"}").with_status_code(StatusCode(503))
            );
        },
        Err(e) => {
            let _ = request.respond(
                Response::from_string(format!("{{\"error\":\"{}\"}}", e)).with_status_code(StatusCode(500))
            );
        }
    }
}

/// 处理SPARQL请求 - 增强错误处理
fn handle_sparql_request(mut request: tiny_http::Request) -> Result<(), String> {
    let path = request.url().to_string();
    let method = request.method().clone();
    
    let mut sparql_query = String::new();

    if method == Method::Post {
        let mut content = String::new();
        if let Err(e) = request.as_reader().read_to_string(&mut content) {
            return Err(format!("Failed to read request body: {}", e));
        }
        sparql_query = content;
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
            Response::from_string("{\"error\":\"Missing query parameter\"}").with_status_code(StatusCode(400))
        );
        return Ok(());
    }

    log!("rs-ontop-core: Received SPARQL query: {}", sparql_query);

    // 使用try-catch块来捕获所有可能的错误
    let result = std::panic::catch_unwind(|| {
        let sparql_clone = sparql_query.clone();
        BackgroundWorker::transaction(move || {
            Spi::connect(|client| {
                let sql = format!("SELECT ontop_query($pgrx${}$pgrx$);", sparql_clone);
                let table = client
                    .select(&sql, None, None)
                    .map_err(|e| format!("Query execution failed: {}", e))?;
                let mut results = Vec::new();
                for row in table {
                    if let Some(jsonb) = row
                        .get_by_name::<pgrx::JsonB, _>("ontop_query")
                        .map_err(|e| format!("Failed to read binding: {}", e))?
                    {
                        results.push(jsonb.0);
                    }
                }
                Ok::<Vec<serde_json::Value>, String>(results)
            })
        })
    });

    match result {
        Ok(exec_result) => {
            match exec_result {
                Ok(bindings) => {
                    let out = format_sparql_response(&sparql_query, bindings);
                    let response = Response::from_string(out.to_string())
                        .with_header(tiny_http::Header::from_bytes(
                            &b"Content-Type"[..],
                            &b"application/sparql-results+json; charset=utf-8"[..],
                        ).expect("valid regex"));
                    let _ = request.respond(response);
                },
                Err(e) => {
                    let error_msg = format!("Query error: {}", e);
                    log!("rs-ontop-core: {}", error_msg);
                    let _ = request.respond(
                        Response::from_string(format!("{{\"error\":\"{}\"}}", error_msg))
                            .with_status_code(StatusCode(500))
                    );
                }
            }
        },
        Err(panic_info) => {
            let error_msg = if let Some(s) = panic_info.downcast_ref::<String>() {
                format!("Internal error: {}", s)
            } else if let Some(s) = panic_info.downcast_ref::<&str>() {
                format!("Internal error: {}", s)
            } else {
                "Internal error: Unknown panic".to_string()
            };
            
            log!("rs-ontop-core: Panic caught: {}", error_msg);
            let _ = request.respond(
                Response::from_string(format!("{{\"error\":\"{}\"}}", error_msg))
                    .with_status_code(StatusCode(500))
            );
        }
    }

    Ok(())
}

/// 处理健康检查请求
fn handle_health_request(request: tiny_http::Request) {
    let health_status = serde_json::json!({
        "status": "healthy",
        "service": "rs-ontop-core SPARQL Gateway",
        "version": "1.0.0",
        "timestamp": chrono::Utc::now().to_rfc3339()
    });

    let response = Response::from_string(health_status.to_string())
        .with_header(tiny_http::Header::from_bytes(
            &b"Content-Type"[..],
            &b"application/json; charset=utf-8"[..],
        ).expect("valid regex"));
    let _ = request.respond(response);
}
