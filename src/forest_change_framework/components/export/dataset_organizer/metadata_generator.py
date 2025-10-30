"""Generate metadata CSV and reports for organized datasets."""

import logging
import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MetadataGenerator:
    """Generate metadata CSV and reports for ML training datasets."""

    def __init__(self, output_dir: Path):
        """
        Initialize metadata generator.

        Args:
            output_dir: Output directory for metadata files
        """
        self.output_dir = Path(output_dir)
        self.metadata_rows = []

    def add_sample_metadata(
        self,
        sample_id: str,
        split: str,
        pre_path: str,
        post_path: str,
        label_path: str,
        year: int,
        bbox: List[float],
        loss_bin: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add metadata for a single sample.

        Args:
            sample_id: Sample identifier
            split: "train", "val", or "test"
            pre_path: Path to pre-event imagery
            post_path: Path to post-event imagery
            label_path: Path to label
            year: Year of forest loss
            bbox: [minx, miny, maxx, maxy]
            loss_bin: Loss magnitude bin (e.g., "high", "medium", "low")
            properties: Additional properties dict
        """
        row = {
            "sample_id": sample_id,
            "split": split,
            "pre_path": pre_path,
            "post_path": post_path,
            "label_path": label_path,
            "year": year,
            "bbox_minx": bbox[0],
            "bbox_miny": bbox[1],
            "bbox_maxx": bbox[2],
            "bbox_maxy": bbox[3],
            "loss_bin": loss_bin or "",
        }

        # Add custom properties
        if properties:
            for key, value in properties.items():
                prop_key = f"prop_{key}"
                row[prop_key] = str(value)

        self.metadata_rows.append(row)

    def generate_metadata_csv(self) -> Path:
        """
        Write metadata to CSV file.

        Returns:
            Path to generated CSV file
        """
        csv_path = self.output_dir / "metadata.csv"

        if not self.metadata_rows:
            logger.warning("No metadata rows to write")
            return csv_path

        try:
            # Get all field names from all rows
            all_keys = set()
            for row in self.metadata_rows:
                all_keys.update(row.keys())

            # Define field order with custom properties at the end
            standard_fields = [
                "sample_id",
                "split",
                "pre_path",
                "post_path",
                "label_path",
                "year",
                "bbox_minx",
                "bbox_miny",
                "bbox_maxx",
                "bbox_maxy",
                "loss_bin",
            ]

            custom_fields = sorted([k for k in all_keys if k not in standard_fields])
            fieldnames = standard_fields + custom_fields

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.metadata_rows)

            logger.info(
                f"Generated metadata CSV: {csv_path} "
                f"({len(self.metadata_rows)} rows)"
            )
            return csv_path

        except Exception as e:
            logger.error(f"Failed to generate metadata CSV: {e}")
            raise

    def generate_split_report(
        self,
        split_counts: Dict[str, int],
        target_percentages: Dict[str, float],
    ) -> Path:
        """
        Generate split distribution report.

        Args:
            split_counts: Dict with counts per split
            target_percentages: Dict with target percentages

        Returns:
            Path to generated report
        """
        report_path = self.output_dir / "split_report.txt"

        try:
            total = sum(split_counts.values())

            with open(report_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("DATASET SPLIT REPORT\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Total Samples: {total}\n\n")

                f.write("SPLIT DISTRIBUTION\n")
                f.write("-" * 60 + "\n")

                for split in ["train", "val", "test"]:
                    count = split_counts.get(split, 0)
                    pct = (count / total * 100) if total > 0 else 0
                    target = target_percentages.get(split, 0)

                    f.write(
                        f"{split.upper():8} : {count:5d} samples "
                        f"({pct:5.1f}% actual, {target:5.1f}% target)\n"
                    )

                f.write("\n" + "=" * 60 + "\n")

            logger.info(f"Generated split report: {report_path}")
            return report_path

        except Exception as e:
            logger.error(f"Failed to generate split report: {e}")
            raise

    def generate_integrity_check(
        self,
        validation_report: Dict[str, Any],
    ) -> Path:
        """
        Generate integrity check JSON report.

        Args:
            validation_report: Validation report dict from organizer

        Returns:
            Path to generated integrity check file
        """
        integrity_path = self.output_dir / "integrity_check.json"

        try:
            report = {
                "status": "valid" if validation_report.get("valid") else "invalid",
                "total_triplets": validation_report.get("total_triplets", 0),
                "complete_triplets": validation_report.get("complete_triplets", 0),
                "incomplete_triplets": validation_report.get("incomplete_triplets", []),
                "split_counts": validation_report.get("split_counts", {}),
            }

            with open(integrity_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            logger.info(f"Generated integrity check: {integrity_path}")
            return integrity_path

        except Exception as e:
            logger.error(f"Failed to generate integrity check: {e}")
            raise

    def generate_statistics(self) -> Dict[str, Any]:
        """
        Generate dataset statistics.

        Returns:
            Statistics dict
        """
        if not self.metadata_rows:
            return {
                "total_samples": 0,
                "splits": {},
                "year_distribution": {},
            }

        # Count samples per split
        split_counts = {"train": 0, "val": 0, "test": 0}
        year_distribution = {}

        for row in self.metadata_rows:
            split = row.get("split", "")
            if split in split_counts:
                split_counts[split] += 1

            year = row.get("year")
            if year:
                year_distribution[year] = year_distribution.get(year, 0) + 1

        # Calculate percentages
        total = sum(split_counts.values())
        split_pcts = {
            k: round(v / total * 100, 2) if total > 0 else 0
            for k, v in split_counts.items()
        }

        return {
            "total_samples": total,
            "splits": {
                "counts": split_counts,
                "percentages": split_pcts,
            },
            "year_distribution": dict(sorted(year_distribution.items())),
        }

    def generate_summary_report(
        self,
        validation_report: Dict[str, Any],
        statistics: Dict[str, Any],
    ) -> Path:
        """
        Generate comprehensive summary report.

        Args:
            validation_report: Validation report from organizer
            statistics: Statistics dict

        Returns:
            Path to summary report
        """
        summary_path = self.output_dir / "summary.txt"

        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("DATASET ORGANIZATION SUMMARY\n")
                f.write("=" * 70 + "\n\n")

                # Validation status
                status = "✓ VALID" if validation_report.get("valid") else "✗ INVALID"
                f.write(f"Validation Status: {status}\n\n")

                # Statistics
                f.write("STATISTICS\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total Samples: {statistics.get('total_samples', 0)}\n")
                f.write(f"Complete Triplets: {validation_report.get('complete_triplets', 0)}\n")
                f.write(f"Incomplete Triplets: {len(validation_report.get('incomplete_triplets', []))}\n")
                f.write("\n")

                # Split distribution
                splits = statistics.get("splits", {})
                counts = splits.get("counts", {})
                pcts = splits.get("percentages", {})

                f.write("SPLIT DISTRIBUTION\n")
                f.write("-" * 70 + "\n")
                for split in ["train", "val", "test"]:
                    count = counts.get(split, 0)
                    pct = pcts.get(split, 0)
                    f.write(f"  {split.upper():6} : {count:5d} samples ({pct:5.1f}%)\n")
                f.write("\n")

                # Year distribution
                year_dist = statistics.get("year_distribution", {})
                if year_dist:
                    f.write("YEAR DISTRIBUTION\n")
                    f.write("-" * 70 + "\n")
                    for year in sorted(year_dist.keys()):
                        count = year_dist[year]
                        f.write(f"  {year}: {count} samples\n")
                    f.write("\n")

                # Issues
                incomplete = validation_report.get("incomplete_triplets", [])
                if incomplete:
                    f.write("INCOMPLETE TRIPLETS\n")
                    f.write("-" * 70 + "\n")
                    for item in incomplete[:10]:  # Show first 10
                        f.write(f"  {item.get('sample_id', 'unknown')}: ")
                        f.write(f"{', '.join(item.get('missing_files', []))}\n")
                    if len(incomplete) > 10:
                        f.write(f"  ... and {len(incomplete) - 10} more\n")
                    f.write("\n")

                f.write("=" * 70 + "\n")

            logger.info(f"Generated summary report: {summary_path}")
            return summary_path

        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            raise
