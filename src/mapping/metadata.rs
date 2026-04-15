#[derive(Debug, Clone, Default)]
pub struct MappingTableMetadata {
    pub table_name: String,
    pub primary_key: Option<String>,
    pub indexed_columns: Vec<String>,
}
