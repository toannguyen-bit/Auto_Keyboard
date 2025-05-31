# gui/countdown_overlay.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QScreen


class CountdownOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint # Cho Linux
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating) # Khong lay focus khi hien

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.label = QLabel("...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.75);
                color: white;
                font-size: 26px;
                font-weight: bold;
                padding: 18px 28px;
                border-radius: 12px;
            }
        """)
        layout.addWidget(self.label)
        self.setFixedSize(self.label.sizeHint() + QSize(10,10)) # Them padding nho

    def setText(self, text):
        self.label.setText(text)
        self.adjustSize() # Tinh lai kich thuoc

        # Can giua man hinh
        target_screen = self.screen()
        if not target_screen and QApplication.instance():
            target_screen = QApplication.primaryScreen()
        self.centerOnScreen(target_screen)


    def centerOnScreen(self, target_screen=None):
        current_screen_to_use = target_screen
        if not current_screen_to_use:
            current_screen_to_use = self.screen()
            if not current_screen_to_use and QApplication.instance():
                current_screen_to_use = QApplication.primaryScreen()

        if current_screen_to_use:
            screen_geometry = current_screen_to_use.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 3 # Hoi lech len tren
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)