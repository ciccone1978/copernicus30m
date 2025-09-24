import sys
import os
from PySide6.QtWidgets import QApplication

from app_controller import AppController

if __name__ == "__main__":

    app = QApplication(sys.argv)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    controller = AppController(base_dir)
    controller.show()
    
    sys.exit(app.exec())