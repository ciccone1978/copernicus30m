import sys
import os
import logging
from PySide6.QtWidgets import QApplication

from logger_config import setup_logging
from app_controller import AppController

if __name__ == "__main__":

    setup_logging(debug=True)
    
    app = QApplication(sys.argv)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    controller = AppController(base_dir)
    controller.show()
    
    sys.exit(app.exec())