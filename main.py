# main.py
import sys
import os
from PySide6.QtWidgets import QApplication

from gui.main_window import AutoTyperWindow

if __name__ == "__main__":

            
    app = QApplication(sys.argv)

    current_file_path = os.path.abspath(__file__)
    base_project_path = os.path.dirname(current_file_path)
    
    window = AutoTyperWindow(base_path=base_project_path) 
    window.show()
    
    sys.exit(app.exec())