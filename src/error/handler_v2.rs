use crate::error::classifier::{classify, ErrorClass};

pub fn http_status_for_error(msg: &str) -> u16 {
    match classify(msg) {
        ErrorClass::Client => 400,
        ErrorClass::Timeout => 408,
        ErrorClass::Unavailable => 503,
        ErrorClass::Server => 500,
    }
}
