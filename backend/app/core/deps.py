"""FastAPI dependencies."""

from app.integrations.supabase.database import SupabaseRepository, get_repository


def get_repo() -> SupabaseRepository:
    return get_repository()
