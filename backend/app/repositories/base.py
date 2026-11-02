"""Generic Base Repository Pattern.

Encapsulates common SQLAlchemy database operations and queries, decoupling ORM
from FastAPI request handlers.
"""

from typing import Any, Generic, Optional, Type, TypeVar
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository for SQLAlchemy declarative models."""

    def __init__(self, model: Type[ModelType], db: Session) -> None:
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        """Retrieve single entity by primary key."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, skip: int = 0, limit: int = 100, **filters: Any) -> list[ModelType]:
        """List entities with pagination and optional field equality filtering."""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.offset(skip).limit(limit).all()

    def create(self, obj: ModelType) -> ModelType:
        """Persist new entity instance."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: ModelType, updates: dict[str, Any]) -> ModelType:
        """Apply partial dictionary updates to existing entity."""
        for field, value in updates.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: Any) -> bool:
        """Delete entity by primary key."""
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

