"""Stratified sampling utilities for extracting balanced AOI samples by year and loss bin."""

import logging
import random
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def group_aois_by_year_and_bin(geojson_data: Dict[str, Any]) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """
    Group AOIs from GeoJSON by year and loss bin category.

    Args:
        geojson_data: GeoJSON FeatureCollection from AOI sampler

    Returns:
        Nested dict: {year: {bin_category: [features]}}

    Example:
        >>> geojson = {"features": [...]}
        >>> grouped = group_aois_by_year_and_bin(geojson)
        >>> grouped[2010]["low_loss"]  # Get all low_loss AOIs from 2010
    """
    grouped = {}

    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        bin_category = props.get("bin_category")
        loss_by_year = props.get("loss_by_year", {})

        # Extract years from loss_by_year keys
        for year_str in loss_by_year.keys():
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse year: {year_str}")
                continue

            # Initialize nested structure if needed
            if year not in grouped:
                grouped[year] = {}
            if bin_category not in grouped[year]:
                grouped[year][bin_category] = []

            # Add feature to this year/bin group
            grouped[year][bin_category].append(feature)

    logger.info(f"Grouped {len(geojson_data.get('features', []))} AOIs into {len(grouped)} years")
    return grouped


def select_stratified_samples(
    grouped_aois: Dict[int, Dict[str, List[Dict[str, Any]]]], samples_per_bin: int
) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """
    Select stratified samples: N samples per bin, distributed across years.

    For each loss bin, randomly selects samples_per_bin AOIs total, distributed
    across available years. This ensures balanced representation of each loss
    category while maintaining year distribution.

    Args:
        grouped_aois: Output from group_aois_by_year_and_bin()
        samples_per_bin: Number of samples to select per loss bin

    Returns:
        Dict with same structure as input, but with randomly selected samples

    Example:
        >>> grouped = {...}
        >>> selected = select_stratified_samples(grouped, samples_per_bin=10)
        >>> # Now selected has exactly 10 samples per bin
    """
    selected = {}
    bin_counts = {}

    # First pass: count samples per bin across all years
    for year, bins in grouped_aois.items():
        for bin_cat, features in bins.items():
            if bin_cat not in bin_counts:
                bin_counts[bin_cat] = 0
            bin_counts[bin_cat] += len(features)

    logger.info(f"Samples per bin available: {bin_counts}")

    # Second pass: select samples per bin, distributed across years
    for bin_cat, total_count in bin_counts.items():
        bin_samples_by_year = {}

        # Collect all AOIs for this bin across all years
        all_bin_aois = []
        bin_year_map = {}
        for year, bins in grouped_aois.items():
            if bin_cat in bins:
                for feature in bins[bin_cat]:
                    all_bin_aois.append(feature)
                    bin_year_map[id(feature)] = year

        if not all_bin_aois:
            logger.warning(f"No AOIs found for bin: {bin_cat}")
            continue

        # Randomly select samples_per_bin AOIs from this bin
        num_to_select = min(samples_per_bin, len(all_bin_aois))
        selected_features = random.sample(all_bin_aois, num_to_select)

        # Organize selected features by year
        for feature in selected_features:
            year = bin_year_map[id(feature)]
            if year not in bin_samples_by_year:
                bin_samples_by_year[year] = []
            bin_samples_by_year[year].append(feature)

        # Add to selected dict
        for year, features in bin_samples_by_year.items():
            if year not in selected:
                selected[year] = {}
            selected[year][bin_cat] = features

    logger.info(f"Selected {sum(len(f) for y in selected.values() for f in y.values())} samples total")
    return selected


def balance_samples_across_years(
    selected_aois: Dict[int, Dict[str, List[Dict[str, Any]]]], samples_per_bin: int
) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """
    Ensure samples are distributed equally across years where possible.

    Adjusts selection to balance representation across years within each bin.
    If a bin has fewer samples than years, distributes available samples.
    If a bin has more samples than years, distributes equally.

    Args:
        selected_aois: Output from select_stratified_samples()
        samples_per_bin: Target number of samples per bin

    Returns:
        Rebalanced dict with better year distribution

    Example:
        >>> selected = {...}
        >>> balanced = balance_samples_across_years(selected, samples_per_bin=10)
    """
    balanced = {}
    years = sorted(selected_aois.keys())

    if not years:
        logger.warning("No years found in selected AOIs")
        return balanced

    num_years = len(years)

    # For each bin, redistribute samples across years
    all_bins = set()
    for year_data in selected_aois.values():
        all_bins.update(year_data.keys())

    for bin_cat in all_bins:
        # Collect all samples for this bin
        all_bin_samples = []
        for year in years:
            if year in selected_aois and bin_cat in selected_aois[year]:
                all_bin_samples.extend(selected_aois[year][bin_cat])

        if not all_bin_samples:
            continue

        # Distribute samples across years
        samples_per_year = len(all_bin_samples) // num_years
        remainder = len(all_bin_samples) % num_years

        # Randomly shuffle to distribute remainder fairly
        random.shuffle(all_bin_samples)

        idx = 0
        for i, year in enumerate(years):
            # Some years get one extra sample if there's a remainder
            n_samples = samples_per_year + (1 if i < remainder else 0)

            if n_samples > 0:
                if year not in balanced:
                    balanced[year] = {}
                balanced[year][bin_cat] = all_bin_samples[idx : idx + n_samples]
                idx += n_samples

    logger.info("Rebalanced samples across years")
    return balanced


def create_sample_manifest(selected_aois: Dict[int, Dict[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
    """
    Create a manifest of selected samples with unique IDs and metadata.

    Generates a flat list of samples with columns:
    sample_id, aoi_id, year, loss_bin, minx, miny, maxx, maxy, loss_percentage

    Args:
        selected_aois: Output from balance_samples_across_years()

    Returns:
        List of dicts, one per sample, with all metadata

    Example:
        >>> balanced = {...}
        >>> manifest = create_sample_manifest(balanced)
        >>> len(manifest)  # Total number of samples
    """
    manifest = []
    sample_counter = 1

    for year in sorted(selected_aois.keys()):
        bins = selected_aois[year]
        for bin_cat in sorted(bins.keys()):
            for feature in bins[bin_cat]:
                sample_id = f"{sample_counter:06d}"
                props = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                # Extract bbox from properties or geometry
                minx = props.get("minx")
                miny = props.get("miny")
                maxx = props.get("maxx")
                maxy = props.get("maxy")

                # If bbox not in properties, extract from geometry
                if minx is None or miny is None or maxx is None or maxy is None:
                    if geometry.get("type") == "Polygon":
                        coords = geometry.get("coordinates", [[]])[0]
                        if coords:
                            xs = [c[0] for c in coords]
                            ys = [c[1] for c in coords]
                            minx = min(xs)
                            miny = min(ys)
                            maxx = max(xs)
                            maxy = max(ys)
                    elif geometry.get("type") == "Point":
                        x, y = geometry.get("coordinates", [None, None])
                        minx = maxx = x
                        miny = maxy = y

                # Get loss for this specific year
                loss_by_year = props.get("loss_by_year", {})
                loss_percentage = loss_by_year.get(str(year), 0.0)

                sample = {
                    "sample_id": sample_id,
                    "aoi_id": props.get("cell_id", f"unknown_{year}_{sample_counter}"),
                    "year": year,
                    "loss_bin": bin_cat,
                    "minx": minx,
                    "miny": miny,
                    "maxx": maxx,
                    "maxy": maxy,
                    "loss_percentage": float(loss_percentage),
                    # Include all properties from input for metadata
                    "input_properties": props,
                }

                manifest.append(sample)
                sample_counter += 1

    logger.info(f"Created manifest with {len(manifest)} samples")
    return manifest
