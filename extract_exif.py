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
    image_files += list(root_path.rglob('*.arw')) + list(root_path.rglob('*.dng'))
    
    if not image_files:
        print(f"No .ARW or .DNG files found in {root_path}")
        return pd.DataFrame()
    
    print(f"Found {len(image_files)} image files. Extracting EXIF data...")
    
    exif_list = []
    for i, file_path in enumerate(image_files, 1):
        if i % 100 == 0 or i == 1:
            print(f"Processing [{i}/{len(image_files)}]: {file_path.name}")
        exif_dict = extract_exif_from_file(file_path)
        exif_list.append(exif_dict)
    
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
    print(f"\nExported {len(df)} files to: {output_path}")
    print(f"Total EXIF columns: {len(df.columns)}")
    
    return df


if __name__ == "__main__":
    # Specify your root directory here
    ROOT_PATH = r"I:\Photos"
    
    # Optional: Specify output CSV path, or leave as None to use default
    OUTPUT_CSV = None  # Will create exif_data.csv in ROOT_PATH
    
    df = crawl_and_extract_exif(ROOT_PATH, OUTPUT_CSV)
    print("\nFirst few rows of the dataframe:")
    print(df.head())
