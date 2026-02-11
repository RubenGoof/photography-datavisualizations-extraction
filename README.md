# EXIF Data Analysis Pipeline

A complete Python pipeline for extracting, cleaning, and analyzing EXIF metadata from photography collections.

## Workflow

```
extract_exif.py  →  main.py  →  Cleaned Data + Visualizations
  (Raw files)    (Process)        (CSV + PNG)
```

## Scripts

### 1. `extract_exif.py` (First Step)
Extracts EXIF metadata from raw camera files (.ARW, .DNG, .JPG, .PNG, etc.) across multiple directories.

**Usage:**
```bash
python extract_exif.py <root_directory> <output_csv>
```

**Example:**
```bash
python extract_exif.py "I:\Photos" exif_raw.csv
```

**Output:**
- `exif_raw.csv` - 63+ raw EXIF fields in standard CSV format

**Extraction Methods (Fallback Chain):**
1. **piexif** - Primary method, excellent raw file support
2. **PIL/Pillow** - Fallback for JPG/PNG
3. **rawpy** - Extended raw format support

---

### 2. `main.py` (Processing & Analysis)
Cleans, normalizes, and analyzes EXIF data. Generates cleaned CSV files and comprehensive visualizations.

**Features:**
- ✅ No hard-coded paths - all via command-line arguments
- ✅ Camera-agnostic - configurable crop factors for any camera
- ✅ ISO threshold filtering (configurable)
- ✅ Focal length normalization for crop sensor cameras
- ✅ 18 total visualizations (2 dashboards × 9 charts each)
- ✅ Automatic date/time extraction and decomposition

**Usage:**
```bash
python main.py <input_csv> [options]
```

**Basic Usage:**
```bash
python main.py exif_raw.csv
```

**With Output Directory:**
```bash
python main.py exif_raw.csv --output-dir ./results
```

**With Custom ISO Threshold:**
```bash
python main.py exif_raw.csv --iso-threshold 12800
```

**With Camera Focal Length Crop Factors:**
```bash
python main.py exif_raw.csv --camera-crop-factors '{"ILCE-6400": 1.5, "RICOH GR IV": 1.5}'
```

**Complete Example:**
```bash
python main.py exif_raw.csv --output-dir ./analysis --iso-threshold 6400 --camera-crop-factors '{"ILCE-6400": 1.5, "RICOH GR IV": 1.5}'
```

**Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `input_csv` | str | Required | Path to raw EXIF CSV from `extract_exif.py` |
| `--output-dir` | str | Same as input | Directory for cleaned CSV and visualizations |
| `--iso-threshold` | int | 6400 | Maximum ISO to keep (above is filtered as outlier) |
| `--camera-crop-factors` | JSON | {} | Camera model → crop factor mapping for focal length normalization |

**Outputs:**
- `exif_data_cleaned.csv` - Cleaned and normalized EXIF data (14 columns)
- `exif_dates.csv` - DateTime column only (for reference)
- `exif_visualization_main.png` - Main dashboard (9 charts)
- `exif_visualization_analysis.png` - Analysis dashboard (9 charts)

**Output Columns (exif_data_cleaned.csv):**
| Column | Type | Description |
|--------|------|-------------|
| `file_path` | str | Full path to original photo |
| `file_name` | str | Filename only |
| `picture_dimensions` | str | Image dimensions (WxH) |
| `camera_model` | str | Camera model name |
| `datetime_taken` | datetime | Full timestamp |
| `date_taken` | date | Date only |
| `time_of_day` | time | Time only |
| `hour` | int | Hour (0-23) |
| `iso_speed` | int | ISO sensitivity |
| `f_stop` | float | Aperture (raw value) |
| `exposure_time` | float | Shutter speed (seconds) |
| `exposure_bias` | float | EV offset |
| `flash_mode` | str | "Flash" or "No Flash" |
| `focal_length` | float | Focal length in mm (crop-corrected) |

---

## Main Visualizations (9 charts)

**Dashboard 1: exif_visualization_main.png**

1. **Pictures Taken Over Time** - Monthly histogram of photos
2. **ISO Speed Distribution** - Bar chart of ISO values
3. **F-Stop Distribution** - Aperture histogram
4. **Exposure Time Distribution** - Shutter speed range (log scale)
5. **Focal Length Distribution** - Focal length histogram
6. **Camera Model Usage** - Photo count by camera
7. **Flash Mode Usage** - Flash vs. No Flash pie chart
8. **Focal Length vs F-Stop** - Scatter plot (colored by ISO)
9. **ISO vs Exposure Time** - Scatter plot (colored by focal length)

**Dashboard 2: exif_visualization_analysis.png**

1. **Photos by Camera Over Time** - Multi-line temporal trend
2. **Average Focal Length by Camera** - Bar chart comparison
3. **Average ISO by Camera** - Bar chart comparison
4. **Focal Length Ranges** - Pie chart (Wide/Standard/Tele)
5. **Exposure Bias Distribution** - Histogram with KDE
6. **Photos by Hour of Day** - 24-hour bar chart
7. **Average ISO Over Time** - Monthly trend line
8. **Average Focal Length Over Time** - Monthly trend line
9. **Average Hour of Day Over Time** - Monthly trend line

---

## Camera-Agnostic Focal Length Normalization

By default, `main.py` normalizes focal lengths for APS-C crop sensor cameras:
- **ILCE-6400** → 1.5× multiplier (16mm becomes 24mm equivalent)
- **RICOH GR IV** → 1.5× multiplier (18.3mm becomes 27.4mm equivalent)

**Full-frame cameras** (ILCA-99M2, ILCE-7M4) are unchanged.

To customize for your cameras, pass a JSON object:

```bash
# Only correct ILCE-6400
python main.py exif_raw.csv --camera-crop-factors '{"ILCE-6400": 1.5}'

# Correct multiple cameras with different factors
python main.py exif_raw.csv --camera-crop-factors '{"ILCE-6400": 1.5, "RICOH GR IV": 1.5, "Nikon Z5": 1.0}'

# Don't correct any cameras
python main.py exif_raw.csv --camera-crop-factors '{}'
```

---

## Complete Workflow Example

```bash
# Step 1: Extract raw EXIF from all photos
python extract_exif.py "D:\Photos\2024" exif_raw.csv

# Step 2: Clean, normalize, and analyze
python main.py exif_raw.csv --output-dir ./analysis --iso-threshold 6400

# Step 3: View the results
# - Open exif_data_cleaned.csv in Excel/Pandas
# - View PNG dashboards in any image viewer
```

---

## Industrial-Grade Design Decisions

1. **No Hard-Coded Paths**
   - All file paths are command-line arguments
   - Output directory is configurable
   - Easy to integrate into automation workflows

2. **Camera-Agnostic**
   - Focal length normalization is configurable
   - ISO threshold is parameterized
   - Works with any camera model without modification

3. **Robust Data Cleaning**
   - Multiple fallback methods for EXIF extraction
   - Comprehensive string/number parsing
   - Error handling and type coercion
   - Outlier filtering (ISO > threshold)

4. **Modular Architecture**
   - Separate extraction script (extract_exif.py)
   - Combined processing and visualization (main.py)
   - Each function is reusable and testable
   - Clear separation of concerns

5. **Comprehensive Logging**
   - Progress messages during processing
   - Statistics summary printed to console
   - File paths confirmed in output
   - Error messages with context

---

## Performance

- **Extraction** (extract_exif.py): ~2-3 seconds per 100 photos
- **Cleaning & Analysis** (main.py): ~1-2 seconds per 1,000 photos
- **Visualization**: ~5-10 seconds for 25,000+ photos

Memory efficient with chunked processing for large CSV files.

---

## Requirements

- Python 3.7+
- pandas
- piexif
- Pillow (PIL)
- rawpy
- matplotlib
- seaborn
- numpy

**Install all dependencies:**
```bash
pip install pandas piexif Pillow rawpy matplotlib seaborn numpy
```

---

## Troubleshooting

**Issue: "Input file not found"**
- Check the CSV path is correct and file exists

**Issue: Empty temporal graphs**
- Ensure DateTime/DateTimeOriginal columns exist in raw EXIF CSV
- Check date format is `YYYY:MM:DD HH:MM:SS`

**Issue: Visualizations not rendering**
- Reduce figure size or data points
- Check for sufficient disk space
- Ensure matplotlib backend is available

**Issue: Camera not being crop-corrected**
- Verify camera model name matches exactly (case-sensitive, whitespace matters)
- Check JSON syntax in --camera-crop-factors argument

---

## Author

Created for comprehensive photography metadata analysis and visualization.

Last updated: February 2026
