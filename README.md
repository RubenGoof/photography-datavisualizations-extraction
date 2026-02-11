# extract_exif.py

Extracts EXIF metadata from raw image files (.ARW, .DNG) and standard image formats, crawling all subdirectories recursively. Supports multiple extraction methods (piexif, PIL, rawpy) with automatic fallback for robust compatibility. Outputs a comprehensive CSV file with 63+ EXIF fields including camera model, ISO, aperture, exposure time, focal length, and datetime. Processes all images found in the specified directory tree and generates a detailed metadata database for analysis and photography review.
