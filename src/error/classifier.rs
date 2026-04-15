#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorClass {
    Client,
    Server,
    Timeout,
    Unavailable,
}

pub fn classify(msg: &str) -> ErrorClass {
    let m = msg.to_ascii_lowercase();
    if m.contains("timeout") { return ErrorClass::Timeout; }
    if m.contains("connection") { return ErrorClass::Unavailable; }
    if m.contains("syntax") || m.contains("does not exist") { return ErrorClass::Client; }
    ErrorClass::Server
}
