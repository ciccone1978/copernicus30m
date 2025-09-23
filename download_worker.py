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
    
    file_progress = Signal(int, int)
    total_progress_updated = Signal(int, int)
    tile_finished = Signal(str)
    error_occurred = Signal(str)
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
        self._is_stopped = False

    def run(self):
        """The main entry point for the thread's execution."""
        try:
            self.s3_client = boto3.client('s3', config=botocore.client.Config(signature_version=botocore.UNSIGNED))
            
            # --- Pre-flight check to calculate total size ---
            self.tile_finished.emit("Calculating total download size...")
            grand_total_size = 0
            for lat, lon in self.tiles:
                if self._is_stopped: 
                    break

                s3_key = format_tile_s3_key(lat, lon)
                local_path = os.path.join(self.save_path, os.path.basename(s3_key))
                # Don't include size of files that already exist
                if not os.path.exists(local_path):
                    try:
                        response = self.s3_client.head_object(Bucket="copernicus-dem-30m", Key=s3_key)
                        grand_total_size += int(response.get('ContentLength', 0))
                    except botocore.exceptions.ClientError:
                        pass 
            
            if self._is_stopped:
                self.tile_finished.emit("Download cancelled during size calculation.")
                self.finished.emit()
                return

            # --- Main Download Loop ---
            cumulative_bytes_downloaded = 0
            total_tiles = len(self.tiles)
                        
            for i, (lat, lon) in enumerate(self.tiles):
                if self._is_stopped:
                    self.tile_finished.emit("Download cancelled by user.")
                    break
                
                self.file_progress.emit(i + 1, total_tiles)

                s3_key = format_tile_s3_key(lat, lon)
                file_name = os.path.basename(s3_key)
                local_path = os.path.join(self.save_path, file_name)

                try:
                    if os.path.exists(local_path):
                        self.tile_finished.emit(f"Skipped (already exists): {file_name}")
                        continue
                        
                    self.tile_finished.emit(f"Downloading: {file_name}...")
                    s3_object = self.s3_client.get_object(Bucket="copernicus-dem-30m", Key=s3_key)
                    streaming_body = s3_object['Body']
                        
                    with open(local_path, 'wb') as f:
                        # Read and write in 1MB chunks
                        for chunk in streaming_body.iter_chunks(chunk_size=1024 * 1024):
                            
                            if self._is_stopped:
                                # Clean up the partially downloaded file
                                f.close()
                                streaming_body.close()
                                os.remove(local_path)
                                self.tile_finished.emit(f"Cancelled: {file_name}")
                                break
                                
                            f.write(chunk)
                            chunk_size = len(chunk)
                            cumulative_bytes_downloaded += chunk_size                           
                            self.total_progress_updated.emit(cumulative_bytes_downloaded, grand_total_size)

                        else:
                            self.tile_finished.emit(f"Finished: {file_name}")
                                
                except botocore.exceptions.ClientError as e:
                    self.error_occurred.emit(f"Error for {file_name}: {e}")
                  
                if self._is_stopped:
                    break

        except Exception as e:
            self.error_occurred.emit(f"A critical error occurred: {e}")
        finally:
            self.finished.emit()


    def stop(self):
        """
        Sets the stop flag to True. The running loop will check this flag
        and exit gracefully.
        """
        print("Stop signal received by worker.")
        self._is_stopped = True        