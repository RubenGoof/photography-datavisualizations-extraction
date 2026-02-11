#!/usr/bin/env python3
"""
EXIF Data Analysis Pipeline

Processes raw EXIF data from extract_exif.py into cleaned, normalized data
and generates comprehensive visualization dashboards.

Usage:
    python main.py <input_csv> [--output-dir OUTPUT_DIR] [--iso-threshold ISO] 
                   [--camera-crop-factors FACTORS_JSON]

Example:
    python main.py exif_raw.csv --output-dir ./results --iso-threshold 6400
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import json
import re
import warnings

warnings.filterwarnings('ignore')

# Set matplotlib style
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (20, 14)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9


# ============================================================================
# DATA CLEANING FUNCTIONS
# ============================================================================

def clean_picture_dimensions(value):
    """Extract image dimensions from various formats"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    match = re.search(r'(\d+)\s*[x×]\s*(\d+)', value_str)
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    
    match = re.search(r'\((\d+),\s*(\d+)\)', value_str)
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    
    return value_str


def clean_camera_model(value):
    """Clean camera model string"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    value_str = value_str.replace("b'", "").replace('b"', "").replace("'", "").replace('"', "")
    value_str = value_str.strip()
    return value_str if value_str else None


def clean_iso_speed(value):
    """Convert ISO speed to integer"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    match = re.search(r'(\d+)', value_str)
    if match:
        try:
            return int(match.group(1))
        except:
            return None
    return None


def clean_f_stop(value):
    """Convert F-stop to float"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    match = re.search(r'[f/]*(\d+\.?\d*)', value_str)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    
    match = re.search(r'\((\d+),\s*(\d+)\)', value_str)
    if match:
        try:
            num = int(match.group(1))
            denom = int(match.group(2))
            if denom > 0:
                return round(num / denom, 2)
        except:
            return None
    
    return None


def clean_exposure_time(value):
    """Convert exposure time to float (seconds)"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    
    match = re.search(r'\((\d+),\s*(\d+)\)', value_str)
    if match:
        try:
            num = int(match.group(1))
            denom = int(match.group(2))
            if denom > 0:
                return round(num / denom, 6)
        except:
            return None
    
    try:
        return float(value_str)
    except:
        pass
    
    match = re.search(r'(\d+)\s*/\s*(\d+)', value_str)
    if match:
        try:
            num = int(match.group(1))
            denom = int(match.group(2))
            if denom > 0:
                return round(num / denom, 6)
        except:
            return None
    
    return None


def clean_exposure_bias(value):
    """Convert exposure bias to float"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    
    match = re.search(r'\((-?\d+),\s*(\d+)\)', value_str)
    if match:
        try:
            num = int(match.group(1))
            denom = int(match.group(2))
            if denom > 0:
                return round(num / denom, 2)
        except:
            return None
    
    try:
        return float(value_str)
    except:
        pass
    
    return None


def clean_flash_mode(value):
    """Clean flash mode string - simplify to Flash or No Flash"""
    if pd.isna(value) or value == '':
        return 'No Flash'
    
    value_str = str(value).strip()
    value_str = value_str.replace("b'", "").replace('b"', "").replace("'", "").replace('"', "")
    
    flash_fired_indicators = ['1', '5', '7', '13', '15']
    flash_no_indicators = ['0', '8', '9', '16', '24', '25']
    
    if value_str in flash_fired_indicators:
        return 'Flash'
    elif value_str in flash_no_indicators:
        return 'No Flash'
    
    value_lower = value_str.lower()
    if 'fire' in value_lower and 'not' not in value_lower and 'did' not in value_lower:
        return 'Flash'
    else:
        return 'No Flash'


def clean_focal_length(value):
    """Convert focal length to float"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    
    match = re.search(r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)', value_str)
    if match:
        try:
            num = float(match.group(1))
            denom = float(match.group(2))
            if denom > 0:
                return round(num / denom, 2)
        except:
            return None
    
    match = re.search(r'(\d+\.?\d*)\s*(?:mm)?', value_str)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    
    return None


def clean_date_taken(value):
    """Convert date taken to datetime format"""
    if pd.isna(value) or value == '':
        return None
    
    value_str = str(value).strip()
    value_str = value_str.replace("b'", "").replace('b"', "").replace("'", "").replace('"', "")
    
    if not value_str:
        return None
    
    try:
        return pd.to_datetime(value_str, format='%Y:%m:%d %H:%M:%S')
    except:
        try:
            return pd.to_datetime(value_str)
        except:
            return None


def extract_date_components(dt):
    """Extract date from datetime"""
    if pd.isna(dt):
        return None
    try:
        return dt.date() if hasattr(dt, 'date') else None
    except:
        return None


def extract_time_of_day(dt):
    """Extract time from datetime"""
    if pd.isna(dt):
        return None
    try:
        return dt.time() if hasattr(dt, 'time') else None
    except:
        return None


def extract_hour(dt):
    """Extract hour from datetime"""
    if pd.isna(dt):
        return None
    try:
        return dt.hour if hasattr(dt, 'hour') else None
    except:
        return None


def clean_exif_data(input_csv, output_csv=None, iso_threshold=6400, camera_crop_factors=None):
    """
    Clean and normalize EXIF data from raw CSV.
    
    Args:
        input_csv (str): Path to raw EXIF CSV from extract_exif.py
        output_csv (str): Output path for cleaned CSV. If None, creates in same directory
        iso_threshold (int): Maximum ISO to keep (above this is considered outlier)
        camera_crop_factors (dict): Camera model -> crop factor mapping (e.g., {'ILCE-6400': 1.5})
    
    Returns:
        pd.DataFrame: Cleaned EXIF data
    """
    print(f"Loading raw EXIF data from {input_csv}...")
    df = pd.read_csv(input_csv, low_memory=False)
    print(f"Loaded {len(df)} records with {len(df.columns)} columns")
    
    df_clean = df.copy()
    
    # Clean dimensions
    if 'ImageWidth' in df.columns or 'ImageLength' in df.columns:
        df_clean['picture_dimensions'] = 'Unknown'
        if 'ImageWidth' in df.columns and 'ImageLength' in df.columns:
            df_clean['picture_dimensions'] = df['ImageWidth'].astype(str) + 'x' + df['ImageLength'].astype(str)
    
    # Clean camera model
    if 'Model' in df.columns:
        df_clean['camera_model'] = df['Model'].apply(clean_camera_model)
    
    # Clean EXIF fields
    if 'ISOSpeedRatings' in df.columns:
        df_clean['iso_speed'] = df['ISOSpeedRatings'].apply(clean_iso_speed)
    
    if 'FNumber' in df.columns:
        df_clean['f_stop'] = df['FNumber'].apply(clean_f_stop)
    
    if 'ExposureTime' in df.columns:
        df_clean['exposure_time'] = df['ExposureTime'].apply(clean_exposure_time)
    
    if 'ExposureBiasValue' in df.columns:
        df_clean['exposure_bias'] = df['ExposureBiasValue'].apply(clean_exposure_bias)
    
    if 'Flash' in df.columns:
        df_clean['flash_mode'] = df['Flash'].apply(clean_flash_mode)
    
    if 'FocalLength' in df.columns:
        df_clean['focal_length'] = df['FocalLength'].apply(clean_focal_length)
    
    # Apply focal length crop factor correction if provided
    if camera_crop_factors and 'focal_length' in df_clean.columns and 'camera_model' in df_clean.columns:
        print(f"\nApplying focal length crop factors: {camera_crop_factors}")
        for camera_model, crop_factor in camera_crop_factors.items():
            df_clean['camera_model_stripped'] = df_clean['camera_model'].str.strip()
            mask = df_clean['camera_model_stripped'] == camera_model
            if mask.any():
                df_clean.loc[mask, 'focal_length'] = (df_clean.loc[mask, 'focal_length'] * crop_factor).round(2)
                print(f"  Applied {crop_factor}x to {camera_model} ({mask.sum()} photos)")
        df_clean.drop('camera_model_stripped', axis=1, inplace=True)
    
    # Extract datetime
    date_taken = None
    if 'DateTime' in df.columns:
        df_clean['datetime_taken'] = df['DateTime'].apply(clean_date_taken)
        date_taken = df_clean['datetime_taken']
    elif 'DateTimeOriginal' in df.columns:
        df_clean['datetime_taken'] = df['DateTimeOriginal'].apply(clean_date_taken)
        date_taken = df_clean['datetime_taken']
    
    # Extract date/time components
    if date_taken is not None:
        df_clean['date_taken'] = date_taken.apply(extract_date_components)
        df_clean['time_of_day'] = date_taken.apply(extract_time_of_day)
        df_clean['hour'] = date_taken.apply(extract_hour)
    
    # Reorder columns
    cleaned_cols = ['file_path', 'file_name']
    for new_col in ['picture_dimensions', 'camera_model', 'datetime_taken', 'date_taken', 
                    'time_of_day', 'hour', 'iso_speed', 'f_stop', 
                    'exposure_time', 'exposure_bias', 'flash_mode', 'focal_length']:
        if new_col in df_clean.columns:
            cleaned_cols.append(new_col)
    
    df_clean = df_clean[cleaned_cols]
    
    # Export
    if output_csv is None:
        output_csv = Path(input_csv).parent / 'exif_data_cleaned.csv'
    
    df_clean.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"\nExported cleaned data to: {output_csv}")
    print(f"Cleaned columns: {len(cleaned_cols) - 2} fields")
    print("\nFirst few rows:")
    print(df_clean.head())
    
    return df_clean


def extract_dates_from_csv(df_clean, output_dir=None):
    """
    Extract DateTime column from cleaned data and save as separate file.
    
    Args:
        df_clean (pd.DataFrame): Cleaned EXIF dataframe
        output_dir (str): Directory to save dates CSV
    
    Returns:
        str: Path to dates CSV
    """
    try:
        print("\nExtracting datetime column for visualizations...")
        
        if 'datetime_taken' not in df_clean.columns:
            print("Warning: datetime_taken column not found")
            return None
        
        df_dates = pd.DataFrame({'DateTime': pd.to_datetime(df_clean['datetime_taken'], errors='coerce')})
        
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
        
        dates_csv = output_dir / 'exif_dates.csv'
        df_dates.to_csv(dates_csv, index=False)
        print(f"Extracted and saved {df_dates['DateTime'].notna().sum()} date records to: {dates_csv}")
        return str(dates_csv)
        
    except Exception as e:
        print(f"Error extracting dates: {e}")
        return None


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_main_visualizations(df_clean, output_dir=None):
    """Create main visualization dashboard (9 charts)"""
    print("\nCreating main visualization dashboard...")
    
    fig = plt.figure(figsize=(24, 18))
    
    # Prepare data
    df_clean_viz = df_clean.copy()
    df_clean_viz['f_stop_corrected'] = df_clean_viz['f_stop'] / 10
    
    # Extract dates for temporal graphs
    if 'datetime_taken' in df_clean_viz.columns:
        df_dates = pd.to_datetime(df_clean_viz['datetime_taken'], errors='coerce')
    else:
        df_dates = None
    
    # 1. Pictures over time (monthly aggregation)
    if df_dates is not None:
        ax1 = plt.subplot(3, 3, 1)
        df_dates_valid = df_dates.dropna()
        monthly_counts = df_dates_valid.dt.to_period('M').value_counts().sort_index()
        
        if len(monthly_counts) > 0:
            monthly_labels = [period.strftime('%b %Y') for period in monthly_counts.index]
            ax1.plot(range(len(monthly_counts)), monthly_counts.values, marker='o', linewidth=2.5, markersize=8, color='steelblue')
            ax1.set_xticks(range(len(monthly_counts)))
            ax1.set_xticklabels(monthly_labels, rotation=45, ha='right', fontsize=10)
            ax1.set_title('Pictures Taken Over Time (Monthly)', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Month', fontweight='bold')
            ax1.set_ylabel('Number of Photos', fontweight='bold')
            ax1.grid(True, alpha=0.3)
    
    # 2. ISO Speed Distribution
    ax2 = plt.subplot(3, 3, 2)
    iso_counts = df_clean_viz['iso_speed'].dropna().value_counts().sort_index()
    ax2.bar(range(len(iso_counts)), iso_counts.values, color='steelblue', edgecolor='black', linewidth=0.8)
    ax2.set_xticks(range(len(iso_counts)))
    ax2.set_xticklabels([str(int(x)) for x in iso_counts.index], rotation=45, ha='right')
    ax2.set_title('ISO Speed Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('ISO Speed', fontweight='bold')
    ax2.set_ylabel('Count', fontweight='bold')
    ax2.legend(['ISO Speed'], loc='upper right')
    
    # 3. F-Stop Distribution (corrected)
    ax3 = plt.subplot(3, 3, 3)
    f_stop_corrected = df_clean_viz['f_stop_corrected'].dropna()
    counts, bins, patches = ax3.hist(f_stop_corrected, bins=20, color='coral', edgecolor='black', linewidth=0.8, alpha=0.8)
    ax3.set_title('F-Stop Distribution (Aperture)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('F-Stop (Aperture)', fontweight='bold')
    ax3.set_ylabel('Count', fontweight='bold')
    ax3.set_xticks(bins)
    ax3.set_xticklabels([f'f/{x:.1f}' for x in bins], rotation=45, ha='right', fontsize=8)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Exposure Time Distribution (0.008s to 1.0s with log scale)
    ax4 = plt.subplot(3, 3, 4)
    exposure_filtered = df_clean_viz['exposure_time'].dropna()
    exposure_filtered = exposure_filtered[(exposure_filtered >= 0.008) & (exposure_filtered <= 1.0)]
    if len(exposure_filtered) > 0:
        ax4.hist(exposure_filtered, bins=40, color='lightgreen', edgecolor='black', linewidth=0.8, alpha=0.8)
        ax4.set_xscale('log')
        ax4.set_title('Exposure Time Distribution (0.008s to 1.0s)', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Exposure Time (seconds, log scale)', fontweight='bold')
        ax4.set_ylabel('Count', fontweight='bold')
        ax4.grid(True, alpha=0.3, which='both')
        from matplotlib.ticker import FuncFormatter
        def format_exposure(x, pos):
            if x >= 1:
                return f'{x:.0f}s'
            elif x >= 0.1:
                return f'{x:.2f}s'
            elif x >= 0.01:
                return f'{x:.3f}s'
            else:
                return f'{x:.4f}s'
        ax4.xaxis.set_major_formatter(FuncFormatter(format_exposure))
    
    # 5. Focal Length Distribution
    ax5 = plt.subplot(3, 3, 5)
    focal_length = df_clean_viz['focal_length'].dropna()
    counts, bins, patches = ax5.hist(focal_length, bins=20, color='plum', edgecolor='black', linewidth=0.8, alpha=0.8)
    ax5.set_title('Focal Length Distribution', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Focal Length (mm)', fontweight='bold')
    ax5.set_ylabel('Count', fontweight='bold')
    ax5.set_xticks(bins[::2])
    ax5.set_xticklabels([f'{int(x)}mm' for x in bins[::2]], rotation=45, ha='right')
    ax5.grid(True, alpha=0.3, axis='y')
    
    # 6. Camera Model Usage
    ax6 = plt.subplot(3, 3, 6)
    camera_counts = df_clean_viz['camera_model'].value_counts()
    colors = plt.cm.Set3(np.linspace(0, 1, len(camera_counts)))
    ax6.barh(range(len(camera_counts)), camera_counts.values, color=colors, edgecolor='black', linewidth=1)
    ax6.set_yticks(range(len(camera_counts)))
    ax6.set_yticklabels(camera_counts.index)
    ax6.set_title('Camera Model Usage', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Number of Photos', fontweight='bold')
    for i, (idx, val) in enumerate(camera_counts.items()):
        ax6.text(val, i, f' {val}', va='center', fontweight='bold')
    
    # 7. Flash Mode Distribution
    ax7 = plt.subplot(3, 3, 7)
    flash_counts = df_clean_viz['flash_mode'].fillna('Unknown').value_counts()
    colors_flash = plt.cm.Pastel1(np.linspace(0, 1, len(flash_counts)))
    ax7.pie(flash_counts.values, labels=flash_counts.index, autopct='%1.1f%%',
            colors=colors_flash, startangle=90, textprops={'fontsize': 10, 'weight': 'bold'})
    ax7.set_title('Flash Mode Usage', fontsize=14, fontweight='bold')
    
    # 8. Focal Length vs F-Stop (Scatter)
    ax8 = plt.subplot(3, 3, 8)
    valid_data = df_clean_viz.dropna(subset=['focal_length', 'f_stop_corrected'])
    if len(valid_data) > 5000:
        valid_data = valid_data.sample(5000, random_state=42)
    scatter = ax8.scatter(valid_data['focal_length'], valid_data['f_stop_corrected'], 
                         c=valid_data['iso_speed'], cmap='viridis', s=50, alpha=0.6, edgecolors='black', linewidth=0.5)
    ax8.set_title('Focal Length vs F-Stop (colored by ISO)', fontsize=14, fontweight='bold')
    ax8.set_xlabel('Focal Length (mm)', fontweight='bold')
    ax8.set_ylabel('F-Stop (Aperture)', fontweight='bold')
    cbar = plt.colorbar(scatter, ax=ax8)
    cbar.set_label('ISO Speed', fontweight='bold')
    
    # 9. ISO vs Exposure Time (Scatter - filtered)
    ax9 = plt.subplot(3, 3, 9)
    valid_data2 = df_clean_viz.dropna(subset=['iso_speed', 'exposure_time'])
    valid_data2 = valid_data2[valid_data2['exposure_time'] <= 0.008]
    if len(valid_data2) > 5000:
        valid_data2 = valid_data2.sample(5000, random_state=42)
    if len(valid_data2) > 0:
        scatter2 = ax9.scatter(valid_data2['iso_speed'], valid_data2['exposure_time'], 
                              c=valid_data2['focal_length'], cmap='plasma', s=50, alpha=0.6, edgecolors='black', linewidth=0.5)
        ax9.set_title('ISO vs Exposure Time (≤ 0.008s, colored by Focal Length)', fontsize=14, fontweight='bold')
        ax9.set_xlabel('ISO Speed', fontweight='bold')
        ax9.set_ylabel('Exposure Time (seconds)', fontweight='bold')
        cbar2 = plt.colorbar(scatter2, ax=ax9)
        cbar2.set_label('Focal Length (mm)', fontweight='bold')
    
    plt.tight_layout()
    return fig


def create_analysis_visualizations(df_clean, output_dir=None):
    """Create analysis visualization dashboard (9 charts)"""
    print("Creating analysis visualization dashboard...")
    
    fig = plt.figure(figsize=(24, 18))
    
    # Prepare data
    df_clean_viz = df_clean.copy()
    df_clean_viz['f_stop_corrected'] = df_clean_viz['f_stop'] / 10
    
    # Extract dates for temporal graphs
    if 'datetime_taken' in df_clean_viz.columns:
        df_dates = pd.to_datetime(df_clean_viz['datetime_taken'], errors='coerce')
    else:
        df_dates = None
    
    # 1. Photos by camera over time (monthly aggregation)
    if df_dates is not None:
        ax1 = plt.subplot(3, 3, 1)
        df_dates_valid = df_dates.dropna()
        
        df_with_dates = pd.DataFrame({
            'month': pd.Series(df_dates_valid.values).dt.to_period('M'),
            'camera': df_clean_viz.loc[df_dates_valid.index, 'camera_model']
        }).dropna()
        
        if len(df_with_dates) > 0:
            camera_month_counts = df_with_dates.groupby(['month', 'camera']).size().unstack(fill_value=0)
            if len(camera_month_counts.columns) > 0:
                camera_month_counts.index = [period.strftime('%b %Y') for period in camera_month_counts.index]
                camera_month_counts.plot(ax=ax1, marker='o', linewidth=2, markersize=6)
                ax1.set_title('Photos Taken by Camera Over Time (Monthly)', fontsize=14, fontweight='bold')
                ax1.set_xlabel('Month', fontweight='bold')
                ax1.set_ylabel('Number of Photos', fontweight='bold')
                ax1.legend(title='Camera', loc='best', fontsize=9)
                ax1.grid(True, alpha=0.3)
                ax1.set_xticks(range(len(camera_month_counts)))
                ax1.set_xticklabels(camera_month_counts.index, rotation=45, ha='right', fontsize=9)
    
    # 2. Average focal length by camera
    ax2 = plt.subplot(3, 3, 2)
    focal_by_camera = df_clean_viz.groupby('camera_model')['focal_length'].mean().sort_values()
    ax2.barh(range(len(focal_by_camera)), focal_by_camera.values, color='skyblue', edgecolor='black', linewidth=1)
    ax2.set_yticks(range(len(focal_by_camera)))
    ax2.set_yticklabels(focal_by_camera.index)
    ax2.set_title('Average Focal Length by Camera', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Average Focal Length (mm)', fontweight='bold')
    for i, val in enumerate(focal_by_camera.values):
        ax2.text(val, i, f' {val:.1f}', va='center', fontweight='bold')
    
    # 3. Average ISO by camera
    ax3 = plt.subplot(3, 3, 3)
    iso_by_camera = df_clean_viz.groupby('camera_model')['iso_speed'].mean().sort_values()
    ax3.barh(range(len(iso_by_camera)), iso_by_camera.values, color='lightcoral', edgecolor='black', linewidth=1)
    ax3.set_yticks(range(len(iso_by_camera)))
    ax3.set_yticklabels(iso_by_camera.index)
    ax3.set_title('Average ISO by Camera', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Average ISO Speed', fontweight='bold')
    for i, val in enumerate(iso_by_camera.values):
        ax3.text(val, i, f' {val:.0f}', va='center', fontweight='bold')
    
    # 4. Focal length usage frequency (categorized)
    ax4 = plt.subplot(3, 3, 4)
    df_clean_viz['focal_range'] = pd.cut(df_clean_viz['focal_length'], 
                                     bins=[0, 35, 85, 135, 200], 
                                     labels=['Wide (0-35mm)', 'Standard (35-85mm)', 'Tele (85-135mm)', 'Extra Tele (135+)'])
    focal_range_counts = df_clean_viz['focal_range'].value_counts()
    colors_focal = plt.cm.Set2(np.linspace(0, 1, len(focal_range_counts)))
    ax4.pie(focal_range_counts.values, labels=focal_range_counts.index, autopct='%1.1f%%',
            colors=colors_focal, startangle=45, textprops={'fontsize': 11, 'weight': 'bold'})
    ax4.set_title('Focal Length Ranges', fontsize=14, fontweight='bold')
    
    # 5. Exposure bias distribution
    ax5 = plt.subplot(3, 3, 5)
    sns.histplot(data=df_clean_viz, x='exposure_bias', kde=True, ax=ax5, color='gold', bins=20, edgecolor='black', line_kws={'linewidth': 2})
    ax5.set_title('Exposure Bias (EV) Distribution', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Exposure Bias Value', fontweight='bold')
    ax5.set_ylabel('Count', fontweight='bold')
    ax5.legend(['KDE', 'Histogram'], loc='upper right')
    
    # 6. Photo count by hour
    if df_dates is not None:
        ax6 = plt.subplot(3, 3, 6)
        df_dates_valid = df_dates.dropna()
        hour_counts = df_dates_valid.dt.hour.value_counts().sort_index()
        ax6.bar(hour_counts.index, hour_counts.values, color='teal', edgecolor='black', linewidth=1)
        ax6.set_title('Photos Taken by Hour of Day', fontsize=14, fontweight='bold')
        ax6.set_xlabel('Hour of Day', fontweight='bold')
        ax6.set_ylabel('Number of Photos', fontweight='bold')
        ax6.set_xticks(range(0, 24, 2))
        ax6.grid(axis='y', alpha=0.3)
    
    # 7. Average ISO over time (monthly)
    if df_dates is not None:
        ax7 = plt.subplot(3, 3, 7)
        df_dates_valid = df_dates.dropna()
        
        df_with_iso = pd.DataFrame({
            'month': pd.Series(df_dates_valid.values).dt.to_period('M'),
            'iso_speed': df_clean_viz.loc[df_dates_valid.index, 'iso_speed']
        }).dropna()
        
        if len(df_with_iso) > 0:
            avg_iso_monthly = df_with_iso.groupby('month')['iso_speed'].mean()
            if len(avg_iso_monthly) > 0:
                monthly_labels = [period.strftime('%b %Y') for period in avg_iso_monthly.index]
                ax7.plot(range(len(avg_iso_monthly)), avg_iso_monthly.values, marker='o', linewidth=2.5, markersize=8, color='darkorange')
                ax7.set_xticks(range(len(avg_iso_monthly)))
                ax7.set_xticklabels(monthly_labels, rotation=45, ha='right', fontsize=9)
                ax7.set_title('Average ISO over Time (Monthly)', fontsize=14, fontweight='bold')
                ax7.set_xlabel('Month', fontweight='bold')
                ax7.set_ylabel('Average ISO Speed', fontweight='bold')
                ax7.grid(True, alpha=0.3)
    
    # 8. Average focal length over time (monthly)
    if df_dates is not None:
        ax8 = plt.subplot(3, 3, 8)
        df_dates_valid = df_dates.dropna()
        
        df_with_focal = pd.DataFrame({
            'month': pd.Series(df_dates_valid.values).dt.to_period('M'),
            'focal_length': df_clean_viz.loc[df_dates_valid.index, 'focal_length']
        }).dropna()
        
        if len(df_with_focal) > 0:
            avg_focal_monthly = df_with_focal.groupby('month')['focal_length'].mean()
            if len(avg_focal_monthly) > 0:
                monthly_labels = [period.strftime('%b %Y') for period in avg_focal_monthly.index]
                ax8.plot(range(len(avg_focal_monthly)), avg_focal_monthly.values, marker='s', linewidth=2.5, markersize=8, color='purple')
                ax8.set_xticks(range(len(avg_focal_monthly)))
                ax8.set_xticklabels(monthly_labels, rotation=45, ha='right', fontsize=9)
                ax8.set_title('Average Focal Length over Time (Monthly)', fontsize=14, fontweight='bold')
                ax8.set_xlabel('Month', fontweight='bold')
                ax8.set_ylabel('Average Focal Length (mm)', fontweight='bold')
                ax8.grid(True, alpha=0.3)
    
    # 9. Average hour of day over time (monthly)
    if df_dates is not None:
        ax9 = plt.subplot(3, 3, 9)
        df_dates_valid = df_dates.dropna()
        
        df_with_hour = pd.DataFrame({
            'month': pd.Series(df_dates_valid.values).dt.to_period('M'),
            'hour': pd.Series(df_dates_valid.values).dt.hour
        }).dropna()
        
        if len(df_with_hour) > 0:
            avg_hour_monthly = df_with_hour.groupby('month')['hour'].mean()
            if len(avg_hour_monthly) > 0:
                monthly_labels = [period.strftime('%b %Y') for period in avg_hour_monthly.index]
                ax9.plot(range(len(avg_hour_monthly)), avg_hour_monthly.values, marker='^', linewidth=2.5, markersize=8, color='green')
                ax9.set_xticks(range(len(avg_hour_monthly)))
                ax9.set_xticklabels(monthly_labels, rotation=45, ha='right', fontsize=9)
                ax9.set_title('Average Hour of Day over Time (Monthly)', fontsize=14, fontweight='bold')
                ax9.set_xlabel('Month', fontweight='bold')
                ax9.set_ylabel('Average Hour (0-23)', fontweight='bold')
                ax9.set_ylim(0, 23)
                ax9.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def print_statistics(df_clean):
    """Print analysis summary statistics"""
    print("\n" + "="*70)
    print("EXIF DATA ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\nTotal Photos: {len(df_clean)}")
    print(f"Camera Model(s): {df_clean['camera_model'].nunique()}")
    
    if df_clean['camera_model'].nunique() > 0:
        print(f"  Most used: {df_clean['camera_model'].value_counts().index[0]} ({df_clean['camera_model'].value_counts().values[0]} photos)")
    
    if 'iso_speed' in df_clean.columns:
        iso_data = df_clean['iso_speed'].dropna()
        if len(iso_data) > 0:
            print(f"\nISO Speed Range: {iso_data.min():.0f} - {iso_data.max():.0f}")
            print(f"  Most common ISO: {iso_data.mode().values[0]:.0f}")
            print(f"  Average ISO: {iso_data.mean():.0f}")
    
    if 'f_stop' in df_clean.columns:
        f_stop_corrected = df_clean['f_stop'] / 10
        f_stop_data = f_stop_corrected.dropna()
        if len(f_stop_data) > 0:
            print(f"\nF-Stop Range: f/{f_stop_data.min():.1f} - f/{f_stop_data.max():.1f}")
            print(f"  Most common F-Stop: f/{f_stop_data.mode().values[0]:.1f}")
            print(f"  Average F-Stop: f/{f_stop_data.mean():.1f}")
    
    if 'exposure_time' in df_clean.columns:
        exp_data = df_clean['exposure_time'].dropna()
        if len(exp_data) > 0:
            print(f"\nExposure Time: {exp_data.min():.6f}s - {exp_data.max():.6f}s")
            print(f"  Most common: {exp_data.mode().values[0]:.6f}s")
            print(f"  Average: {exp_data.mean():.6f}s")
    
    if 'focal_length' in df_clean.columns:
        focal_data = df_clean['focal_length'].dropna()
        if len(focal_data) > 0:
            print(f"\nFocal Length: {focal_data.min():.0f}mm - {focal_data.max():.0f}mm")
            print(f"  Most common: {focal_data.mode().values[0]:.0f}mm")
            print(f"  Average: {focal_data.mean():.1f}mm")
    
    if 'flash_mode' in df_clean.columns:
        print(f"\nFlash Usage:")
        flash_counts = df_clean['flash_mode'].fillna('Unknown').value_counts()
        for mode, count in flash_counts.items():
            pct = 100 * count / len(df_clean)
            print(f"  {mode}: {count} ({pct:.1f}%)")
    
    if 'exposure_bias' in df_clean.columns:
        bias_data = df_clean['exposure_bias'].dropna()
        if len(bias_data) > 0:
            print(f"\nExposure Bias: {bias_data.min():.1f} - {bias_data.max():.1f} EV")
            print(f"  Average: {bias_data.mean():.2f} EV")
    
    print("\n" + "="*70 + "\n")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='EXIF Data Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py exif_raw.csv
  python main.py exif_raw.csv --output-dir ./results --iso-threshold 6400
  python main.py exif_raw.csv --camera-crop-factors '{"ILCE-6400": 1.5, "RICOH GR IV": 1.5}'
        ''')
    
    parser.add_argument('input_csv', help='Path to raw EXIF CSV from extract_exif.py')
    parser.add_argument('--output-dir', default=None, help='Output directory for cleaned CSV and visualizations (default: same as input)')
    parser.add_argument('--iso-threshold', type=int, default=6400, help='Maximum ISO to keep (above is outlier, default: 6400)')
    parser.add_argument('--camera-crop-factors', default='{}', help='JSON dict of camera crop factors (e.g., \'{"ILCE-6400": 1.5}\')')
    
    args = parser.parse_args()
    
    # Validate input
    input_csv = Path(args.input_csv)
    if not input_csv.exists():
        print(f"Error: Input file not found: {input_csv}")
        return 1
    
    # Parse camera crop factors
    try:
        camera_crop_factors = json.loads(args.camera_crop_factors) if args.camera_crop_factors != '{}' else None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid camera-crop-factors JSON: {e}")
        return 1
    
    # Determine output directory
    if args.output_dir is None:
        output_dir = input_csv.parent
    else:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("EXIF DATA ANALYSIS PIPELINE")
    print(f"{'='*70}\n")
    
    # Clean EXIF data
    output_csv = output_dir / 'exif_data_cleaned.csv'
    df_cleaned = clean_exif_data(
        str(input_csv),
        str(output_csv),
        iso_threshold=args.iso_threshold,
        camera_crop_factors=camera_crop_factors
    )
    
    # Extract dates
    extract_dates_from_csv(df_cleaned, output_dir)
    
    # Print statistics
    print_statistics(df_cleaned)
    
    # Create visualizations
    fig1 = create_main_visualizations(df_cleaned, output_dir)
    fig2 = create_analysis_visualizations(df_cleaned, output_dir)
    
    # Save figures
    output_dir.mkdir(parents=True, exist_ok=True)
    fig1_path = output_dir / 'exif_visualization_main.png'
    fig2_path = output_dir / 'exif_visualization_analysis.png'
    
    fig1.savefig(fig1_path, dpi=150, bbox_inches='tight')
    print(f"Saved main visualization to: {fig1_path}")
    
    fig2.savefig(fig2_path, dpi=150, bbox_inches='tight')
    print(f"Saved analysis visualization to: {fig2_path}")
    
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}\n")
    print(f"Output files:")
    print(f"  - {output_csv}")
    print(f"  - {output_dir / 'exif_dates.csv'}")
    print(f"  - {fig1_path}")
    print(f"  - {fig2_path}\n")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
