# gui/countdown_overlay.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QScreen


class CountdownOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

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
        self.setFixedSize(self.label.sizeHint() + QSize(10,10))

        # Anim cho opacity
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutSine) # Easing mem mai


    def setText(self, text):
        self.label.setText(text)
        self.adjustSize()
        self.centerOnScreen()


    def centerOnScreen(self, target_screen=None):
        current_screen_to_use = target_screen
        if not current_screen_to_use:
            current_screen_to_use = self.screen()
            if not current_screen_to_use and QApplication.instance():
                current_screen_to_use = QApplication.primaryScreen()

        if current_screen_to_use:
            screen_geometry = current_screen_to_use.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 3
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)

    def show_animated(self):
        if self.opacity_animation.state() == QAbstractAnimation.State.Running:
            self.opacity_animation.stop()

        self.setWindowOpacity(0.0) # Bat dau tu mo
        self.show() # Phai show truoc khi anim opacity
        
        self.opacity_animation.setDuration(220) # Thoi gian fade in
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

    def hide_animated(self):
        if not self.isVisible():
            return
        if self.opacity_animation.state() == QAbstractAnimation.State.Running:
            self.opacity_animation.stop()

        self.opacity_animation.setDuration(180) # Thoi gian fade out
        self.opacity_animation.setStartValue(self.windowOpacity()) # Tu opacity hien tai
        self.opacity_animation.setEndValue(0.0)
        
        # Dam bao disconnect slot cu truoc khi connect moi
        try: self.opacity_animation.finished.disconnect(self._on_hide_animation_finished)
        except RuntimeError: pass # Neu chua connect
        self.opacity_animation.finished.connect(self._on_hide_animation_finished)
        
        self.opacity_animation.start()

    def _on_hide_animation_finished(self):
        # Quan trong: disconnect de tranh goi lai nhieu lan hoac loi
        try: self.opacity_animation.finished.disconnect(self._on_hide_animation_finished)
        except RuntimeError: pass
        
        self.hide()
        self.setWindowOpacity(1.0) # Reset opacity cho lan show sau