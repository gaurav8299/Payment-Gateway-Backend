from common.middleware import get_current_correlation_id
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class returning structured metadata.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "message": "Data retrieved successfully",
                "data": data,
                "meta": {
                    "count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "current_page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "timestamp": timezone.now().isoformat(),
                "correlation_id": get_current_correlation_id(),
            }
        )
