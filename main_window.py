import os
from PySide6.QtCore import Qt, QUrl, QSize, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar,
    QLabel,
    QVBoxLayout,
    QListWidget, 
    QPushButton,
    QProgressBar, 
    QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

class MainWindow(QMainWindow):
    """
    The main application window (the "View").
    """
    window_closed = Signal()
    toggle_grid_visibility_requested = Signal(bool)
    download_requested = Signal()
    stop_download_requested = Signal()

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

        self.setWindowTitle("Copernicus DEM Downloader")

        # Load icons
        self.download_icon = QIcon(os.path.join(self.base_dir, "icons", "download-cloud.png"))
        self.stop_icon = QIcon(os.path.join(self.base_dir, "icons", "cross-circle.png"))
        self.grid_icon = QIcon(os.path.join(self.base_dir, "icons", "grid.png"))

        # --- Create Core Layout ---
        main_splitter = QSplitter(Qt.Horizontal)
        self.map_view = QWebEngineView()
        self.sidebar_widget = self._create_sidebar()

        main_splitter.addWidget(self.map_view)
        main_splitter.addWidget(self.sidebar_widget)
        main_splitter.setSizes([900, 300]) # Set initial proportions
        self.setCentralWidget(main_splitter)

        # --- Setup Standard UI Elements ---
        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()


    def _create_sidebar(self):
        """Creates the sidebar widget with all its UI elements."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        title_label = QLabel("Selected Tiles")
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        
        self.tile_list_widget = QListWidget()
        self.tile_list_widget.setToolTip("List of DEM tiles selected on the map.")
        
        self.download_button = QPushButton("Download Selected Tiles")
        self.download_button.setIcon(self.download_icon)
        self.download_button.setEnabled(False) # Initially disabled
        self.download_button.clicked.connect(self.on_download_button_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide() # Hidden until a download starts

        layout.addWidget(title_label)
        layout.addWidget(self.tile_list_widget)
        layout.addWidget(self.download_button)
        layout.addWidget(self.progress_bar)
        return container


    def _setup_actions(self):
        """Creates the reusable QAction objects for the application."""
        exit_icon_path = os.path.join(self.base_dir, "icons", "control-power.png")
        self.exit_action = QAction(QIcon(exit_icon_path), "&Exit", self)
        self.exit_action.triggered.connect(self.close) 

        grid_icon_path = os.path.join(self.base_dir, "icons", "grid.png")
        self.toggle_grid_action = QAction(self.grid_icon, "Show/Hide &Grid", self)
        self.toggle_grid_action.setCheckable(True)
        self.toggle_grid_action.setChecked(True)
        self.toggle_grid_action.toggled.connect(self.toggle_grid_visibility_requested)

    def _setup_menu(self):
        """Creates the main menu bar."""
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        file_menu.addAction(self.exit_action)
        view_menu = menu.addMenu("&View")
        view_menu.addAction(self.toggle_grid_action)

    def _setup_toolbar(self):
        """Creates the main toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.addAction(self.exit_action)
        toolbar.addSeparator()
        toolbar.addAction(self.toggle_grid_action)

    def _setup_statusbar(self):
        """Creates the status bar and its permanent widgets."""
        self.setStatusBar(QStatusBar(self))
        self.coord_label = QLabel("Lat: N/A, Lon: N/A")
        self.zoom_label = QLabel("Zoom: N/A")
        self.zoom_label.setContentsMargins(10, 0, 5, 0)
        self.statusBar().addPermanentWidget(self.zoom_label)
        self.statusBar().addPermanentWidget(self.coord_label)

    # --- Public Methods for the Controller ---

    def show_status_message(self, message: str, timeout: int = 5000):
        """
        Public method to display a message in the status bar.
        
        Args:
            message (str): The text to display.
            timeout (int): Duration in milliseconds. 0 means it's a permanent message                           
        """
        self.statusBar().showMessage(message, timeout)

    def set_map_url(self, url: QUrl):
        """Public method for the controller to set the map's URL."""
        self.map_view.setUrl(url)

    def set_web_channel(self, channel: QWebChannel):
        """
        Public method for the controller to provide the web communication channel.
        The View is responsible for setting it on its internal web page.
        """
        self.map_view.page().setWebChannel(channel)    

    def closeEvent(self, event):
        """
        Overrides the default close event to emit a signal.
        This lets the controller know it's time to clean up.
        """
        self.window_closed.emit()
        event.accept()

    def is_map_ready(self) -> bool:
        """
        Public method for the controller to check if the map page is loaded
        and ready to accept JavaScript commands.
        """
        return not self.map_view.page().url().isEmpty()    
    
    def run_javascript(self, js_code: str):
        """Public method to execute a string of JavaScript code in the web view."""
        self.map_view.page().runJavaScript(js_code)

    def update_coord_display(self, coords_text: str, zoom_level: int):
        """Public method to update the coordinate and zoom labels in the status bar."""
        self.coord_label.setText(coords_text)
        self.zoom_label.setText(f"Zoom: {zoom_level}")    

    def update_tile_list(self, tile_name_list: list):
        """Clears and repopulates the sidebar list with new tile names."""
        self.tile_list_widget.clear()
        self.tile_list_widget.addItems(tile_name_list)    

    def update_download_button_state(self, is_enabled: bool):
        """Enables or disables the download button."""
        self.download_button.setEnabled(is_enabled)    

    def on_download_button_clicked(self):
        """
        When the main action button is clicked, this determines whether to
        emit a 'download_requested' or 'stop_download_requested' signal
        based on its current text/state.
        """
        if "Stop" in self.download_button.text():
            self.stop_download_requested.emit()
        else:
            self.download_requested.emit()    

    def set_download_state(self, is_downloading: bool):
        """Configures the UI for either a downloading or an idle state."""
        self.tile_list_widget.setEnabled(not is_downloading)
        if is_downloading:
            self.download_button.setText("Stop Download")
            self.download_button.setIcon(self.stop_icon)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p% - %v / %m Bytes")
            self.progress_bar.show()
        else: # Reverting to idle state
            self.download_button.setText("Download Selected Tiles")
            self.download_button.setIcon(self.download_icon)
            self.progress_bar.hide()
            self.progress_bar.setFormat("%p%")        