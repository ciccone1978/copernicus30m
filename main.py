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
        # We create an action with an icon, text, and a shortcut.
        exit_icon_path = os.path.join(self.base_dir, "icons", "control-power.png")
        self.exit_action = QAction(QIcon(exit_icon_path), "&Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("Exit the application")
        # Connect the action's 'triggered' signal to the application's quit slot
        self.exit_action.triggered.connect(QApplication.instance().quit)

    def _setup_menu(self):
        """Create the main menu bar."""
        
        menu = self.menuBar()
        
        # --- File Menu ---
        file_menu = menu.addMenu("&File")
        file_menu.addAction(self.exit_action)

    def _setup_toolbar(self):
        """Create the main toolbar."""
        
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24)) # Set a nice size for the icons
        toolbar.addAction(self.exit_action)

    def _setup_statusbar(self):
        """Create the status bar."""
        
        self.setStatusBar(QStatusBar(self))       
        self.statusBar().showMessage("Welcome to the Copernicus DEM Downloader!", 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())