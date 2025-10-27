"""Visualization module for AOI sampler - generates yearly loss maps."""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import to_rgba
except ImportError:
    plt = None

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
except ImportError:
    ccrs = None
    cfeature = None

try:
    import geopandas as gpd
except ImportError:
    gpd = None

try:
    from shapely.geometry import shape
except ImportError:
    shape = None

logger = logging.getLogger(__name__)


# Color mapping for loss bins
BIN_COLORS = {
    "no_loss": (0.2, 0.8, 0.2),  # Green
    "low_loss": (1.0, 1.0, 0.0),  # Yellow
    "medium_loss": (1.0, 0.65, 0.0),  # Orange
    "high_loss": (1.0, 0.0, 0.0),  # Red
    "unclassified": (0.5, 0.5, 0.5),  # Gray
}


def create_yearly_maps(
    geojson_data: Dict[str, Any],
    output_folder: Path,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    dpi: int = 150,
) -> Dict[int, str]:
    """
    Create PNG maps for each year showing AOIs with loss.

    Args:
        geojson_data: GeoJSON dict with features containing loss_by_year
        output_folder: Where to save PNG files
        bbox: Optional bounding box (minx, miny, maxx, maxy) to zoom to
        dpi: Resolution in dots per inch

    Returns:
        Dictionary mapping year -> PNG file path
    """
    if plt is None or ccrs is None or cfeature is None or shape is None:
        raise ImportError(
            "matplotlib, cartopy, and shapely required for visualization. "
            "Install with: pip install matplotlib cartopy shapely"
        )

    output_folder.mkdir(parents=True, exist_ok=True)

    # Extract all years from features
    all_years = set()
    for feature in geojson_data.get("features", []):
        loss_by_year = feature.get("properties", {}).get("loss_by_year", {})
        all_years.update(loss_by_year.keys())

    if not all_years:
        logger.warning("No loss data found in features")
        return {}

    all_years = sorted(all_years)
    year_map_paths = {}

    logger.info(f"Creating yearly maps for {len(all_years)} years: {min(all_years)}-{max(all_years)}")

    # Convert bbox dict to tuple if provided
    bbox_tuple = None
    if bbox:
        bbox_tuple = (bbox.get("minx"), bbox.get("miny"), bbox.get("maxx"), bbox.get("maxy"))

    # Create map for each year
    for year in all_years:
        logger.debug(f"Creating map for year {year}")

        # Filter features with loss in this year
        year_features = []
        for feature in geojson_data.get("features", []):
            loss_by_year = feature.get("properties", {}).get("loss_by_year", {})
            if year in loss_by_year and loss_by_year[year] > 0:
                year_features.append(feature)

        if not year_features:
            logger.debug(f"No loss data for year {year}, skipping map")
            continue

        # Create map
        map_path = _create_single_year_map(
            year, year_features, output_folder, bbox_tuple, dpi
        )

        if map_path:
            year_map_paths[year] = str(map_path)

    logger.info(f"Created {len(year_map_paths)} yearly maps")
    return year_map_paths


def _create_single_year_map(
    year: int,
    features: List[Dict[str, Any]],
    output_folder: Path,
    bbox: Optional[Tuple[float, float, float, float]],
    dpi: int,
) -> Optional[Path]:
    """
    Create a single year map.

    Args:
        year: Year to map
        features: GeoJSON features with loss in this year
        output_folder: Output directory
        bbox: Optional bounding box to zoom to
        dpi: Resolution

    Returns:
        Path to saved PNG file or None if failed
    """
    try:
        # Calculate map extent
        if bbox and all(v is not None for v in bbox):
            extent = bbox  # (minx, miny, maxx, maxy)
        else:
            # Calculate from features
            all_coords = []
            for feature in features:
                coords = feature.get("geometry", {}).get("coordinates", [])
                if coords:
                    all_coords.extend(_extract_coords(coords))

            if not all_coords:
                return None

            minx = min(c[0] for c in all_coords)
            maxx = max(c[0] for c in all_coords)
            miny = min(c[1] for c in all_coords)
            maxy = max(c[1] for c in all_coords)

            # Add buffer
            buffer = max((maxx - minx) * 0.1, (maxy - miny) * 0.1)
            extent = (minx - buffer, miny - buffer, maxx + buffer, maxy + buffer)

        # Create figure with Cartopy projection
        fig = plt.figure(figsize=(16, 10), dpi=dpi)
        ax = plt.axes(projection=ccrs.PlateCarree())

        # Set extent and add features
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.coastlines(resolution="10m", linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.add_feature(cfeature.LAND, facecolor="lightgray", alpha=0.3)
        ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.2)
        ax.gridlines(draw_labels=True, alpha=0.3)

        # Plot features colored by bin
        for feature in features:
            geom = shape(feature["geometry"])
            props = feature.get("properties", {})
            bin_cat = props.get("bin_category", "unclassified")
            loss_year = props.get("loss_by_year", {}).get(year, 0)

            color = BIN_COLORS.get(bin_cat, BIN_COLORS["unclassified"])
            alpha = min(0.5 + (loss_year / 10), 1.0)  # Scale alpha by loss percentage

            # Plot polygon
            x, y = geom.exterior.xy
            ax.fill(
                x,
                y,
                color=color,
                alpha=alpha,
                transform=ccrs.PlateCarree(),
                edgecolor="black",
                linewidth=0.1,
            )

        # Add legend
        legend_elements = [
            mpatches.Patch(
                facecolor=BIN_COLORS["no_loss"],
                edgecolor="black",
                alpha=0.5,
                label="No Loss",
            ),
            mpatches.Patch(
                facecolor=BIN_COLORS["low_loss"],
                edgecolor="black",
                alpha=0.5,
                label="Low Loss (0-15%)",
            ),
            mpatches.Patch(
                facecolor=BIN_COLORS["medium_loss"],
                edgecolor="black",
                alpha=0.5,
                label="Medium Loss (15-30%)",
            ),
            mpatches.Patch(
                facecolor=BIN_COLORS["high_loss"],
                edgecolor="black",
                alpha=0.5,
                label="High Loss (30%+)",
            ),
        ]
        ax.legend(handles=legend_elements, loc="lower left", fontsize=10)

        # Add title
        num_aois = len(features)
        ax.set_title(
            f"Forest Loss Distribution - Year {year}\n({num_aois} AOIs with loss)",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )

        # Save figure
        output_path = output_folder / f"loss_map_{year:04d}.png"
        fig.savefig(output_path, bbox_inches="tight", dpi=dpi)
        plt.close(fig)

        logger.debug(f"Saved map: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to create map for year {year}: {str(e)}")
        return None


def _extract_coords(coords: list) -> list:
    """
    Recursively extract coordinate tuples from nested geometry coordinates.

    Args:
        coords: Nested list of coordinates

    Returns:
        Flat list of (lon, lat) tuples
    """
    result = []

    def extract(obj):
        if isinstance(obj, (int, float)):
            return
        if isinstance(obj, list):
            if len(obj) == 2 and isinstance(obj[0], (int, float)):
                result.append((obj[0], obj[1]))
            else:
                for item in obj:
                    extract(item)

    extract(coords)
    return result


def generate_map_summary(
    year_map_paths: Dict[int, str], output_folder: Path
) -> Path:
    """
    Generate an HTML index file linking to all yearly maps.

    Args:
        year_map_paths: Dict mapping year -> PNG path
        output_folder: Output directory

    Returns:
        Path to HTML index file
    """
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Forest Loss Maps by Year</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #2196F3;
            padding-bottom: 10px;
        }
        .map-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .map-item {
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .map-item img {
            width: 100%;
            height: auto;
            display: block;
        }
        .map-title {
            padding: 10px;
            background-color: #f9f9f9;
            font-weight: bold;
            text-align: center;
        }
        .legend {
            margin-top: 20px;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 4px;
        }
        .legend h3 {
            margin-top: 0;
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 10px;
        }
        .legend-color {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 8px;
            vertical-align: middle;
            border: 1px solid black;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌍 Forest Loss Maps by Year</h1>

        <div class="legend">
            <h3>Loss Categories:</h3>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(51, 204, 51, 0.5);"></div>
                No Loss (0-5%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(255, 255, 0, 0.5);"></div>
                Low Loss (5-15%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(255, 166, 0, 0.5);"></div>
                Medium Loss (15-30%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(255, 0, 0, 0.5);"></div>
                High Loss (30%+)
            </div>
        </div>

        <p>
            Each map shows Areas of Interest (AOIs) that experienced forest loss in that year.
            Color indicates severity category. Opacity increases with loss percentage.
        </p>

        <div class="map-grid">
"""

    for year in sorted(year_map_paths.keys()):
        map_path = year_map_paths[year]
        filename = Path(map_path).name

        html_content += f"""        <div class="map-item">
                <div class="map-title">Year {year}</div>
                <img src="{filename}" alt="Loss map for {year}">
            </div>
"""

    html_content += """        </div>
    </div>
</body>
</html>
"""

    html_path = output_folder / "loss_maps_index.html"
    with open(html_path, "w") as f:
        f.write(html_content)

    logger.info(f"Generated map index: {html_path}")
    return html_path
