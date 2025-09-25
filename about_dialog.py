from PySide6.QtWidgets import QDialog
from ui.ui_about_dialog import Ui_Dialog

class AboutDialog(QDialog):
    """
    The logic class for the "About" dialog.
    It loads the UI designed in Qt Designer and connects its signals.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)