"""Abstract storage adapter — swap local JSON for S3/GCS/Supabase later."""

from abc import ABC, abstractmethod

from gnomon_expenses.models.expense import Expense


class StorageAdapter(ABC):
    @abstractmethod
    def load_all(self) -> list[Expense]:
        """Load all expense records."""

    @abstractmethod
    def save(self, expense: Expense) -> None:
        """Save or update a single expense (upsert by id)."""

    @abstractmethod
    def save_all(self, expenses: list[Expense]) -> None:
        """Replace all records."""

    @abstractmethod
    def find_by_id(self, expense_id: str) -> Expense | None:
        """Find expense by id prefix."""

    @abstractmethod
    def find_by_hash(self, file_hash: str) -> Expense | None:
        """Find expense by file hash (dedup check)."""

    @abstractmethod
    def delete(self, expense_id: str) -> bool:
        """Delete an expense by id."""
