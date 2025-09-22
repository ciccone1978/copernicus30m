import os
import boto3
import botocore
from PySide6.QtCore import QThread, Signal

# Helper function to format tile names (moved here for encapsulation)
def format_tile_s3_key(lat, lon):
    """Formats lat/lon into the full S3 key for a tile."""
    lat_str = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_str = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
    base_name = f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"
    return f"{base_name}/{base_name}.tif"

class DownloadWorker(QThread):
    """
    A QThread worker for downloading Copernicus DEM tiles from AWS S3.
    """
    # Signal arguments: (current_value, total_value)
    progress_updated = Signal(int, int)
    # Signal argument: (message_string)
    tile_finished = Signal(str)
    # Signal argument: (error_message_string)
    error_occurred = Signal(str)
    # Signal with no arguments
    finished = Signal()

    def __init__(self, tiles_to_download, save_path):
        """
        Args:
            tiles_to_download (list): A list of (lat, lon) tuples.
            save_path (str): The absolute path to the directory to save files in.
        """
        super().__init__()
        self.tiles = tiles_to_download
        self.save_path = save_path
        self.s3_client = None

    def run(self):
        """The main entry point for the thread's execution."""
        try:
            self.s3_client = boto3.client('s3', config=botocore.client.Config(signature_version=botocore.UNSIGNED))
            total_tiles = len(self.tiles)
            
            for i, (lat, lon) in enumerate(self.tiles):
                s3_key = format_tile_s3_key(lat, lon)
                file_name = os.path.basename(s3_key)
                local_path = os.path.join(self.save_path, file_name)

                try:
                    # Check if file already exists
                    if os.path.exists(local_path):
                        self.tile_finished.emit(f"Skipped (already exists): {file_name}")
                    else:
                        self.tile_finished.emit(f"Downloading: {file_name}...")
                        self.s3_client.download_file("copernicus-dem-30m", s3_key, local_path)
                        self.tile_finished.emit(f"Finished: {file_name}")

                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == "404":
                        self.error_occurred.emit(f"Error: Tile not found on server: {file_name}")
                    else:
                        self.error_occurred.emit(f"Network Error for {file_name}: {e}")
                
                # Update overall progress after each attempt
                self.progress_updated.emit(i + 1, total_tiles)

        except Exception as e:
            self.error_occurred.emit(f"A critical error occurred: {e}")
        finally:
            self.finished.emit()