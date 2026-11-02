"""Plot and Geospatial Query Repository.

Provides specialized spatial query operations and active crop cycle lookups.
"""

from typing import Optional
from shapely.geometry import Point, shape
from shapely.wkt import loads as loads_wkt
from sqlalchemy.orm import Session

from app.models.plot import CropCycle, FarmPlot
from app.repositories.base import BaseRepository


class PlotRepository(BaseRepository[FarmPlot]):
    """Repository handling geospatial field plot queries and boundary operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(FarmPlot, db)

    def get_plot_by_id(self, plot_id: int) -> Optional[FarmPlot]:
        """Fetch plot by ID."""
        return self.get(plot_id)

    def get_plots_by_device(self, device_id: str, active_only: bool = False) -> list[FarmPlot]:
        """List plots registered to a device."""
        query = self.db.query(FarmPlot).filter(FarmPlot.device_id == device_id)
        if active_only:
            query = query.filter(FarmPlot.is_active.is_(True))
        return query.order_by(FarmPlot.id.desc()).all()

    def get_plots_by_farm(self, farm_id: int, active_only: bool = False) -> list[FarmPlot]:
        """List all plots associated with a parent farm holding."""
        query = self.db.query(FarmPlot).filter(FarmPlot.farm_id == farm_id)
        if active_only:
            query = query.filter(FarmPlot.is_active.is_(True))
        return query.order_by(FarmPlot.id.desc()).all()

    def get_active_crop_cycle(self, plot_id: int) -> Optional[CropCycle]:
        """Fetch currently active crop cycle for a plot."""
        return (
            self.db.query(CropCycle)
            .filter(CropCycle.plot_id == plot_id, CropCycle.is_active.is_(True))
            .first()
        )

    def find_plots_containing_point(self, latitude: float, longitude: float) -> list[FarmPlot]:
        """Spatial point-in-polygon lookup for field polygons containing the given coordinate."""
        pt = Point(longitude, latitude)
        active_plots = self.db.query(FarmPlot).filter(FarmPlot.is_active.is_(True)).all()
        matching = []

        for plot in active_plots:
            try:
                poly = loads_wkt(str(plot.boundary))
                if poly.contains(pt):
                    matching.append(plot)
            except Exception:
                continue

        return matching

