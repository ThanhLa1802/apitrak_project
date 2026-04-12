from rest_framework.pagination import CursorPagination


class CreatedAtCursorPagination(CursorPagination):
    """Project-wide cursor pagination using the `created_at` field present on all models."""
    ordering = "-created_at"
    page_size = 100
