"""Metadata management for sample extraction - export and validation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None


def create_metadata_dict(manifest_list: List[Dict[str, Any]], patches_dir: str) -> Dict[str, Any]:
    """
    Convert manifest list to a nested dict structure suitable for JSON export.

    Args:
        manifest_list: List of sample dicts from create_sample_manifest()
        patches_dir: Path to directory containing extracted patches

    Returns:
        Dict with metadata ready for JSON export

    Example:
        >>> manifest = [{"sample_id": "000001", ...}]
        >>> meta_dict = create_metadata_dict(manifest, "patches/")
        >>> meta_dict["samples"][0]  # Access first sample
    """
    metadata = {
        "metadata": {
            "total_samples": len(manifest_list),
            "patches_directory": str(patches_dir),
        },
        "samples": [],
    }

    for sample in manifest_list:
        sample_dict = {
            "sample_id": sample.get("sample_id"),
            "aoi_id": sample.get("aoi_id"),
            "year": sample.get("year"),
            "loss_bin": sample.get("loss_bin"),
            "bbox": {
                "minx": sample.get("minx"),
                "miny": sample.get("miny"),
                "maxx": sample.get("maxx"),
                "maxy": sample.get("maxy"),
            },
            "loss_percentage": sample.get("loss_percentage"),
            "tiff_path": f"{patches_dir}/{sample.get('sample_id')}.tif",
        }
        metadata["samples"].append(sample_dict)

    return metadata


def write_metadata_csv(manifest_list: List[Dict[str, Any]], output_path: str) -> None:
    """
    Write sample manifest to CSV file.

    CSV columns:
    sample_id, aoi_id, year, loss_bin, minx, miny, maxx, maxy, loss_percentage, tiff_path

    Args:
        manifest_list: List of sample dicts from create_sample_manifest()
        output_path: Path where CSV will be written

    Raises:
        ImportError: If pandas is not installed
        IOError: If file cannot be written

    Example:
        >>> manifest = [...]
        >>> write_metadata_csv(manifest, "samples_metadata.csv")
    """
    if pd is None:
        raise ImportError("pandas required for CSV export. Install with: pip install pandas")

    # Convert manifest to DataFrame
    data = []
    for sample in manifest_list:
        row = {
            "sample_id": sample.get("sample_id"),
            "aoi_id": sample.get("aoi_id"),
            "year": sample.get("year"),
            "loss_bin": sample.get("loss_bin"),
            "minx": sample.get("minx"),
            "miny": sample.get("miny"),
            "maxx": sample.get("maxx"),
            "maxy": sample.get("maxy"),
            "loss_percentage": sample.get("loss_percentage"),
            "tiff_path": f"patches/{sample.get('sample_id')}.tif",
        }
        data.append(row)

    df = pd.DataFrame(data)

    # Write CSV
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)

    logger.info(f"Wrote {len(manifest_list)} samples to CSV: {output_path}")


def write_metadata_json(manifest_list: List[Dict[str, Any]], output_path: str, patches_dir: str = "patches") -> None:
    """
    Write sample manifest to JSON file.

    Args:
        manifest_list: List of sample dicts from create_sample_manifest()
        output_path: Path where JSON will be written
        patches_dir: Relative path to patches directory (for path in metadata)

    Raises:
        IOError: If file cannot be written

    Example:
        >>> manifest = [...]
        >>> write_metadata_json(manifest, "samples_metadata.json")
    """
    metadata = create_metadata_dict(manifest_list, patches_dir)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Wrote {len(manifest_list)} samples to JSON: {output_path}")


def validate_metadata(
    manifest_list: List[Dict[str, Any]], patches_dir: str
) -> Dict[str, Any]:
    """
    Validate that all samples in manifest have corresponding TIFF files.

    Args:
        manifest_list: List of sample dicts from create_sample_manifest()
        patches_dir: Path to directory containing extracted patches

    Returns:
        Validation report dict with keys:
        - valid (bool): Whether all samples are valid
        - total_samples (int): Number of samples in manifest
        - missing_files (list): Paths to missing TIFF files
        - invalid_bboxes (list): Samples with invalid bounding boxes
        - duplicate_ids (list): Duplicate sample IDs
        - errors (list): Error messages
        - warnings (list): Warning messages

    Example:
        >>> manifest = [...]
        >>> report = validate_metadata(manifest, "patches/")
        >>> if report["valid"]:
        ...     print("All samples valid!")
    """
    report = {
        "valid": True,
        "total_samples": len(manifest_list),
        "missing_files": [],
        "invalid_bboxes": [],
        "duplicate_ids": [],
        "errors": [],
        "warnings": [],
    }

    patches_path = Path(patches_dir)
    seen_ids = set()

    for sample in manifest_list:
        sample_id = sample.get("sample_id")

        # Check for duplicate IDs
        if sample_id in seen_ids:
            report["duplicate_ids"].append(sample_id)
            report["errors"].append(f"Duplicate sample_id: {sample_id}")
            report["valid"] = False
        seen_ids.add(sample_id)

        # Check if TIFF file exists
        tiff_path = patches_path / f"{sample_id}.tif"
        if not tiff_path.exists():
            report["missing_files"].append(str(tiff_path))
            report["errors"].append(f"Missing TIFF file: {tiff_path}")
            report["valid"] = False

        # Validate bounding box
        bbox_keys = ["minx", "miny", "maxx", "maxy"]
        bbox_values = [sample.get(key) for key in bbox_keys]

        if any(v is None for v in bbox_values):
            report["invalid_bboxes"].append((sample_id, "Missing bbox value"))
            report["errors"].append(f"Invalid bbox for {sample_id}: Missing value")
            report["valid"] = False
        elif not all(isinstance(v, (int, float)) for v in bbox_values):
            report["invalid_bboxes"].append((sample_id, "Non-numeric bbox value"))
            report["errors"].append(f"Invalid bbox for {sample_id}: Non-numeric value")
            report["valid"] = False
        elif sample.get("minx") >= sample.get("maxx") or sample.get("miny") >= sample.get("maxy"):
            report["invalid_bboxes"].append((sample_id, "Inverted bbox coordinates"))
            report["errors"].append(f"Invalid bbox for {sample_id}: Inverted coordinates")
            report["valid"] = False

    logger.info(f"Validation complete: {len(manifest_list)} samples, valid={report['valid']}")

    return report


def print_validation_report(report: Dict[str, Any]) -> None:
    """
    Print a human-readable validation report.

    Args:
        report: Output from validate_metadata()

    Example:
        >>> report = validate_metadata(manifest, "patches/")
        >>> print_validation_report(report)
    """
    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)

    status = "✅ VALID" if report["valid"] else "❌ INVALID"
    print(f"Status: {status}")
    print(f"Total samples: {report['total_samples']}")

    if report["missing_files"]:
        print(f"\n⚠️  Missing files ({len(report['missing_files'])}):")
        for path in report["missing_files"][:5]:
            print(f"   {path}")
        if len(report["missing_files"]) > 5:
            print(f"   ... and {len(report['missing_files']) - 5} more")

    if report["invalid_bboxes"]:
        print(f"\n⚠️  Invalid bboxes ({len(report['invalid_bboxes'])}):")
        for sample_id, reason in report["invalid_bboxes"][:5]:
            print(f"   {sample_id}: {reason}")
        if len(report["invalid_bboxes"]) > 5:
            print(f"   ... and {len(report['invalid_bboxes']) - 5} more")

    if report["duplicate_ids"]:
        print(f"\n⚠️  Duplicate IDs ({len(report['duplicate_ids'])}):")
        for sample_id in report["duplicate_ids"][:5]:
            print(f"   {sample_id}")
        if len(report["duplicate_ids"]) > 5:
            print(f"   ... and {len(report['duplicate_ids']) - 5} more")

    if report["errors"]:
        print(f"\n❌ Errors ({len(report['errors'])}):")
        for error in report["errors"][:5]:
            print(f"   {error}")
        if len(report["errors"]) > 5:
            print(f"   ... and {len(report['errors']) - 5} more")

    if report["warnings"]:
        print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
        for warning in report["warnings"][:5]:
            print(f"   {warning}")
        if len(report["warnings"]) > 5:
            print(f"   ... and {len(report['warnings']) - 5} more")

    print("=" * 80 + "\n")
