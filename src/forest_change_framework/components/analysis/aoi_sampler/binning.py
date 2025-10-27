"""Binning and filtering logic for AOIs based on loss statistics."""

import logging
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def validate_bins_config(bins: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validate that bins configuration is valid.

    Checks:
    - Each bin has 'name', 'min', 'max'
    - Bins don't overlap
    - Bins cover reasonable range
    - min < max for each bin

    Args:
        bins: List of bin dicts with keys: name, min, max

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not bins:
        return False, "bins list is empty"

    if not isinstance(bins, list):
        return False, "bins must be a list"

    required_keys = {"name", "min", "max"}

    for i, bin_def in enumerate(bins):
        if not isinstance(bin_def, dict):
            return False, f"bin {i} is not a dict"

        missing_keys = required_keys - set(bin_def.keys())
        if missing_keys:
            return False, f"bin {i} missing keys: {missing_keys}"

        min_val = bin_def["min"]
        max_val = bin_def["max"]

        if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
            return False, f"bin {i} min/max must be numeric"

        if min_val >= max_val:
            return False, f"bin {i}: min ({min_val}) >= max ({max_val})"

        if min_val < 0 or max_val > 100:
            return False, f"bin {i}: values must be in range [0, 100], got [{min_val}, {max_val}]"

    # Check for overlaps
    sorted_bins = sorted(bins, key=lambda b: b["min"])
    for i in range(len(sorted_bins) - 1):
        if sorted_bins[i]["max"] > sorted_bins[i + 1]["min"]:
            return False, (
                f"bins overlap: '{sorted_bins[i]['name']}' "
                f"[{sorted_bins[i]['min']}, {sorted_bins[i]['max']}] "
                f"overlaps '{sorted_bins[i+1]['name']}' "
                f"[{sorted_bins[i+1]['min']}, {sorted_bins[i+1]['max']}]"
            )

    logger.info(f"Bins configuration is valid: {len(bins)} bins")
    return True, ""


def get_bin_for_value(value: float, bins: List[Dict[str, Any]]) -> Optional[str]:
    """
    Determine which bin a value falls into.

    Args:
        value: Numeric value (e.g., loss percentage)
        bins: List of bin dicts with keys: name, min, max

    Returns:
        Bin name if value falls into a bin, None otherwise
    """
    for bin_def in bins:
        if bin_def["min"] <= value < bin_def["max"]:
            return bin_def["name"]

        # For the last bin, include the max boundary
        if bin_def["max"] == 100 and bin_def["min"] <= value <= bin_def["max"]:
            return bin_def["name"]

    return None


def bin_aois(
    aois: List[Dict[str, Any]],
    bins: List[Dict[str, Any]],
    loss_key: str = "loss_percentage",
) -> List[Dict[str, Any]]:
    """
    Assign bin category to each AOI based on loss percentage.

    Args:
        aois: List of AOI dicts with statistics
        bins: List of bin dicts with keys: name, min, max
        loss_key: Key in AOI dict containing loss percentage (default: loss_percentage)

    Returns:
        List of AOIs with added 'bin_category' field
    """
    binned_aois = []

    for aoi in aois:
        loss_value = aoi.get(loss_key, 0)
        bin_name = get_bin_for_value(loss_value, bins)

        aoi_copy = aoi.copy()
        aoi_copy["bin_category"] = bin_name or "unclassified"

        binned_aois.append(aoi_copy)

    return binned_aois


def filter_by_validity(
    aois: List[Dict[str, Any]],
    validity_threshold: float = 0.8,
    validity_key: str = "data_validity",
    keep_invalid: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split AOIs into valid and invalid based on data validity threshold.

    Args:
        aois: List of AOI dicts with statistics
        validity_threshold: Minimum validity (0-100) for AOI to be included
        validity_key: Key in AOI dict containing validity percentage
        keep_invalid: If True, also return invalid AOIs marked with 'validity_status'

    Returns:
        Tuple of (valid_aois, invalid_aois)
        - valid_aois: List of AOIs passing validity threshold
        - invalid_aois: Empty list or list of excluded AOIs (if keep_invalid=True)
    """
    valid_aois = []
    invalid_aois = []

    for aoi in aois:
        validity_pct = aoi.get(validity_key, 0)

        # Convert threshold (0-1) to percentage (0-100)
        threshold_pct = validity_threshold * 100 if validity_threshold <= 1.0 else validity_threshold

        if validity_pct >= threshold_pct:
            aoi_copy = aoi.copy()
            aoi_copy["validity_status"] = "valid"
            valid_aois.append(aoi_copy)
        else:
            if keep_invalid:
                aoi_copy = aoi.copy()
                aoi_copy["validity_status"] = "invalid"
                invalid_aois.append(aoi_copy)

    return valid_aois, invalid_aois


def get_bin_summary(binned_aois: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get count of AOIs per bin category.

    Args:
        binned_aois: List of AOIs with 'bin_category' field

    Returns:
        Dictionary mapping bin_name -> count
    """
    summary = {}

    for aoi in binned_aois:
        bin_cat = aoi.get("bin_category", "unclassified")
        summary[bin_cat] = summary.get(bin_cat, 0) + 1

    return summary


def apply_binning_and_filtering(
    aois: List[Dict[str, Any]],
    bins: List[Dict[str, Any]],
    validity_threshold: float = 0.8,
    keep_invalid_aois: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Apply both binning and validity filtering to AOIs.

    Args:
        aois: List of AOI dicts with statistics
        bins: List of bin dicts
        validity_threshold: Minimum validity percentage for inclusion
        keep_invalid_aois: Whether to keep (but mark) invalid AOIs

    Returns:
        Tuple of:
        - Processed AOIs list
        - Summary dict with counts and statistics
    """
    # Validate bins
    is_valid, error_msg = validate_bins_config(bins)
    if not is_valid:
        raise ValueError(f"Invalid bins configuration: {error_msg}")

    # Bin the AOIs
    binned_aois = bin_aois(aois, bins)

    # Filter by validity
    valid_aois, invalid_aois = filter_by_validity(
        binned_aois,
        validity_threshold=validity_threshold,
        keep_invalid=keep_invalid_aois,
    )

    # Get bin summary only from VALID AOIs
    bin_summary = get_bin_summary(valid_aois)

    # Prepare all output AOIs
    if keep_invalid_aois:
        output_aois = valid_aois + invalid_aois
    else:
        output_aois = valid_aois

    # Create summary
    summary = {
        "total_aois": len(aois),
        "valid_aois": len(valid_aois),
        "invalid_aois": len(invalid_aois),
        "excluded_aois": len(aois) - len(valid_aois),
        "validity_threshold": validity_threshold,
        "bin_summary": bin_summary,
        "bins_applied": len(bins),
    }

    logger.info(
        f"Binning and filtering complete: {len(valid_aois)} valid, "
        f"{len(invalid_aois)} invalid, bin_summary={bin_summary}"
    )

    return output_aois, summary
