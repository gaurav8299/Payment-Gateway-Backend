from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAuditBackend(ABC):
    """
    Abstract Interface for Pluggable Audit Logging Backends.
    Allows seamlessly switching storage targets (PostgreSQL, JSON files, Elasticsearch)
    without modifying application logic.
    """

    @abstractmethod
    def log(self, audit_data: Dict[str, Any]) -> None:
        """
        Record a sanitized audit log entry.
        """
