import logging
from typing import Any, Dict

from audit_logs.backends.base import BaseAuditBackend

logger = logging.getLogger("payment_gateway")


class ElasticAuditBackend(BaseAuditBackend):
    """
    Extensible Audit Backend interface for Elasticsearch/OpenSearch centralized logging platforms.
    """

    def log(self, audit_data: Dict[str, Any]) -> None:
        # Extensible placeholder streaming logs to Elasticsearch cluster index
        logger.info(
            f"[ElasticSearch Audit Index] -> {audit_data.get('event_type')}: {audit_data.get('action')}"
        )
