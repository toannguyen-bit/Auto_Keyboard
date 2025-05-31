# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Ktr HĐH, chi ap dung cho Windows
IS_WINDOWS = os.name == 'nt'

if IS_WINDOWS:
    import ctypes
    myappid = u'mycompany.autokeyboard.poetic.1_0_0' 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except AttributeError:
        # Co the xay ra neu shell32 ko co ham nay (hiem) hoac chay tren HĐH ko phai Win
        pass 
    except Exception:
        pass


from gui.main_window import AutoTyperWindow # Import tu file moi (da doi ten class ben trong)

if __name__ == "__main__":

            
    app = QApplication(sys.argv)

    current_file_path = os.path.abspath(__file__)
    base_project_path = os.path.dirname(current_file_path)
    

    icon_path_app_level = os.path.join(base_project_path, "assets", "icon.ico")
    if os.path.exists(icon_path_app_level):
        app.setWindowIcon(QIcon(icon_path_app_level))
    
    window = AutoTyperWindow(base_path=base_project_path) 
    window.show()
    
    sys.exit(app.exec())