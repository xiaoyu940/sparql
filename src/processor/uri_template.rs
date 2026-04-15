#[derive(Debug, Default)]
pub struct UriTemplate;

impl UriTemplate {
    pub fn apply(template: &str, value: &str) -> String {
        template.replace("{value}", value)
    }
}
