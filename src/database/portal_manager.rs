//! Sprint1 delivery shim: portal manager facade.

use crate::error::OntopError;
use crate::database::streaming_client::QueryPortal;

#[derive(Debug, Default)]
pub struct PortalManager;

impl PortalManager {
    pub fn close_portal(&self, portal: &mut QueryPortal) -> Result<(), OntopError> {
        portal.close()
    }
}
