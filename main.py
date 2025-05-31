# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont # QFont se duoc set trong main_window.apply_styles

from gui.main_window import AutoTyperWindow
from core.translations import Translations # Can de set NN ban dau neu muon

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Xac dinh base_path (thu muc goc cua du an)
    # Neu main.py o thu muc goc cua du an:
    current_file_path = os.path.abspath(__file__)
    base_project_path = os.path.dirname(current_file_path)
    
    # Co the load ngon ngu tu file config o day
    # Translations.set_language(Translations.LANG_EN) # Vi du

    window = AutoTyperWindow(base_path=base_project_path) # Truyen base_path vao
    window.show()
    
    sys.exit(app.exec())