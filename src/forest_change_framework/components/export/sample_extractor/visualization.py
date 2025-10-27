"""Map visualization with sample locations - generates PNG with pins for all samples."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_sample_map(
    manifest: List[Dict[str, Any]], output_path: str, title: str = "Sample Locations"
) -> None:
    """
    Create a PNG map visualization showing all sample locations with pins.

    Uses folium to create an interactive map centered on sample locations,
    with color-coded pins based on loss bin category.

    Args:
        manifest: List of sample dicts with minx, miny, maxx, maxy, loss_bin, sample_id
        output_path: Path where PNG map will be saved
        title: Title for the map (default: "Sample Locations")

    Raises:
        ImportError: If folium not installed
        ValueError: If manifest is empty or missing required fields
        IOError: If file cannot be written

    Example:
        >>> manifest = [
        ...     {"sample_id": "001", "minx": -50.0, "miny": -20.0, "maxx": -49.9, "maxy": -19.9, "loss_bin": "high_loss"},
        ...     {"sample_id": "002", "minx": -48.0, "miny": -22.0, "maxx": -47.9, "maxy": -21.9, "loss_bin": "low_loss"},
        ... ]
        >>> create_sample_map(manifest, "samples_map.png", title="Forest Loss Samples")
    """
    try:
        import folium
        from folium.plugins import HeatMap
    except ImportError:
        raise ImportError(
            "folium required for map visualization. Install with: pip install folium"
        )

    if not manifest:
        raise ValueError("Manifest must contain at least one sample")

    # Validate required fields
    required_fields = {"sample_id", "minx", "miny", "maxx", "maxy", "loss_bin"}
    for sample in manifest:
        missing = required_fields - set(sample.keys())
        if missing:
            raise ValueError(f"Sample {sample.get('sample_id')} missing fields: {missing}")

    # Calculate center of map
    all_miny = [s["miny"] for s in manifest]
    all_maxy = [s["maxy"] for s in manifest]
    all_minx = [s["minx"] for s in manifest]
    all_maxx = [s["maxx"] for s in manifest]

    center_lat = (min(all_miny) + max(all_maxy)) / 2
    center_lon = (min(all_minx) + max(all_maxx)) / 2

    # Create base map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="OpenStreetMap")

    # Color mapping for loss bins
    color_map = {
        "no_loss": "green",
        "low_loss": "yellow",
        "medium_loss": "orange",
        "high_loss": "red",
    }

    # Add pins for each sample
    for sample in manifest:
        sample_id = sample["sample_id"]
        loss_bin = sample.get("loss_bin", "unknown")
        color = color_map.get(loss_bin, "gray")

        # Use center of bbox as pin location
        lat = (sample["miny"] + sample["maxy"]) / 2
        lon = (sample["minx"] + sample["maxx"]) / 2

        # Create popup with sample info
        popup_text = (
            f"<b>Sample {sample_id}</b><br>"
            f"Loss Bin: {loss_bin}<br>"
            f"Year: {sample.get('year', 'N/A')}<br>"
            f"Loss %: {sample.get('loss_percentage', 'N/A'):.2f}%"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            popup=popup_text,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
            tooltip=f"Sample {sample_id}",
        ).add_to(m)

    # Add title
    title_html = (
        f'<div style="position: fixed; '
        f'top: 10px; left: 50px; width: 300px; height: 60px; '
        f'background-color: white; border:2px solid grey; z-index:9999; '
        f'font-size:16px; font-weight: bold; padding: 10px;">'
        f'{title}<br>'
        f'{len(manifest)} samples'
        f"</div>"
    )
    m.get_root().html.add_child(folium.Element(title_html))

    # Add legend
    legend_html = (
        '<div style="position: fixed; '
        'bottom: 50px; left: 50px; width: 180px; height: 180px; '
        'background-color: white; border:2px solid grey; z-index:9999; '
        'font-size:12px; padding: 10px;">'
        '<b>Loss Categories</b><br>'
        '<i style="background: green; width: 18px; height: 18px; '
        'float: left; margin-right: 8px; border-radius: 50%;"></i>No Loss<br>'
        '<i style="background: yellow; width: 18px; height: 18px; '
        'float: left; margin-right: 8px; border-radius: 50%;"></i>Low Loss<br>'
        '<i style="background: orange; width: 18px; height: 18px; '
        'float: left; margin-right: 8px; border-radius: 50%;"></i>Medium Loss<br>'
        '<i style="background: red; width: 18px; height: 18px; '
        'float: left; margin-right: 8px; border-radius: 50%;"></i>High Loss<br>'
        "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save map
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Save as HTML first
        html_path = str(output_file.with_suffix(".html"))
        m.save(html_path)
        logger.info(f"Saved interactive map to: {html_path}")

        # Convert HTML to PNG using selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            import tempfile
            import time

            # Create temporary HTML file
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(options=chrome_options)
            driver.get(f"file:///{Path(html_path).resolve()}")
            time.sleep(2)  # Wait for map to render

            # Take screenshot
            driver.save_screenshot(str(output_file))
            driver.quit()

            logger.info(f"Saved PNG map to: {output_path}")

        except ImportError:
            logger.warning(
                "Selenium/ChromeDriver not available for PNG conversion. "
                f"Interactive HTML map saved instead: {html_path}"
            )
            # Still return success since HTML map was created
            return

    except Exception as e:
        raise IOError(f"Failed to create map visualization: {e}")


def create_sample_summary_map(
    manifest: List[Dict[str, Any]], output_path: str
) -> None:
    """
    Create a PNG map using matplotlib with OpenStreetMap basemap.

    Args:
        manifest: List of sample dicts with spatial information
        output_path: Path where PNG map will be saved
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        raise ImportError(
            "matplotlib required for map visualization. Install with: pip install matplotlib"
        )

    # Try to import contextily for basemap
    has_contextily = True
    try:
        import contextily as ctx
    except ImportError:
        has_contextily = False
        logger.warning(
            "contextily not available - map will be plotted without basemap. "
            "For map tiles, install: pip install contextily"
        )

    if not manifest:
        raise ValueError("Manifest must contain at least one sample")

    # Calculate bounds
    all_miny = [s["miny"] for s in manifest]
    all_maxy = [s["maxy"] for s in manifest]
    all_minx = [s["minx"] for s in manifest]
    all_maxx = [s["maxx"] for s in manifest]

    min_lat = min(all_miny) - 1
    max_lat = max(all_maxy) + 1
    min_lon = min(all_minx) - 1
    max_lon = max(all_maxx) + 1

    # Calculate proper aspect ratio for latitude/longitude
    # At equator: 1 degree longitude ≈ 111 km, 1 degree latitude ≈ 111 km
    # But we need to account for latitude distortion in map projection
    lat_center = (min_lat + max_lat) / 2
    import math
    lon_scale = math.cos(math.radians(lat_center))  # Correction for latitude

    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    aspect_ratio = (lat_range / lon_range) / lon_scale

    # Create figure with proper aspect ratio
    fig_width = 14
    fig_height = fig_width * aspect_ratio
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Color mapping
    color_map = {
        "no_loss": "green",
        "low_loss": "yellow",
        "medium_loss": "orange",
        "high_loss": "red",
    }

    # Set limits first
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)

    # Add basemap tiles if contextily is available
    if has_contextily:
        try:
            import contextily as ctx
            # Add OpenStreetMap tiles (Leaflet.Providers)
            ctx.add_basemap(
                ax,
                crs="EPSG:4326",
                source=ctx.providers.OpenStreetMap.Mapnik,
                zoom=8,
                attribution=False,
            )
            logger.debug("Added OpenStreetMap basemap tiles")
        except Exception as e:
            logger.warning(f"Failed to add basemap tiles: {e}")

    # Plot each sample as a rectangle with center pin
    for sample in manifest:
        sample_id = sample["sample_id"]
        loss_bin = sample.get("loss_bin", "unknown")
        color = color_map.get(loss_bin, "gray")

        # Draw bounding box
        minx = sample["minx"]
        miny = sample["miny"]
        maxx = sample["maxx"]
        maxy = sample["maxy"]

        width = maxx - minx
        height = maxy - miny
        rect = mpatches.Rectangle(
            (minx, miny),
            width,
            height,
            linewidth=2,
            edgecolor=color,
            facecolor=color,
            alpha=0.3,
            zorder=4,
        )
        ax.add_patch(rect)

        # Add center pin with better visibility
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2
        ax.plot(
            center_lon,
            center_lat,
            marker="o",
            color=color,
            markersize=10,
            zorder=5,
            markeredgecolor="black",
            markeredgewidth=1,
        )

        # Add year label with background for visibility
        year = sample.get("year", "?")
        ax.text(
            center_lon,
            center_lat + 0.05,
            str(year),
            fontsize=10,
            ha="center",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.9, edgecolor="black"),
            zorder=6,
        )

    # Labels and title
    ax.set_xlabel("Longitude", fontsize=12, fontweight="bold")
    ax.set_ylabel("Latitude", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Sample Locations ({len(manifest)} samples)", fontsize=14, fontweight="bold"
    )
    ax.grid(True, alpha=0.3, linestyle="--")

    # Create legend
    legend_elements = [
        mpatches.Patch(color="green", label="No Loss"),
        mpatches.Patch(color="yellow", label="Low Loss"),
        mpatches.Patch(color="orange", label="Medium Loss"),
        mpatches.Patch(color="red", label="High Loss"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=10)

    # Save figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        fig.savefig(str(output_file), dpi=150, bbox_inches="tight")
        logger.info(f"Saved PNG map to: {output_path}")
        plt.close(fig)

    except Exception as e:
        raise IOError(f"Failed to save PNG map: {e}")
