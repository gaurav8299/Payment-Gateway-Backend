import json
import logging
from typing import Any, Dict

from audit_logs.backends.base import BaseAuditBackend

logger = logging.getLogger("audit_file")


class FileAuditBackend(BaseAuditBackend):
    """
    Audit logging backend appending structured JSON lines to local audit log files.
    """

    def log(self, audit_data: Dict[str, Any]) -> None:
        try:
            log_line = json.dumps(audit_data)
            logger.info(log_line)
        except Exception as e:
            logger.error(f"Failed to write audit log to file: {e}")
