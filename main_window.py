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
    QHBoxLayout,
    QListWidget, 
    QPushButton,
    QProgressBar, 
    QMessageBox, 
    QMenu
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

class MainWindow(QMainWindow):
    """
    The main application window (the "View").
    """
    window_closed = Signal()
    toggle_grid_visibility_requested = Signal(bool)
    clear_selection_requested = Signal()
    download_requested = Signal()
    stop_download_requested = Signal()
    about_requested = Signal()

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

        self.setWindowTitle("Copernicus DEM Downloader")

        # Load icons
        self.download_icon = QIcon(os.path.join(self.base_dir, "icons", "download-cloud.png"))
        self.stop_icon = QIcon(os.path.join(self.base_dir, "icons", "cross-circle.png"))
        self.grid_icon = QIcon(os.path.join(self.base_dir, "icons", "grid.png"))
        self.broom_icon = QIcon(os.path.join(self.base_dir, "icons", "broom.png"))
        self.control_power_icon = QIcon(os.path.join(self.base_dir, "icons", "control-power.png"))
        self.about_icon = QIcon(os.path.join(self.base_dir, "icons", "information.png"))

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
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Selected Tiles")
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)

        self.tile_count_label = QLabel("(0)")
        count_font = self.tile_count_label.font()
        count_font.setPointSize(12)
        self.tile_count_label.setFont(count_font)

        title_layout.addWidget(title_label)
        title_layout.addWidget(self.tile_count_label)
        title_layout.addStretch() 
        
        self.tile_list_widget = QListWidget()
        self.tile_list_widget.setToolTip("List of DEM tiles selected on the map.")
        self.tile_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tile_list_widget.customContextMenuRequested.connect(self._setup_context_menu)
        
        self.download_button = QPushButton("Download Selected Tiles")
        self.download_button.setIcon(self.download_icon)
        self.download_button.setEnabled(False) # Initially disabled
        self.download_button.clicked.connect(self.on_download_button_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide() # Hidden until a download starts

        layout.addLayout(title_layout)
        layout.addWidget(self.tile_list_widget)
        layout.addWidget(self.download_button)
        layout.addWidget(self.progress_bar)
        return container


    def _setup_actions(self):
        """Creates the reusable QAction objects for the application."""
        #Exit
        self.exit_action = QAction(QIcon(self.control_power_icon), "&Exit", self)
        self.exit_action.triggered.connect(self.close) 

        # Toggle Grid
        self.toggle_grid_action = QAction(self.grid_icon, "Show/Hide &Grid", self)
        self.toggle_grid_action.setCheckable(True)
        self.toggle_grid_action.setChecked(True)
        self.toggle_grid_action.toggled.connect(self.toggle_grid_visibility_requested)

        # Clear Selection
        self.clear_selection_action = QAction(self.broom_icon, "&Clear Selection", self)
        self.clear_selection_action.setShortcut("Ctrl+D")
        self.clear_selection_action.setToolTip("Clear all selected tiles from the list.")
        self.clear_selection_action.triggered.connect(self.clear_selection_requested)

        # About
        self.about_action = QAction(QIcon(self.about_icon), "&About", self)
        self.about_action.setStatusTip("Show application information")
        self.about_action.triggered.connect(self.about_requested)

    def _setup_menu(self):
        """Creates the main menu bar."""
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        file_menu.addAction(self.exit_action)

        edit_menu = menu.addMenu("&Edit")
        edit_menu.addAction(self.clear_selection_action)

        view_menu = menu.addMenu("&View")
        view_menu.addAction(self.toggle_grid_action)

        help_menu = menu.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _setup_toolbar(self):
        """Creates the main toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.addAction(self.exit_action)
        toolbar.addSeparator()
        toolbar.addAction(self.toggle_grid_action)
        toolbar.addSeparator()
        toolbar.addAction(self.clear_selection_action)

    def _setup_statusbar(self):
        """Creates the status bar and its permanent widgets."""
        self.setStatusBar(QStatusBar(self))
        
        self.hover_tile_label = QLabel("Tile: N/A")
        self.hover_tile_label.setMinimumWidth(350) 
        
        self.coord_label = QLabel("Lat: N/A, Lon: N/A")
        
        self.zoom_label = QLabel("Zoom Level: N/A")
        self.zoom_label.setContentsMargins(10, 0, 5, 0)
        
        self.statusBar().addPermanentWidget(self.coord_label)
        self.statusBar().addPermanentWidget(self.zoom_label)
        self.statusBar().addPermanentWidget(self.hover_tile_label)

    def _setup_context_menu(self, position):
        """Creates and shows a context menu when the user right-clicks the list."""
        context_menu = QMenu(self)
        context_menu.addAction(self.clear_selection_action)
        context_menu.exec(self.tile_list_widget.mapToGlobal(position))

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

    def update_coord_display(self, coords_text: str, zoom_level: int, tile_name: str):
        """Public method to update the coordinate and zoom labels in the status bar."""
        self.coord_label.setText(coords_text)
        self.zoom_label.setText(f"Zoom Level: {zoom_level}")    
        self.hover_tile_label.setText(f"Tile: {tile_name}")

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

    def update_tile_count(self, count: int):
        """Updates the text of the tile count label in the sidebar."""
        self.tile_count_label.setText(f"({count})")