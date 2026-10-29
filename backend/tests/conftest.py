"""Pytest shared configuration and fixtures for Krishi Mitra test suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.profile import DeviceProfile
from app.models.plot import FarmPlot, CropCycle


@pytest.fixture(scope="session")
def test_engine():
    """Create a persistent shared in-memory SQLite database for the test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session")
def SessionTesting(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_engine, SessionTesting):
    """Provide a transactional database session per test, rolling back on completion."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionTesting(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with dependency override for get_db."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seed_test_farmer(db_session):
    """Seed a test farmer profile and active cotton plot."""
    profile = DeviceProfile(
        device_id="TEST-HARDWARE-UUID-001",
        farmer_name="Rameshwar Patil",
        preferred_language="hi",
        phone_number="+919876543210",
        kisan_id="PMK-123456",
    )
    db_session.add(profile)
    db_session.flush()

    plot = FarmPlot(
        id=1,
        device_id="TEST-HARDWARE-UUID-001",
        name="Field North",
        boundary="POLYGON((78.50 17.50, 78.51 17.50, 78.51 17.51, 78.50 17.51, 78.50 17.50))",
        centroid_lat=17.505,
        centroid_lon=78.505,
        area_hectares=1.2,
        soil_texture="Vertisol",
        slope_percent=1.5,
        is_active=True,
    )
    db_session.add(plot)
    db_session.flush()

    cycle = CropCycle(
        id=1,
        plot_id=1,
        crop_name="Cotton",
        variety="Bt-Cotton",
        growth_stage="FLOWERING",
        irrigation_method="DRIP",
        is_active=True,
    )
    db_session.add(cycle)
    db_session.commit()
    return profile

