"""Database connectivity and ORM base definition for Krishi Mitra.

Supports PostgreSQL + PostGIS in production, and SQLite with WKT/GeoJSON fallback for local testing.
"""

import json
from typing import Generator, Any
from sqlalchemy import create_engine, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.types import TypeDecorator
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape, mapping, Polygon
from shapely import wkt

from app.core.config import settings

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PostGISGeometry(TypeDecorator):
    """PostGIS Polygon geometry type with dialect fallback.

    Uses native PostGIS GEOMETRY(Polygon, 4326) on PostgreSQL.
    Falls back to text-serialized WKT/GeoJSON on SQLite for portability.
    """
    impl = Geometry
    cache_ok = True

    def __init__(self, geometry_type: str = "POLYGON", srid: int = 4326, **kwargs: Any) -> None:
        super().__init__()
        self.geom_type = geometry_type
        self.srid = srid
        self.kwargs = kwargs

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect is not None and dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(self.geom_type, srid=self.srid, **self.kwargs))
        if dialect is not None:
            return dialect.type_descriptor(Text())
        return Text()

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None

        # Convert dictionary (GeoJSON) or Polygon object to WKT string
        if isinstance(value, dict):
            geom = shape(value)
            wkt_str = geom.wkt
        elif hasattr(value, "wkt"):
            wkt_str = value.wkt
        elif isinstance(value, str):
            wkt_str = value
        else:
            wkt_str = str(value)

        if dialect.name == "postgresql":
            return WKTElement(wkt_str, srid=self.srid)
        return wkt_str

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "data"):
            # GeoAlchemy2 WKBElement
            return str(value)
        return str(value)


def get_db() -> Generator[Session, None, None]:
    """Dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

