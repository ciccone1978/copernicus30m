import argparse
import boto3
import botocore  # Corrected from 'botore'
import math
import os
import sys
import threading  # <-- CRITICAL FIX: Added the missing threading import
from tqdm import tqdm

class ProgressPercentage(object):
    """
    A callable class to track the progress of a Boto3 download and update a tqdm bar.
    """
    def __init__(self, filename, size):
        self._filename = os.path.basename(filename)
        self._size = float(size)
        self._seen_so_far = 0
        self._lock = threading.Lock()  # Lock to make updates thread-safe
        self._pbar = tqdm(
            total=self._size,
            unit='B',
            unit_scale=True,
            desc=self._filename,
            # A nice format for the progress bar
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'
        )

    def __call__(self, bytes_amount):
        """
        This method is called by boto3 with the number of bytes transferred.
        """
        with self._lock:
            self._seen_so_far += bytes_amount
            self._pbar.update(bytes_amount)

    def close(self):
        """Closes the tqdm progress bar."""
        self._pbar.close()

def calcola_e_gestisci_tile_copernicus(min_lon, min_lat, max_lon, max_lat, cartella_output, download=True):
    """
    Calculates Copernicus DEM GLO-30 tiles for a bounding box and either downloads them
    with a progress bar or prints their names.
    """
    
    # Initialize the S3 client for anonymous (public) access
    s3_client = boto3.client('s3', config=botocore.client.Config(signature_version=botocore.UNSIGNED))
    bucket_name = "copernicus-dem-30m"

    if download and not os.path.exists(cartella_output):
        os.makedirs(cartella_output)
        print(f"Created output directory: '{cartella_output}'")

    print(f"\nAnalyzing tiles for bounding box: [{min_lon}, {min_lat}, {max_lon}, {max_lat}]")

    # Calculate the integer grid of tiles to cover the bounding box
    lon_start = math.floor(min_lon)
    lat_start = math.floor(min_lat)
    lon_end = math.ceil(max_lon)
    lat_end = math.ceil(max_lat)

    # Generate the list of tile keys to process
    tiles_to_process = []
    for lat in range(lat_start, lat_end):
        for lon in range(lon_start, lon_end):
            lat_str = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
            lon_str = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
            
            nome_base_tile = f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"
            s3_key = f"{nome_base_tile}/{nome_base_tile}.tif"
            tiles_to_process.append(s3_key)

    if not tiles_to_process:
        print("No tiles found for the specified coordinates.")
        return

    print(f"Found {len(tiles_to_process)} potential tiles to process.")

    # Process each tile
    for s3_key in tiles_to_process:
        if not download:
            print(s3_key)
            continue

        nome_file_locale = os.path.basename(s3_key)
        percorso_file_output = os.path.join(cartella_output, nome_file_locale)
        
        if os.path.exists(percorso_file_output):
            print(f"Tile '{nome_file_locale}' already exists locally. Skipping download.")
            continue

        try:
            # Get file metadata (specifically its size) before downloading
            response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            file_size = response['ContentLength']
            
            # Create an instance of our progress bar callback
            progress = ProgressPercentage(nome_file_locale, file_size)

            # Start the download, passing our progress object as the Callback
            s3_client.download_file(
                bucket_name,
                s3_key,
                percorso_file_output,
                Callback=progress
            )
            progress.close()  # Ensure the progress bar is closed cleanly

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print(f"WARNING: Tile '{s3_key}' was not found in the S3 bucket.")
            else:
                print(f"ERROR: An unexpected error occurred downloading '{s3_key}': {e}")
    
    print("\nProcess completed.")


if __name__ == '__main__':
    # --- Command-Line Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Download Copernicus DEM GLO-30 tiles from AWS for a given bounding box (http://bboxfinder.com/).",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'bbox', type=float, nargs=4,
        metavar=('MIN_LON', 'MIN_LAT', 'MAX_LON', 'MAX_LAT'),
        help="The geographic bounding box coordinates in the order:\n"
             "min_longitude min_latitude max_longitude max_latitude\n"
             "Example: 11.8 46.5 12.2 46.7"
    )
    parser.add_argument(
        '-o', '--output', type=str, default="copernicus_dem_tiles",
        help="The output directory to save downloaded tiles.\n"
             "Default: 'copernicus_dem_tiles'"
    )
    parser.add_argument(
        '-p', '--print-only', action='store_true',
        help="If specified, print the names of the required tiles without downloading them."
    )

    args = parser.parse_args()
    min_lon, min_lat, max_lon, max_lat = args.bbox
    
    # --- Input Validation ---
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and
            -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        print("ERROR: Invalid coordinates. Longitude must be between -180 and 180, Latitude between -90 and 90.", file=sys.stderr)
        sys.exit(1)
        
    if min_lon >= max_lon or min_lat >= max_lat:
        print("ERROR: Minimum coordinates must be less than maximum coordinates.", file=sys.stderr)
        sys.exit(1)

    # --- Run Main Function ---
    calcola_e_gestisci_tile_copernicus(
        min_lon, min_lat, max_lon, max_lat,
        cartella_output=args.output,
        download=not args.print_only
    )