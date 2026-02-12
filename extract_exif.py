import os
from pathlib import Path
import pandas as pd
import piexif
from PIL import Image
from PIL.ExifTags import TAGS
import warnings
try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False

warnings.filterwarnings('ignore')

# --- added: time/ETA helpers ---
import time
from dataclasses import dataclass


def _format_bytes(num_bytes: int) -> str:
    num_bytes = int(num_bytes or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for u in units:
        if size < 1024 or u == units[-1]:
            return f"{size:.2f}{u}" if u != "B" else f"{int(size)}{u}"
        size /= 1024.0
    return f"{size:.2f}TB"


def _format_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0.0))
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, s = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{s:02d}s"
    hours, m = divmod(minutes, 60)
    return f"{hours}h{m:02d}m"


@dataclass
class ProgressEstimator:
    total_files: int
    total_bytes: int
    start_ts: float = time.perf_counter()
    processed_files: int = 0
    processed_bytes: int = 0

    def advance(self, file_bytes: int) -> None:
        self.processed_files += 1
        self.processed_bytes += int(file_bytes or 0)

    def status_suffix(self) -> str:
        elapsed = time.perf_counter() - self.start_ts

        # Prefer byte-based ETA when we know total_bytes; fallback to file-based.
        eta = None
        if self.total_bytes > 0 and self.processed_bytes > 0:
            rate_bps = self.processed_bytes / max(elapsed, 1e-9)
            remaining = max(self.total_bytes - self.processed_bytes, 0)
            eta = remaining / max(rate_bps, 1e-9)
        elif self.total_files > 0 and self.processed_files > 0:
            rate_fps = self.processed_files / max(elapsed, 1e-9)
            remaining = max(self.total_files - self.processed_files, 0)
            eta = remaining / max(rate_fps, 1e-9)

        pct = (100.0 * self.processed_files / self.total_files) if self.total_files else 0.0
        eta_str = _format_duration(eta) if eta is not None else "?"
        return (
            f" | {self.processed_files}/{self.total_files} ({pct:.1f}%)"
            f" | { _format_bytes(self.processed_bytes) }/{ _format_bytes(self.total_bytes) }"
            f" | elapsed {_format_duration(elapsed)}"
            f" | ETA {eta_str}"
        )


def extract_exif_from_file(file_path):
    """Extract EXIF data from an image file (.ARW, .DNG, etc.)"""
    exif_data = {}
    exif_data['file_path'] = str(file_path)
    exif_data['file_name'] = file_path.name

    try:
        # Try piexif first (works best for raw files)
        exif_dict = piexif.load(str(file_path))
        for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
            if ifd_name in exif_dict:
                for tag in exif_dict[ifd_name]:
                    tag_info = piexif.TAGS[ifd_name][tag]
                    tag_name = tag_info["name"]
                    # Handle both bytes and str
                    if isinstance(tag_name, bytes):
                        tag_name = tag_name.decode()

                    value = exif_dict[ifd_name][tag]
                    try:
                        exif_data[tag_name] = str(value)
                    except:
                        exif_data[tag_name] = "Unable to convert value"
    except Exception as e1:
        # If piexif fails, try PIL
        try:
            image = Image.open(file_path)
            exif_dict = image._getexif()

            if exif_dict:
                for tag_id, value in exif_dict.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    try:
                        exif_data[tag_name] = str(value)
                    except:
                        exif_data[tag_name] = "Unable to convert value"
            else:
                exif_data['error'] = "No EXIF data found"
        except Exception as e2:
            exif_data['error'] = str(e1)

    return exif_data


def crawl_and_extract_exif(root_path, output_csv=None):
    """
    Crawl all folders in root_path and extract EXIF data from .ARW and .DNG files

    Args:
        root_path (str): Root directory to start crawling from
        output_csv (str): Path to output CSV file. If None, uses root_path/exif_data.csv

    Returns:
        pd.DataFrame: DataFrame containing EXIF data for all files
    """
    root_path = Path(root_path)

    if not root_path.exists():
        raise ValueError(f"Path does not exist: {root_path}")

    # Find all .ARW and .DNG files
    image_files = list(root_path.rglob('*.ARW')) + list(root_path.rglob('*.DNG'))
    print(f"Found {len(image_files)} image files in {root_path}.")
    image_files += list(root_path.rglob('*.arw')) + list(root_path.rglob('*.dng'))
    print(f"Found {len(image_files)} image files in {root_path}.")

    if not image_files:
        print(f"No .ARW or .DNG files found in {root_path}")
        return pd.DataFrame()

    # --- added: compute total size up-front and print it at the beginning ---
    sizes = []
    total_bytes = 0
    for p in image_files:
        try:
            b = p.stat().st_size
        except OSError:
            b = 0
        sizes.append(b)
        total_bytes += b

    est = ProgressEstimator(total_files=len(image_files), total_bytes=total_bytes)

    print(
        f"Found {len(image_files)} image files. Total size: {_format_bytes(total_bytes)}. "
        f"Extracting EXIF data..."
        f"{est.status_suffix()}"
    )

    exif_list = []
    for i, file_path in enumerate(image_files, 1):
        file_size = sizes[i - 1]

        exif_dict = extract_exif_from_file(file_path)
        exif_list.append(exif_dict)

        # --- added: advance estimator after work is done for this file ---
        est.advance(file_size)

        # --- changed: include estimation after every progress print ---
        if i % 100 == 0 or i == 1:
            print(f"Processing [{i}/{len(image_files)}]: {file_path.name}{est.status_suffix()}")

    # Create DataFrame
    df = pd.DataFrame(exif_list)

    # Reorder columns: file_path and file_name first
    cols = ['file_path', 'file_name'] + [col for col in df.columns if col not in ['file_path', 'file_name']]
    df = df[cols]

    # Export to CSV
    if output_csv is None:
        output_csv = root_path / 'exif_data.csv'

    output_path = Path(output_csv)
    df.to_csv(output_path, index=False, encoding='utf-8')

    # --- changed: add estimations after every print (these are prints too) ---
    print(f"\nExported {len(df)} files to: {output_path}{est.status_suffix()}")
    print(f"Total EXIF columns: {len(df.columns)}{est.status_suffix()}")

    return df


if __name__ == "__main__":
    # Specify your root directory here
    ROOT_PATH = r"D:\Photos"

    # Optional: Specify output CSV path, or leave as None to use default
    OUTPUT_CSV = None  # Will create exif_data.csv in ROOT_PATH

    df = crawl_and_extract_exif(ROOT_PATH, OUTPUT_CSV)
    print("\nFirst few rows of the dataframe:")
    print(df.head())
