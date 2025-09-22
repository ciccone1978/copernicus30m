import sys
import os

from PySide6.QtCore import Qt, QUrl, Slot, QSize, QObject, Signal
from PySide6.QtGui import QAction, QIcon 
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QLabel,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QProgressBar,
    QListWidgetItem,
    QFileDialog, 
    QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from local_http_server import LocalHttpServer
from download_worker import DownloadWorker

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_tiles = set()
        self.worker = None 

        self.setWindowTitle("Copernicus DEM Tile Downloader")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # --- Start the local HTTP server ---
        self.map_dir_path = os.path.join(self.base_dir, "map")
        self.http_server = LocalHttpServer(port=8001, serve_dir=self.map_dir_path)
        self.http_server.server_started.connect(self.load_map_url)
        self.http_server.start()

        # --- Create UI components ---
        main_splitter = QSplitter(Qt.Horizontal)
        self.map_view = QWebEngineView()

        self.sidebar_panel = self._create_sidebar()
        
        main_splitter.addWidget(self.map_view)
        main_splitter.addWidget(self.sidebar_panel)
        main_splitter.setSizes([900, 300])

        self.setCentralWidget(main_splitter)

        # --- Setup Menu, Toolbar, and Status Bar ---
        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
               
        # --- Setup the Web Channel for JS-Python communication ---
        self._setup_web_channel()

    # --- A dedicated method to create and return the sidebar widget ---
    def _create_sidebar(self):
        """Creates the sidebar widget with all its UI elements."""
        # Use a QWidget as a container for the layout
        container = QWidget()
        
        # Use a Vertical Box Layout
        layout = QVBoxLayout()
        container.setLayout(layout)

        # 1. Title Label
        title_label = QLabel("Selected Tiles")
        # You can style it for better appearance
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        
        # 2. List Widget
        self.tile_list_widget = QListWidget()
        self.tile_list_widget.setToolTip("List of DEM tiles selected on the map.")

        # 3. Download Button
        self.download_button = QPushButton("Download Selected Tiles")
        self.download_button.setToolTip("Download all tiles in the list.")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)

        # 4. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100) # Percentage based
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setToolTip("Download progress")
        self.progress_bar.hide() # Hide it until a download starts

        # Add widgets to the layout in order
        layout.addWidget(title_label)
        layout.addWidget(self.tile_list_widget)
        layout.addWidget(self.download_button)
        layout.addWidget(self.progress_bar)

        return container    

    @Slot(str, int)
    def load_map_url(self, host, port):
        """
        This method is called ONLY when the http_server emits the server_started signal.
        This guarantees the server is ready before we try to connect.
        """
        print(f"Server is ready. Loading map from http://{host}:{port}/index.html")
        self.map_view.setUrl(QUrl(f"http://{host}:{port}/index.html"))

    # --- NEW: Methods for handling the download process ---
    @Slot()
    def start_download(self):
        """Initiates the file download process."""
        if not self.selected_tiles:
            QMessageBox.information(self, "No Tiles Selected", "Please select one or more tiles on the map before downloading.")
            return

        save_path = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            os.path.expanduser("~") # Start in the user's home directory
        )

        if not save_path: # User cancelled the dialog
            return

        # --- UI State: Preparing for download ---
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.download_button.setEnabled(False)
        self.tile_list_widget.setEnabled(False) # Prevent changes during download
        self.statusBar().showMessage("Starting download...")

        # --- Create and start the worker ---
        self.worker = DownloadWorker(list(self.selected_tiles), save_path)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.tile_finished.connect(self.update_status_message)
        self.worker.error_occurred.connect(self.show_error_message)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.start()

    @Slot(int, int)
    def update_progress(self, current_value, total_value):
        """Updates the progress bar."""
        self.progress_bar.setMaximum(total_value)
        self.progress_bar.setValue(current_value)

    @Slot(str)
    def update_status_message(self, message):
        """Shows a temporary message in the status bar."""
        self.statusBar().showMessage(message, 5000)

    @Slot(str)
    def show_error_message(self, message):
        """Shows an error in the status bar or a dialog."""
        self.statusBar().showMessage(message, 10000) # Show errors for longer
        # For more critical errors, you could use a QMessageBox:
        # QMessageBox.warning(self, "Download Error", message)

    @Slot()
    def on_download_finished(self):
        """Called when the worker thread has finished."""
        self.statusBar().showMessage("All downloads completed!", 10000)
        self.progress_bar.hide()
        self.download_button.setEnabled(True)
        self.tile_list_widget.setEnabled(True)
        self.worker = None # Allow the worker to be garbage collected
        QMessageBox.information(self, "Download Complete", "All selected tiles have been processed.")    

    def closeEvent(self, event):
        """Ensure worker is stopped if running when window is closed."""
        if self.worker and self.worker.isRunning():
            # A more advanced implementation might ask the user for confirmation
            self.worker.quit() # Request the thread to stop
            self.worker.wait() # Wait for it to finish
        self.http_server.stop()
        self.http_server.wait()
        event.accept()

    def _setup_actions(self):
        """Create the application's actions (reusable commands)."""

        # --- Exit Action ---
        exit_icon_path = os.path.join(self.base_dir, "icons", "control-power.png")
        self.exit_action = QAction(QIcon(exit_icon_path), "&Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(QApplication.instance().quit)

        # --- Toggle Grid Action ---
        grid_icon_path = os.path.join(self.base_dir, "icons", "grid.png")
        self.toggle_grid_action = QAction(QIcon(grid_icon_path), "Show/Hide &Grid", self)
        self.toggle_grid_action.setShortcut("Ctrl+G")
        self.toggle_grid_action.setStatusTip("Show or hide the 1x1 degree grid")
        self.toggle_grid_action.setCheckable(True)
        self.toggle_grid_action.setChecked(True)
        self.toggle_grid_action.toggled.connect(self.on_toggle_grid)

    def _setup_menu(self):
        """Create the main menu bar."""
        
        menu = self.menuBar()
        
        # --- File Menu ---
        file_menu = menu.addMenu("&File")
        file_menu.addAction(self.exit_action)

        # --- View Menu ---
        view_menu = menu.addMenu("&View")
        view_menu.addAction(self.toggle_grid_action)

    def _setup_toolbar(self):
        """Create the main toolbar."""
        
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24)) # Set a nice size for the icons
        toolbar.addAction(self.exit_action)
        toolbar.addSeparator()
        toolbar.addAction(self.toggle_grid_action)

    def _setup_statusbar(self):
        """Create the status bar."""
        
        self.setStatusBar(QStatusBar(self))       
        self.statusBar().showMessage("Welcome to the Copernicus DEM Downloader!", 5000)
        
        self.coord_label = QLabel("Lat: N/A, Lon: N/A")
        self.zoom_label = QLabel("Zoom: N/A")
        self.zoom_label.setContentsMargins(10, 0, 5, 0) 

        self.statusBar().addPermanentWidget(self.zoom_label)
        self.statusBar().addPermanentWidget(self.coord_label)


    # --- Method to set up the QWebChannel ---
    def _setup_web_channel(self):
        """Initializes the QWebChannel to enable JS-to-Python communication."""
        
        self.channel = QWebChannel(self.map_view.page())
        self.map_view.page().setWebChannel(self.channel)

        self.bridge = MapBridge()
        self.channel.registerObject("backend", self.bridge)

        self.bridge.coordinates_changed.connect(self.update_coord_label)
        self.bridge.tile_clicked.connect(self.on_tile_selected)

    # --- The slot that updates the status bar label ---
    @Slot(str)
    def update_coord_label(self, coords_text, zoom_level):
        self.coord_label.setText(coords_text)    
        self.zoom_label.setText(f"Zoom: {zoom_level}")

    # --- The slot that responds to the toggle action ---
    @Slot(bool)
    def on_toggle_grid(self, is_checked):
        """
        Executes JavaScript in the web view to show or hide the grid.
        
        Args:
            is_checked (bool): The new state of the action, passed by the 'toggled' signal.
        """
        if self.map_view.page().url().isEmpty():
             # Don't try to run JS if the page isn't loaded yet
            return

        print(f"Toggling grid visibility to: {is_checked}")
        # The argument to the JS function must be 'true' or 'false' (lowercase)
        js_code = f"toggleGridVisibility({str(is_checked).lower()});"
        self.map_view.page().runJavaScript(js_code)

    # --- Helper function to format the tile name ---
    def format_tile_name(self, lat, lon):
        """Formats lat/lon coordinates into the standard Copernicus tile name."""
        lat_str = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
        lon_str = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
        # We only need the base name for the list, not the full S3 key
        return f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"

    # --- The main logic handler for tile selection ---
    @Slot(int, int)
    def on_tile_selected(self, lat, lon):
        """
        Manages the state of selected tiles when a tile is clicked on the map.
        
        Args:
            lat (int): Integer latitude of the clicked tile's SW corner.
            lon (int): Integer longitude of the clicked tile's SW corner.
        """
        tile = (lat, lon) # Use a tuple to represent the tile
        tile_name = self.format_tile_name(lat, lon)

        if tile in self.selected_tiles:
            # --- Tile is already selected, so DESELECT it ---
            self.selected_tiles.remove(tile)
            print(f"Deselected tile: {tile}. Total selected: {len(self.selected_tiles)}")
            # Command JavaScript to remove the highlight
            js_code = f"removeHighlight({lat}, {lon});"
            self.map_view.page().runJavaScript(js_code)
            
            # --- Remove from sidebar list ---
            # Find the item in the list widget and remove it.
            items = self.tile_list_widget.findItems(tile_name, Qt.MatchExactly)
            if items:
                row = self.tile_list_widget.row(items[0])
                self.tile_list_widget.takeItem(row)
        else:
            # --- Tile is not selected, so SELECT it ---
            self.selected_tiles.add(tile)
            print(f"Selected tile: {tile}. Total selected: {len(self.selected_tiles)}")
            # Command JavaScript to add the highlight
            js_code = f"addHighlight({lat}, {lon});"
            self.map_view.page().runJavaScript(js_code)

            # --- Add to sidebar list ---
            # Create a QListWidgetItem and add it to the list widget.
            list_item = QListWidgetItem(tile_name)
            self.tile_list_widget.addItem(list_item)
            # You can also store the raw coordinates in the item for later use
            list_item.setData(Qt.UserRole, tile)

            # --- Update the state of the download button ---
            # The button should only be enabled if there is at least one item selected.
            is_list_empty = self.tile_list_widget.count() == 0
            self.download_button.setEnabled(not is_list_empty)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())