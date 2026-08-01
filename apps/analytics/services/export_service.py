import csv
import io
import json
import logging
from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse

logger = logging.getLogger("payment_gateway")


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ExportService:
    """
    Export Service providing CSV and JSON export capabilities
    for analytics report data.
    """

    @staticmethod
    def export_csv(rows: list, filename: str = "report.csv") -> HttpResponse:
        """Generate a CSV HttpResponse from a list of dicts."""
        if not rows:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            # Convert non-string values for CSV output
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, (Decimal, datetime)):
                    clean_row[k] = str(v)
                else:
                    clean_row[k] = v
            writer.writerow(clean_row)

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_json(data: dict, filename: str = "report.json") -> HttpResponse:
        """Generate a JSON file download HttpResponse."""
        content = json.dumps(data, cls=DecimalEncoder, indent=2)
        response = HttpResponse(content, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
