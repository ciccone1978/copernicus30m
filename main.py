import sys
import os

# Make sure to import the necessary Qt modules for signals/slots
from PySide6.QtCore import Qt, QUrl, Slot, QSize
from PySide6.QtGui import QAction, QIcon 
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QSplitter,
    QStatusBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from local_http_server import LocalHttpServer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

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
        self.sidebar_panel = QWidget()
        
        main_splitter.addWidget(self.map_view)
        main_splitter.addWidget(self.sidebar_panel)
        main_splitter.setSizes([900, 300])

        self.setCentralWidget(main_splitter)

        # --- Setup Menu, Toolbar, and Status Bar ---
        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

    @Slot(str, int)
    def load_map_url(self, host, port):
        """
        This method is called ONLY when the http_server emits the server_started signal.
        This guarantees the server is ready before we try to connect.
        """
        print(f"Server is ready. Loading map from http://{host}:{port}/index.html")
        self.map_view.setUrl(QUrl(f"http://{host}:{port}/index.html"))

    def closeEvent(self, event):
        """
        Overrides the window's close event to ensure the server is stopped.
        """
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




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())