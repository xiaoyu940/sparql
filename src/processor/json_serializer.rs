use crate::error::OntopError;

#[derive(Debug, Default)]
pub struct JsonSerializer;

impl JsonSerializer {
    pub fn to_string<T: serde::Serialize>(value: &T) -> Result<String, OntopError> {
        serde_json::to_string(value).map_err(OntopError::from)
    }
}
