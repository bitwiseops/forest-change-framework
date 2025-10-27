"""Statistics calculation functions for forest loss and data validity metrics."""

import logging
from typing import Dict, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

# Hansen lossyear band: 0=no loss, 1-21 represents year offset from 2000
HANSEN_BASE_YEAR = 2000
HANSEN_MAX_LOSS_YEAR = 21


def calculate_validity(datamask_array: np.ndarray) -> float:
    """
    Calculate percentage of valid pixels in the array.

    Valid pixels have datamask value of 1. Values of 0 indicate nodata/invalid.

    Args:
        datamask_array: 2D numpy array from Hansen datamask band

    Returns:
        Validity percentage (0-100)
    """
    if datamask_array.size == 0:
        return 0.0

    valid_count = np.sum(datamask_array == 1)
    validity_pct = (valid_count / datamask_array.size) * 100

    return float(validity_pct)


def calculate_loss_percentage(
    lossyear_array: np.ndarray, datamask_array: np.ndarray
) -> float:
    """
    Calculate percentage of pixels with forest loss.

    Loss is indicated by lossyear > 0. Calculation is relative to valid pixels only.

    Args:
        lossyear_array: 2D numpy array from Hansen lossyear band
        datamask_array: 2D numpy array from Hansen datamask band

    Returns:
        Loss percentage (0-100) relative to valid pixels
    """
    # Count valid pixels
    valid_mask = datamask_array == 1
    valid_count = np.sum(valid_mask)

    if valid_count == 0:
        return 0.0

    # Count loss pixels (lossyear > 0) among valid pixels
    loss_mask = (lossyear_array > 0) & valid_mask
    loss_count = np.sum(loss_mask)

    loss_pct = (loss_count / valid_count) * 100

    return float(loss_pct)


def calculate_loss_by_year(
    lossyear_array: np.ndarray, datamask_array: np.ndarray
) -> Dict[int, float]:
    """
    Calculate percentage of pixels with loss for each year.

    Hansen lossyear band: 0=no loss, 1-21 represents years 2000-2020.

    Args:
        lossyear_array: 2D numpy array from Hansen lossyear band
        datamask_array: 2D numpy array from Hansen datamask band

    Returns:
        Dictionary mapping year -> loss_percentage
        Example: {2000: 0.5, 2001: 1.2, ...}
    """
    # Count valid pixels
    valid_mask = datamask_array == 1
    valid_count = np.sum(valid_mask)

    if valid_count == 0:
        return {}

    loss_by_year = {}

    # For each possible loss year value (1-21)
    for year_offset in range(1, HANSEN_MAX_LOSS_YEAR + 1):
        year = HANSEN_BASE_YEAR + year_offset

        # Count pixels with this loss year
        year_loss_mask = (lossyear_array == year_offset) & valid_mask
        year_loss_count = np.sum(year_loss_mask)

        if year_loss_count > 0:
            year_loss_pct = (year_loss_count / valid_count) * 100
            loss_by_year[year] = float(year_loss_pct)

    return loss_by_year


def calculate_treecover_stats(
    treecover_array: np.ndarray, datamask_array: np.ndarray
) -> Dict[str, float]:
    """
    Calculate tree cover statistics (mean, median, std).

    Args:
        treecover_array: 2D numpy array from Hansen treecover2000 band (0-100)
        datamask_array: 2D numpy array from Hansen datamask band

    Returns:
        Dictionary with keys: mean, median, std, min, max
        Returns empty dict if no valid pixels
    """
    # Mask valid pixels
    valid_mask = datamask_array == 1
    valid_treecover = treecover_array[valid_mask]

    if len(valid_treecover) == 0:
        return {}

    return {
        "mean": float(np.mean(valid_treecover)),
        "median": float(np.median(valid_treecover)),
        "std": float(np.std(valid_treecover)),
        "min": float(np.min(valid_treecover)),
        "max": float(np.max(valid_treecover)),
    }


def calculate_cell_statistics(
    treecover_data: np.ndarray,
    lossyear_data: np.ndarray,
    datamask_data: np.ndarray,
    include_treecover_stats: bool = False,
    include_loss_by_year: bool = True,
) -> Dict[str, Any]:
    """
    Calculate all statistics for a single grid cell.

    Args:
        treecover_data: 2D array from treecover2000 band
        lossyear_data: 2D array from lossyear band
        datamask_data: 2D array from datamask band
        include_treecover_stats: Whether to include tree cover mean/median/std
        include_loss_by_year: Whether to include loss breakdown by year

    Returns:
        Dictionary with calculated statistics
    """
    stats = {
        "loss_percentage": calculate_loss_percentage(lossyear_data, datamask_data),
        "data_validity": calculate_validity(datamask_data),
    }

    if include_loss_by_year:
        stats["loss_by_year"] = calculate_loss_by_year(lossyear_data, datamask_data)

    if include_treecover_stats:
        treecover_stats = calculate_treecover_stats(treecover_data, datamask_data)
        if treecover_stats:
            stats["treecover"] = treecover_stats

    return stats


def aggregate_statistics(all_stats: list) -> Dict[str, Any]:
    """
    Aggregate statistics from multiple cells.

    Args:
        all_stats: List of statistics dicts from individual cells

    Returns:
        Aggregated statistics
    """
    if not all_stats:
        return {}

    loss_percentages = [s.get("loss_percentage", 0) for s in all_stats]
    validities = [s.get("data_validity", 0) for s in all_stats]

    aggregated = {
        "total_cells": len(all_stats),
        "mean_loss_percentage": float(np.mean(loss_percentages)),
        "median_loss_percentage": float(np.median(loss_percentages)),
        "std_loss_percentage": float(np.std(loss_percentages)),
        "min_loss_percentage": float(np.min(loss_percentages)),
        "max_loss_percentage": float(np.max(loss_percentages)),
        "mean_data_validity": float(np.mean(validities)),
        "median_data_validity": float(np.median(validities)),
    }

    return aggregated
