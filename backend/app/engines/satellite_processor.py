"""Satellite Multispectral Zonal Statistics & Cloud Masking Engine.

Computes Normalized Difference Vegetation Index (NDVI), Normalized Difference Water Index (NDWI),
and Normalized Difference Moisture Index (NDMI) with Scene Classification Layer (SCL) cloud filtering.
Provides seamless fallback to phenological growth curves when cloud occlusion exceeds 30%.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
from typing import Any, Optional

import numpy as np

from app.engines.satellite_stac import calculate_synthetic_indices


@dataclass(frozen=True)
class SatelliteZonalResult:
    """Zonal statistics and quality metadata over a farm field polygon."""

    acquisition_date: date
    mean_ndvi: float
    min_ndvi: float
    max_ndvi: float
    std_ndvi: float
    mean_ndwi: float
    mean_ndmi: float
    cloud_cover_percent: float
    pixel_validity_count: int
    status: str  # MEASURED, CLOUD_OCCLUDED, SYNTHETIC_FALLBACK
    source: str
    provenance_type: str
    quality_score: float
    stac_item_id: Optional[str] = None


class SatelliteProcessor:
    """Multispectral raster zonal statistics calculator with cloud masking."""

    CLOUD_THRESHOLD_PERCENT = 30.0

    # Sentinel-2 Scene Classification Layer (SCL) mask codes
    SCL_NO_DATA = 0
    SCL_SATURATED = 1
    SCL_DARK_FEATURE = 2
    SCL_CLOUD_SHADOW = 3
    SCL_VEGETATION = 4
    SCL_NOT_VEGETATED = 5
    SCL_WATER = 6
    SCL_UNCLASSIFIED = 7
    SCL_CLOUD_MEDIUM_PROB = 8
    SCL_CLOUD_HIGH_PROB = 9
    SCL_CIRRUS = 10
    SCL_SNOW_ICE = 11

    CLOUD_SCL_CLASSES = {
        SCL_CLOUD_SHADOW,
        SCL_CLOUD_MEDIUM_PROB,
        SCL_CLOUD_HIGH_PROB,
        SCL_CIRRUS,
    }

    @classmethod
    def compute_zonal_statistics(
        cls,
        red_band: np.ndarray,
        nir_band: np.ndarray,
        green_band: np.ndarray,
        swir_band: Optional[np.ndarray] = None,
        scl_band: Optional[np.ndarray] = None,
        acquisition_date: Optional[date] = None,
        stac_item_id: Optional[str] = None,
        crop_name: str = "Cotton",
        sowing_date: Optional[date] = None,
    ) -> SatelliteZonalResult:
        """Calculate NDVI, NDWI, NDMI and cloud occlusion over field raster arrays.

        If cloud cover exceeds 30%, flags status as CLOUD_OCCLUDED and falls back to
        the phenological growth curve.
        """
        if acquisition_date is None:
            acquisition_date = date.today()
        if sowing_date is None:
            sowing_date = acquisition_date

        total_pixels = red_band.size
        if total_pixels == 0:
            return cls._generate_pure_synthetic_result(crop_name, sowing_date, acquisition_date)

        # 1. Cloud Masking via SCL or zero-data
        if scl_band is not None and scl_band.shape == red_band.shape:
            cloud_mask = np.isin(scl_band, list(cls.CLOUD_SCL_CLASSES))
            cloud_count = int(np.sum(cloud_mask))
            cloud_pct = round((cloud_count / total_pixels) * 100.0, 1)
            valid_mask = (~cloud_mask) & (red_band > 0) & (nir_band > 0)
        else:
            cloud_pct = 0.0
            valid_mask = (red_band > 0) & (nir_band > 0)

        valid_count = int(np.sum(valid_mask))

        # 2. Check Cloud Occlusion Threshold (> 30% or 0 valid pixels)
        if cloud_pct > cls.CLOUD_THRESHOLD_PERCENT or valid_count == 0:
            synthetic = calculate_synthetic_indices(crop_name, sowing_date, acquisition_date)
            return SatelliteZonalResult(
                acquisition_date=acquisition_date,
                mean_ndvi=synthetic.ndvi,
                min_ndvi=max(-1.0, round(synthetic.ndvi - 0.05, 3)),
                max_ndvi=min(1.0, round(synthetic.ndvi + 0.05, 3)),
                std_ndvi=0.03,
                mean_ndwi=synthetic.ndwi,
                mean_ndmi=round(synthetic.ndwi - 0.04, 3),
                cloud_cover_percent=cloud_pct,
                pixel_validity_count=valid_count,
                status="CLOUD_OCCLUDED",
                source="SYNTHETIC_PHENOLOGY_MODEL",
                provenance_type="SYNTHETIC_FALLBACK",
                quality_score=0.60,
                stac_item_id=stac_item_id,
            )

        # 3. Valid Pixel Mathematical Indices
        red_valid = red_band[valid_mask].astype(float)
        nir_valid = nir_band[valid_mask].astype(float)
        green_valid = green_band[valid_mask].astype(float)

        eps = 1e-6
        ndvi_arr = (nir_valid - red_valid) / (nir_valid + red_valid + eps)
        ndwi_arr = (green_valid - nir_valid) / (green_valid + nir_valid + eps)

        if swir_band is not None and swir_band.shape == red_band.shape:
            swir_valid = swir_band[valid_mask].astype(float)
            ndmi_arr = (nir_valid - swir_valid) / (nir_valid + swir_valid + eps)
            mean_ndmi = float(np.mean(ndmi_arr))
        else:
            mean_ndmi = float(np.mean(ndwi_arr)) - 0.05

        return SatelliteZonalResult(
            acquisition_date=acquisition_date,
            mean_ndvi=round(float(np.mean(ndvi_arr)), 3),
            min_ndvi=round(float(np.min(ndvi_arr)), 3),
            max_ndvi=round(float(np.max(ndvi_arr)), 3),
            std_ndvi=round(float(np.std(ndvi_arr)), 3),
            mean_ndwi=round(float(np.mean(ndwi_arr)), 3),
            mean_ndmi=round(mean_ndmi, 3),
            cloud_cover_percent=cloud_pct,
            pixel_validity_count=valid_count,
            status="MEASURED",
            source="SENTINEL_2_L2A",
            provenance_type="DERIVED",
            quality_score=round(max(0.70, 1.0 - (cloud_pct / 100.0)), 2),
            stac_item_id=stac_item_id or "S2A_MSIL2A_SIMULATED",
        )

    @classmethod
    def _generate_pure_synthetic_result(
        cls,
        crop_name: str,
        sowing_date: date,
        observation_date: date,
    ) -> SatelliteZonalResult:
        """Pure fallback when no raster arrays are present."""
        synth = calculate_synthetic_indices(crop_name, sowing_date, observation_date)
        return SatelliteZonalResult(
            acquisition_date=observation_date,
            mean_ndvi=synth.ndvi,
            min_ndvi=round(synth.ndvi - 0.04, 3),
            max_ndvi=round(synth.ndvi + 0.04, 3),
            std_ndvi=0.02,
            mean_ndwi=synth.ndwi,
            mean_ndmi=round(synth.ndwi - 0.03, 3),
            cloud_cover_percent=0.0,
            pixel_validity_count=100,
            status="SYNTHETIC_FALLBACK",
            source="SYNTHETIC_PHENOLOGY_MODEL",
            provenance_type="SYNTHETIC_FALLBACK",
            quality_score=0.75,
            stac_item_id="SYNTHETIC_SIMULATION",
        )

    @classmethod
    def simulate_multispectral_scene(
        cls,
        crop_name: str = "Cotton",
        das: int = 45,
        cloud_pct: float = 10.0,
        grid_size: tuple[int, int] = (10, 10),
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Generate synthetic multispectral raster bands (Red, NIR, Green, SWIR, SCL) for testing."""
        h, w = grid_size
        total = h * w
        sowing = date.fromordinal(date.today().toordinal() - das)
        synth = calculate_synthetic_indices(crop_name, sowing, date.today())

        # Base reflectances scaled 0 - 10000 (Sentinel-2 L2A digital numbers)
        # Higher NDVI -> higher NIR, lower Red
        base_nir = int(2500 + synth.ndvi * 3000)
        base_red = int(1200 - synth.ndvi * 800)
        base_green = int(1100)
        base_swir = int(1600 - synth.ndwi * 600)

        nir = np.full((h, w), base_nir, dtype=np.uint16)
        red = np.full((h, w), base_red, dtype=np.uint16)
        green = np.full((h, w), base_green, dtype=np.uint16)
        swir = np.full((h, w), base_swir, dtype=np.uint16)
        scl = np.full((h, w), cls.SCL_VEGETATION, dtype=np.uint8)

        # Inject cloud pixels according to requested percentage
        cloud_pixels = int(total * (cloud_pct / 100.0))
        if cloud_pixels > 0:
            flat_indices = np.random.choice(total, cloud_pixels, replace=False)
            for idx in flat_indices:
                r = idx // w
                c = idx % w
                scl[r, c] = cls.SCL_CLOUD_HIGH_PROB
                red[r, c] = 8000
                nir[r, c] = 8500
                green[r, c] = 8000
                swir[r, c] = 7000

        return red, nir, green, swir, scl

