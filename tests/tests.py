import pytest

from extract_exif import *
from main import main

@pytest.fixture(autouse=True)
def setup():
    # Specify your root directory here
    ROOT_PATH = r"D:\Photos"

    # Optional: Specify output CSV path, or leave as None to use default
    CSV_LOCATION = "./exif_data.csv"
    return ROOT_PATH, CSV_LOCATION

def test_main_only(setup):
    ROOT_PATH, CSV_LOCATION = setup
    assert main(input_csv=CSV_LOCATION, output_dir="./", iso_threshold=6400) == 0

def test_piexif(setup):
    ROOT_PATH, CSV_LOCATION = setup
    df = crawl_and_extract_exif(ROOT_PATH, output_csv=CSV_LOCATION, method="piexif" ,max_files=100)
    print("\nFirst few rows of the dataframe:")
    print(df.head())
    assert main(input_csv=CSV_LOCATION, output_dir="./", iso_threshold=6400) == 0

def test_exifread(setup):
    ROOT_PATH, CSV_LOCATION = setup
    df = crawl_and_extract_exif(ROOT_PATH, output_csv=CSV_LOCATION, method="exifread", max_files=100)
    print("\nFirst few rows of the dataframe:")
    print(df.head())
    assert main(input_csv=CSV_LOCATION, output_dir="./", iso_threshold=6400) == 0


def test_is_same_output(setup):
    ROOT_PATH, CSV_LOCATION = setup
    df = crawl_and_extract_exif(ROOT_PATH, output_csv=CSV_LOCATION, max_files=100)
    print("\nFirst few rows of the dataframe:")
    print(df.head())
    assert 2>1 # add assertion here

