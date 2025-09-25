import os
import logging
from PySide6.QtCore import QObject, Slot, QUrl, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtWebChannel import QWebChannel

from main_window import MainWindow
from local_http_server import LocalHttpServer
from selection_model import SelectionModel
from download_worker import DownloadWorker, format_tile_s3_key
from about_dialog import AboutDialog

logger = logging.getLogger(__name__)

# --- Define the Bridge class ---
class MapBridge(QObject):
    """
    A bridge object to facilitate communication from JavaScript to Python.
    It exposes 'slots' that can be called from JS and emits 'signals'
    that the main application can connect to.
    """
    # Signal that will carry the coordinate string and zoom level to the main window
    coordinates_changed = Signal(str, int)
    tile_clicked = Signal(int, int)

    @Slot(float, float, int)
    def on_mouse_move(self, lat, lng, zoom):
        """
        A slot that is called from JavaScript whenever the mouse moves over the map.
        
        Args:
            lat (float): Latitude of the mouse cursor.
            lng (float): Longitude of the mouse cursor.
            zoom (int): The current zoom level of the map.
        """
        formatted_coords = f"Lat: {lat:.5f}, Lon: {lng:.5f}"
        self.coordinates_changed.emit(formatted_coords, zoom)
        
    # --- Slot that receives the raw tile click from JS ---
    @Slot(int, int)
    def on_tile_clicked(self, lat, lon):
        self.tile_clicked.emit(lat, lon) 


# --- Controller class ---
class AppController(QObject):
    """
    The main controller for the application.
    
    Responsibilities:
    - Creates and manages the main window (the View).
    - Starts and stops background services (like the HTTP server).
    - Connects signals from the View to its slots (application logic).
    """
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.worker = None

        # The controller creates and owns both the Model and the View.
        self.model = SelectionModel()
        self.view = MainWindow(self.base_dir)

        # Start the background services
        self._start_http_server()
        self._setup_web_channel()

        # Connect signals from the view to the controller's logic slots
        self._connect_signals()

    def _start_http_server(self):
        """Initializes and starts the local HTTP server in a background thread."""
        map_dir_path = os.path.join(self.base_dir, "map")
        self.http_server = LocalHttpServer(port=8001, serve_dir=map_dir_path)
        self.http_server.server_started.connect(self.on_server_ready)
        self.http_server.start()
        logger.debug("Local HTTP server thread started.")

    def _setup_web_channel(self):
        """Initializes the QWebChannel to enable JS-to-Python communication."""
        self.channel = QWebChannel()
        self.bridge = MapBridge()
        self.channel.registerObject("backend", self.bridge)
        self.view.set_web_channel(self.channel)

    def _connect_signals(self):
        """Connects signals from the view to slots in this controller."""
        
        self.view.toggle_grid_visibility_requested.connect(self.on_toggle_grid)
        self.view.clear_selection_requested.connect(self.on_clear_selection)
        self.view.download_requested.connect(self.start_download)
        self.view.stop_download_requested.connect(self.stop_download)
        self.view.window_closed.connect(self.cleanup)
        self.view.about_requested.connect(self.show_about_dialog)

        self.bridge.coordinates_changed.connect(self.on_coordinates_changed)
        self.bridge.tile_clicked.connect(self.on_tile_selected)

        self.model.selection_changed.connect(self.on_selection_changed)
        

    def show(self):
        """Tells the view to show itself."""
        self.view.showMaximized()

    @Slot(str, int)
    def on_server_ready(self, host, port):
        """
        Slot that is called when the HTTP server is running.
        It tells the view to load the map URL.
        """
        logger.info(f"Server is ready. Telling View to load map from http://{host}:{port}/index.html")
        url = QUrl(f"http://{host}:{port}/index.html")
        self.view.set_map_url(url)


    @Slot(bool)
    def on_toggle_grid(self, is_checked):
        """
        Executes JavaScript in the web view to show or hide the grid.
        
        Args:
            is_checked (bool): The new state of the action, passed by the 'toggled' signal.
        """
        if not self.view.is_map_ready():
            logger.info(f"Map is not ready for JS commands yet.")
            return

        logger.debug(f"Toggling grid visibility to: {is_checked}")
                
        js_code = f"toggleGridVisibility({str(is_checked).lower()});"
        self.view.run_javascript(js_code)    

    @Slot()
    def on_clear_selection(self):
        """Clears the current selection in both the model and the view."""
        logger.debug("Clearing all selected tiles from model and view.")
        
        # Clear the model's selection
        self.model.clear_selection()
        
        # Command the view to remove all highlights
        if self.view.is_map_ready():
            self.view.run_javascript("clearAllHighlights();")
        else:
            logger.info("Map is not ready for JS commands yet; cannot clear highlights.")
        
        # Update the sidebar list and button state
        #self.view.update_tile_list([])
        #self.view.update_download_button_state(False)


    @Slot(str, int)
    def on_coordinates_changed(self, coords_text, zoom_level):
        """Commands the View to update its status bar display."""
        self.view.update_coord_display(coords_text, zoom_level)    

    @Slot(int, int)
    def on_tile_selected(self, lat, lon):
        """
        Handles the direct click event from the map. This is the primary handler
        for updating the map's visual state and the data model.
        """
        tile = (lat, lon)
        logger.debug(f"Tile click received for ({lat}, {lon}).")
        
        if tile in self.model.get_selected_tiles():
            self.view.run_javascript(f"removeHighlight({lat}, {lon});")
        else:
            self.view.run_javascript(f"addHighlight({lat}, {lon});")
        
        # After commanding the view, update the model.
        self.model.toggle_selection(tile)
    
    @Slot(set)
    def on_selection_changed(self, selected_tiles):
        """
        Handles updates when the data model changes. This should only update
        UI elements that depend on the entire list, like the sidebar.
        """
        logging.debug(f"Model selection changed. New selection: {selected_tiles}")

        tile_names = [self.format_tile_name(*tile) for tile in sorted(list(selected_tiles))]
        self.view.update_tile_list(tile_names)
        self.view.update_download_button_state(self.model.has_selection())
        self.view.update_tile_count(len(selected_tiles))


    # --- The main slot to handle the download request from the View ---
    @Slot()
    def start_download(self):
        """
        Orchestrates the entire download process, from user input to starting the worker.
        """
        if self.worker is not None and self.worker.isRunning():
            logging.info("Download already in progress.")
            return
        
        # 1. Ask user for a save directory
        save_path = QFileDialog.getExistingDirectory(self.view, "Select Save Directory", os.path.expanduser("~"))
        if not save_path:
            return # User cancelled

        # 2. Ask user how to handle existing files
        overwrite_mode = self._handle_existing_files(save_path)
        if overwrite_mode is None:
            return # User cancelled

        # 3. Command the View to enter its "downloading" state
        self.view.set_download_state(is_downloading=True)
        
        # 4. Create, configure, and start the worker
        self.worker = DownloadWorker(list(self.model.get_selected_tiles()), save_path, overwrite_mode)
        logging.info(f"Starting download worker with {len(self.model.get_selected_tiles())} tiles to process.")
        
        # 5. Connect signals from the worker to the controller's slots (or directly to the view)
        self.worker.file_progress.connect(lambda cur, tot: self.view.show_status_message(f"Processing file {cur} of {tot}...", 0))
        self.worker.total_progress_updated.connect(self.view.progress_bar.setValue)
        self.worker.total_progress_updated.connect(lambda _, tot: self.view.progress_bar.setMaximum(tot))
        self.worker.status_update.connect(self.view.show_status_message)
        self.worker.error_occurred.connect(lambda msg: self.view.show_status_message(f"ERROR: {msg}", 10000))
        self.worker.finished.connect(self.on_download_finished)
        
        self.worker.start()


    def _handle_existing_files(self, save_path):
        """Checks for existing files and asks the user how to proceed via a dialog."""
        existing_files = [
            os.path.basename(format_tile_s3_key(*tile)) 
            for tile in self.model.get_selected_tiles()
            if os.path.exists(os.path.join(save_path, os.path.basename(format_tile_s3_key(*tile))))
        ]
        
        if not existing_files:
            return 'overwrite' # No conflicts, proceed normally
        
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("Files Already Exist")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText(f"{len(existing_files)} of the selected files already exist.")
        msg_box.setInformativeText("Would you like to overwrite them or skip them?")
        
        overwrite_button = msg_box.addButton("Overwrite All", QMessageBox.AcceptRole)
        skip_button = msg_box.addButton("Skip Existing", QMessageBox.DestructiveRole)
        cancel_button = msg_box.addButton("Cancel Download", QMessageBox.RejectRole)
        
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == overwrite_button:
            return 'overwrite'
        elif clicked == skip_button:
            return 'skip'
        else: # User clicked Cancel or closed the dialog
            return None


    # --- cSlot to handle the stop request from the View ---
    @Slot()
    def stop_download(self):
        """Signals the running worker to stop."""
        if self.worker:
            self.view.show_status_message("Stopping download...", 0)
            self.worker.stop()

    # --- Slot that cleans up after the download is finished or cancelled ---
    @Slot()
    def on_download_finished(self):
        """Handles the UI reset when the worker is finished."""
        
        logging.info("Download worker has finished.")

        if self.worker is None:
            logging.info("No worker instance found on download finish.")
            return

        self.worker.finished.disconnect(self.on_download_finished)

        was_cancelled = self.worker._is_stopped
        logging.debug(f"Download worker finished. Cancelled: {was_cancelled}")
        
        # Command the view to return to its idle state
        self.view.set_download_state(is_downloading=False)
        self.view.update_download_button_state(self.model.has_selection())
        self.worker = None

        if was_cancelled:
            msg = "Download cancelled."            
        else:
            msg = "All downloads completed!"
            QMessageBox.information(self.view, "Download Complete", "All selected tiles have been processed.")
        
        self.view.show_status_message(msg, 10000)


    @Slot()
    def cleanup(self):
        """Ensures background threads are stopped when the app closes."""
        logger.info("Cleaning up background services...")

        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.http_server.stop()
        self.http_server.wait()
        
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
        

    @Slot()
    def show_about_dialog(self):
        """Creates and shows the 'About' dialog."""
        dialog = AboutDialog(self.view)
        dialog.exec()


    # --- Helper method for the controller ---
    def format_tile_name(self, lat, lon):
        """Formats lat/lon coordinates into the user-friendly tile name."""
        lat_str = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
        lon_str = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
        return f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"    