# keyboard.py
import sys
import time
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox, QFormLayout,
    QSizePolicy, QFrame, QStackedLayout
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot, QPoint, QSize, QRect # Them QRect
from PySide6.QtGui import QFont, QPixmap, QIcon, QMouseEvent
from pynput.keyboard import Controller as PynputController, Listener as PynputListener, Key as PynputKey
import os

# --- Worker gõ phím (ko đổi) ---
class AutoTyperWorker(QObject):
    update_status_signal = Signal(str)
    typing_finished_signal = Signal()
    error_signal = Signal(str)
    def __init__(self, text_to_type, interval_ms, repetitions, hotkey_display_name):
        super().__init__()
        self.text_to_type = text_to_type
        self.interval_s = interval_ms / 1000.0
        self.repetitions = repetitions
        self.hotkey_display_name = hotkey_display_name
        self.keyboard_controller = PynputController()
        self._is_running_request = True
    @Slot()
    def run(self):
        try:
            if not self.text_to_type: self.error_signal.emit("Vui lòng nhập văn bản/phím cần nhấn."); return
            if self.interval_s <= 0: self.error_signal.emit("Khoảng thời gian phải lớn hơn 0."); return
            if self.repetitions < 0: self.error_signal.emit("Số lần lặp lại phải là số không âm."); return
            count = 0; initial_delay = 0.75; start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request: return
                time.sleep(0.05)
            while self._is_running_request:
                if self.repetitions != 0 and count >= self.repetitions: break
                special_keys_map = {"<enter>":PynputKey.enter,"<tab>":PynputKey.tab,"<esc>":PynputKey.esc,"<space>":PynputKey.space,"<up>":PynputKey.up,"<down>":PynputKey.down,"<left>":PynputKey.left,"<right>":PynputKey.right,**{f"<f{i}>":getattr(PynputKey,f"f{i}")for i in range(1,13)},}
                if self.text_to_type.lower() in special_keys_map:
                    key_to_press=special_keys_map[self.text_to_type.lower()]; self.keyboard_controller.press(key_to_press); self.keyboard_controller.release(key_to_press)
                else: self.keyboard_controller.type(self.text_to_type)
                count+=1; rep_text=f"{self.repetitions}"if self.repetitions!=0 else"∞"
                self.update_status_signal.emit(f"Đang chạy... (Lần {count}/{rep_text}). Nhấn {self.hotkey_display_name} để dừng.")
                sleep_start_time=time.perf_counter()
                while time.perf_counter()-sleep_start_time < self.interval_s:
                    if not self._is_running_request:break
                    time.sleep(0.05)
                if not self._is_running_request:break
        except Exception as e: self.error_signal.emit(f"Lỗi trong quá trình chạy: {str(e)}")
        finally: self.typing_finished_signal.emit()
    @Slot()
    def request_stop(self): self._is_running_request=False

# --- Worker lắng nghe Hotkey (ko đổi) ---
class HotkeyListenerWorker(QObject):
    hotkey_pressed_signal=Signal()
    def __init__(self,hotkey_to_listen):super().__init__();self.hotkey_to_listen=hotkey_to_listen;self._pynput_listener=None;self._keep_listening=True
    @Slot()
    def run(self):
        def on_press(key):
            if not self._keep_listening:return False
            try:
                if key==self.hotkey_to_listen:self.hotkey_pressed_signal.emit()
            except AttributeError:pass
            return self._keep_listening
        self._pynput_listener=PynputListener(on_press=on_press);self._pynput_listener.start();self._pynput_listener.join()
    @Slot()
    def request_stop(self):self._keep_listening=False;PynputListener.stop(self._pynput_listener)if self._pynput_listener else None


# --- Custom Title Bar (logic di chuyen se chuyen len QMainWindow) ---
class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0); layout.setSpacing(5)
        self.title_label = QLabel("AutoTyper Poetic"); self.title_label.setObjectName("titleBarLabel"); self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label); layout.addStretch()
        self.btn_minimize = QPushButton("–"); self.btn_minimize.setObjectName("minimizeButton"); self.btn_minimize.setFixedSize(30, 30); self.btn_minimize.clicked.connect(self.window().showMinimized)
        layout.addWidget(self.btn_minimize)
        self.btn_maximize_restore = QPushButton("□"); self.btn_maximize_restore.setObjectName("maximizeRestoreButton"); self.btn_maximize_restore.setFixedSize(30, 30); self.btn_maximize_restore.clicked.connect(self._toggle_maximize_restore)
        layout.addWidget(self.btn_maximize_restore)
        self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("closeButton"); self.btn_close.setFixedSize(30, 30); self.btn_close.clicked.connect(self.window().close)
        layout.addWidget(self.btn_close)
    def _toggle_maximize_restore(self):
        if self.window().isMaximized(): self.window().showNormal(); self.btn_maximize_restore.setText("□")
        else: self.window().showMaximized(); self.btn_maximize_restore.setText("▫")
    def setTitle(self, title): self.title_label.setText(title)

# --- Cửa sổ chính ---
class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    DEFAULT_HOTKEY_NAME = "F9"

    RESIZE_MARGIN = 10

    NO_EDGE = 0x0
    TOP_EDGE = 0x1
    BOTTOM_EDGE = 0x2
    LEFT_EDGE = 0x4
    RIGHT_EDGE = 0x8
    TOP_LEFT_CORNER = TOP_EDGE | LEFT_EDGE
    TOP_RIGHT_CORNER = TOP_EDGE | RIGHT_EDGE
    BOTTOM_LEFT_CORNER = BOTTOM_EDGE | LEFT_EDGE
    BOTTOM_RIGHT_CORNER = BOTTOM_EDGE | RIGHT_EDGE

    def __init__(self):
        super().__init__()
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.background_image_filename = "stellar.jpg"
        self.background_image_path = os.path.join(self.base_path, self.background_image_filename).replace("\\", "/")

        self.setWindowTitle("AutoTyper Poetic")
        self.setMinimumSize(580, 450)
        self.resize(800, 600)

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.is_typing_active = False
        self.current_hotkey = self.DEFAULT_HOTKEY
        self.current_hotkey_name = self.DEFAULT_HOTKEY_NAME

        self.autotyper_thread = None
        self.autotyper_worker = None
        self.hotkey_listener_thread = None
        self.hotkey_listener_worker = None
        
        self.original_pixmap = QPixmap(self.background_image_path)

        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._is_resizing = False
        self._resize_edge = self.NO_EDGE
        self._resize_start_mouse_pos = QPoint()
        self._resize_start_window_geometry = QRect()

        self.init_ui()
        self.apply_styles()
        self.init_hotkey_listener()
        
        self.custom_title_bar.setTitle(f"AutoTyper Poetic - Hotkey: {self.DEFAULT_HOTKEY_NAME}")
        self.setMouseTracking(True)

    def init_ui(self):
        self.main_container_widget = QWidget()
        self.main_container_widget.setObjectName("mainContainerWidget")
        self.setCentralWidget(self.main_container_widget)

        overall_layout = QVBoxLayout(self.main_container_widget)
        overall_layout.setContentsMargins(0,0,0,0)
        overall_layout.setSpacing(0)

        self.custom_title_bar = CustomTitleBar(self)
        overall_layout.addWidget(self.custom_title_bar)

        main_area_widget = QWidget()
        main_area_layout = QVBoxLayout(main_area_widget)
        main_area_layout.setContentsMargins(0,0,0,0)
        main_area_layout.setSpacing(0)

        main_area_stacked_layout = QStackedLayout()
        main_area_stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        self.background_label = QLabel()
        self.background_label.setObjectName("backgroundLabel")
        if self.original_pixmap.isNull():
            print(f"Loi: Khong the tai anh nen tu '{self.background_image_path}'")
            self.background_label.setText("Lỗi tải ảnh nền! Kiểm tra console.")
            self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.background_label.setStyleSheet("background-color: rgb(10, 12, 22); color: white;")
        else:
            self._update_background_pixmap()
        
        self.background_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        main_area_stacked_layout.addWidget(self.background_label)

        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(35, 20, 35, 25)
        content_layout.setSpacing(18)

        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        form_layout = QFormLayout(input_frame)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(12); form_layout.setVerticalSpacing(15)

        self.entry_text = QLineEdit(); self.entry_text.setPlaceholderText("Nhập văn bản hoặc <key_name>..."); self.entry_text.setObjectName("textInput")
        form_layout.addRow(QLabel("Văn bản/Phím:"), self.entry_text)
        self.spin_interval = QSpinBox(); self.spin_interval.setRange(50,600000); self.spin_interval.setValue(1000); self.spin_interval.setSuffix(" ms"); self.spin_interval.setObjectName("intervalInput")
        form_layout.addRow(QLabel("Khoảng thời gian:"), self.spin_interval)
        self.spin_repetitions = QSpinBox(); self.spin_repetitions.setRange(0,1000000); self.spin_repetitions.setValue(0); self.spin_repetitions.setSpecialValueText("Vô hạn (0)"); self.spin_repetitions.setObjectName("repetitionsInput")
        form_layout.addRow(QLabel("Số lần lặp:"), self.spin_repetitions)
        content_layout.addWidget(input_frame)

        button_layout_container = QWidget()
        button_layout = QHBoxLayout(button_layout_container); button_layout.setContentsMargins(0,10,0,0)
        self.btn_start = QPushButton(f"Start ({self.current_hotkey_name})"); self.btn_start.setObjectName("startButton"); self.btn_start.clicked.connect(self.toggle_typing_process)
        self.btn_stop = QPushButton("Stop"); self.btn_stop.setObjectName("stopButton"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_typing_process)
        button_layout.addStretch(); button_layout.addWidget(self.btn_start); button_layout.addWidget(self.btn_stop); button_layout.addStretch()
        content_layout.addWidget(button_layout_container)

        self.status_label = QLabel(f"Sẵn sàng. Nhấn '{self.current_hotkey_name}' để bắt đầu."); self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        main_area_stacked_layout.addWidget(content_widget)
        main_area_stacked_layout.setCurrentWidget(content_widget)
        main_area_layout.addLayout(main_area_stacked_layout)

        overall_layout.addWidget(main_area_widget)

    def apply_styles(self):
        font_family = "Segoe UI, Arial, sans-serif"
        
        app_main_container_bg = "rgb(10, 12, 22)" 
        title_bar_bg = "rgba(15, 18, 30, 0.9)" 
        title_bar_text_color = "rgb(224, 218, 230)" 
        title_bar_button_bg = "transparent"
        title_bar_button_hover_bg = "rgba(224, 218, 230, 0.15)"
        title_bar_button_pressed_bg = "rgba(224, 218, 230, 0.08)"
        close_button_hover_bg = "rgba(200, 90, 110, 0.75)"
        close_button_pressed_bg = "rgba(190, 80, 100, 0.6)"
        
        input_frame_bg_color = "rgba(20, 24, 40, 0.88)"
        input_frame_border_color = "rgba(170, 150, 200, 0.4)"
        
        text_color = "rgb(238, 235, 245)"
        subtext_color = "rgb(175, 170, 185)"
        
        input_bg_color = "rgba(12, 15, 28, 0.92)"
        input_border_color = "rgba(170, 150, 200, 0.55)"
        input_focus_border_color = "rgb(210, 190, 250)"
        input_focus_bg_color = "rgba(22, 25, 45, 0.96)"
        
        button_text_color = text_color
        button_bg_color = "rgba(75, 80, 115, 0.92)" # Mau nut Stop
        button_border_color = "rgba(210, 190, 250, 0.7)" # Vien nut Stop
        
        # Dieu chinh mau nut Start
        start_button_bg_color = "rgba(96, 125, 199, 0.65)"  # Comet Tail Blue / Dusty Blue
        start_button_border_color = "rgba(126, 155, 229, 0.85)"
        start_button_hover_bg = "rgba(116, 145, 219, 0.75)"
        start_button_pressed_bg = "rgba(86, 115, 189, 0.6)"
        start_button_hover_border_color_val = "rgb(116, 145, 219)" # Mau vien khi hover nut Start

        stop_button_hover_bg = "rgba(210, 190, 250, 0.6)"
        stop_button_pressed_bg = "rgba(210, 190, 250, 0.4)"
        
        disabled_bg_color = "rgba(60, 63, 90, 0.7)"
        disabled_text_color = "rgba(160, 155, 170, 0.75)"
        disabled_border_color = "rgba(170, 150, 200, 0.3)"
        
        status_bg_color = "rgba(20, 24, 40, 0.85)"
        status_border_color = "rgba(100, 105, 140, 0.7)"
        
        # Nut trong QMessageBox se dung mau cua nut Start moi
        msgbox_bg_color = "rgb(20, 22, 40)"
        msgbox_text_color = "rgb(230, 225, 235)"
        msgbox_button_bg = start_button_bg_color 
        msgbox_button_border = start_button_border_color
        msgbox_button_hover_bg = start_button_hover_bg

        qss = f"""
            QMainWindow {{ background: transparent; }}
            QWidget#mainContainerWidget {{ background-color: {app_main_container_bg}; border-radius: 10px; }}
            QLabel#backgroundLabel {{ border-radius: 10px; }}
            QWidget#contentWidget {{ background-color: transparent; }}
            QWidget#customTitleBar {{ background-color: {title_bar_bg}; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid rgba(224, 218, 230, 0.1); }}
            QLabel#titleBarLabel {{ color: {title_bar_text_color}; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; padding-left: 10px; background-color: transparent; }}
            QPushButton#minimizeButton, QPushButton#maximizeRestoreButton, QPushButton#closeButton {{ background-color: {title_bar_button_bg}; border: none; border-radius: 6px; color: {subtext_color}; font-family: "{font_family}"; font-size: 12pt; font-weight: bold; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0px; }}
            QPushButton#minimizeButton:hover, QPushButton#maximizeRestoreButton:hover {{ background-color: {title_bar_button_hover_bg}; color: {text_color}; }}
            QPushButton#closeButton:hover {{ background-color: {close_button_hover_bg}; color: white; }}
            QPushButton#minimizeButton:pressed, QPushButton#maximizeRestoreButton:pressed {{ background-color: {title_bar_button_pressed_bg}; }}
            QPushButton#closeButton:pressed {{ background-color: {close_button_pressed_bg}; }}
            QFrame#inputFrame {{ background-color: {input_frame_bg_color}; border-radius: 14px; padding: 22px; border: 1.5px solid {input_frame_border_color}; }}
            QLabel {{ color: {text_color}; font-family: "{font_family}"; font-size: 10pt; padding: 3px; background-color: transparent; }}
            QLineEdit, QSpinBox {{ background-color: {input_bg_color}; color: {text_color}; border: 1.5px solid {input_border_color}; border-radius: 9px; padding: 10px 13px; font-family: "{font_family}"; font-size: 10pt; min-height: 26px; }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1.5px solid {input_focus_border_color}; background-color: {input_focus_bg_color}; }}
            QLineEdit::placeholder {{ color: {subtext_color}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: right; width: 20px; border: 1.5px solid {input_border_color}; border-radius: 5px; background-color: {button_bg_color}; margin: 2px 3px 2px 2px; }}
            QSpinBox::up-button {{ top: 2px; height: 12px;}} 
            QSpinBox::down-button {{ bottom: 2px; height: 12px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: rgba(95, 100, 135, 0.95); }}
            QPushButton {{ color: {button_text_color}; background-color: {button_bg_color}; border: 1.5px solid {button_border_color}; padding: 12px 25px; border-radius: 12px; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; min-width: 140px; }}
            QPushButton#startButton {{ background-color: {start_button_bg_color}; border-color: {start_button_border_color}; }}
            QPushButton#startButton:hover {{ background-color: {start_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }}
            QPushButton#startButton:pressed {{ background-color: {start_button_pressed_bg}; }}
            QPushButton#stopButton:hover {{ background-color: {stop_button_hover_bg}; border-color: rgb(210, 190, 250); }} /* Giu nguyen hoac dieu chinh cho phu hop*/
            QPushButton#stopButton:pressed {{ background-color: {stop_button_pressed_bg}; }}
            QPushButton:disabled {{ background-color: {disabled_bg_color}; color: {disabled_text_color}; border-color: {disabled_border_color}; }}
            QLabel#statusLabel {{ color: {subtext_color}; background-color: {status_bg_color}; border: 1px solid {status_border_color}; border-radius: 9px; padding: 13px; font-size: 9pt; margin-top: 15px; }}
            QMessageBox {{ background-color: {msgbox_bg_color}; font-family: "{font_family}"; border-radius: 8px; border: 1px solid {input_frame_border_color}; }}
            QMessageBox QLabel {{ color: {msgbox_text_color}; font-size: 10pt; background-color: transparent;}}
            QMessageBox QPushButton {{ background-color: {msgbox_button_bg}; border-color: {msgbox_button_border}; color: {button_text_color}; padding: 9px 20px; border-radius: 9px; min-width: 85px; }}
            QMessageBox QPushButton:hover {{ background-color: {msgbox_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }} /* Ap dung mau vien hover moi */
        """
        self.setStyleSheet(qss)
    
    def _update_background_pixmap(self):
        if hasattr(self, 'background_label') and not self.original_pixmap.isNull():
            main_area_height = self.main_container_widget.height() - self.custom_title_bar.height()
            main_area_width = self.main_container_widget.width()
            
            if main_area_width <= 0 or main_area_height <= 0: return

            target_size_for_bg = QSize(main_area_width, main_area_height)
            
            scaled_pixmap = self.original_pixmap.scaled(
                target_size_for_bg, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        self._update_background_pixmap()
        super().resizeEvent(event)

    def _get_current_resize_edge(self, local_pos: QPoint) -> int:
        edge = self.NO_EDGE
        rect = self.rect()

        if local_pos.x() < self.RESIZE_MARGIN: edge |= self.LEFT_EDGE
        if local_pos.x() > rect.width() - self.RESIZE_MARGIN: edge |= self.RIGHT_EDGE
        if local_pos.y() < self.RESIZE_MARGIN: edge |= self.TOP_EDGE
        if local_pos.y() > rect.height() - self.RESIZE_MARGIN: edge |= self.BOTTOM_EDGE
        
        return edge

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint()
            global_pos = event.globalPosition().toPoint()

            self._resize_edge = self._get_current_resize_edge(local_pos)
            if self._resize_edge != self.NO_EDGE:
                self._is_resizing = True
                self._is_dragging = False
                self._resize_start_mouse_pos = global_pos
                self._resize_start_window_geometry = self.geometry()
                event.accept()
                return

            if self.custom_title_bar.geometry().contains(local_pos):
                self._is_dragging = True
                self._is_resizing = False
                self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                event.accept()
                return
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            if self._is_resizing:
                current_mouse_pos = event.globalPosition().toPoint()
                delta = current_mouse_pos - self._resize_start_mouse_pos
                
                start_geom = self._resize_start_window_geometry
                new_geom = QRect(start_geom)

                min_w = self.minimumSize().width()
                min_h = self.minimumSize().height()

                if self._resize_edge & self.LEFT_EDGE:
                    new_left = start_geom.left() + delta.x()
                    new_width = start_geom.width() - delta.x()
                    if new_width < min_w:
                        new_width = min_w
                        new_left = start_geom.right() - min_w
                    new_geom.setLeft(new_left)
                    new_geom.setWidth(new_width)

                if self._resize_edge & self.RIGHT_EDGE:
                    new_width = start_geom.width() + delta.x()
                    if new_width < min_w: new_width = min_w
                    new_geom.setWidth(new_width)

                if self._resize_edge & self.TOP_EDGE:
                    new_top = start_geom.top() + delta.y()
                    new_height = start_geom.height() - delta.y()
                    if new_height < min_h:
                        new_height = min_h
                        new_top = start_geom.bottom() - min_h
                    new_geom.setTop(new_top)
                    new_geom.setHeight(new_height)

                if self._resize_edge & self.BOTTOM_EDGE:
                    new_height = start_geom.height() + delta.y()
                    if new_height < min_h: new_height = min_h
                    new_geom.setHeight(new_height)
                
                self.setGeometry(new_geom)
                event.accept()
                return
            elif self._is_dragging:
                self.move(event.globalPosition().toPoint() - self._drag_start_pos)
                event.accept()
                return

        if not (self._is_resizing or self._is_dragging):
            local_pos = event.position().toPoint()
            current_hover_edge = self._get_current_resize_edge(local_pos)
            
            is_on_title_bar_main_part = self.custom_title_bar.geometry().contains(local_pos) and \
                                        current_hover_edge == self.NO_EDGE

            if is_on_title_bar_main_part:
                self.unsetCursor()
            elif current_hover_edge == self.TOP_LEFT_CORNER or current_hover_edge == self.BOTTOM_RIGHT_CORNER:
                self.setCursor(Qt.SizeFDiagCursor)
            elif current_hover_edge == self.TOP_RIGHT_CORNER or current_hover_edge == self.BOTTOM_LEFT_CORNER:
                self.setCursor(Qt.SizeBDiagCursor)
            elif current_hover_edge & self.LEFT_EDGE or current_hover_edge & self.RIGHT_EDGE:
                self.setCursor(Qt.SizeHorCursor)
            elif current_hover_edge & self.TOP_EDGE or current_hover_edge & self.BOTTOM_EDGE:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.unsetCursor()
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            changed_state = False
            if self._is_resizing:
                self._is_resizing = False
                changed_state = True
            if self._is_dragging:
                self._is_dragging = False
                changed_state = True
            
            if changed_state:
                self._resize_edge = self.NO_EDGE
                self.unsetCursor()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def init_hotkey_listener(self):
        self.hotkey_listener_thread = QThread(self)
        self.hotkey_listener_worker = HotkeyListenerWorker(self.current_hotkey)
        self.hotkey_listener_worker.moveToThread(self.hotkey_listener_thread)
        self.hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_typing_process)
        self.hotkey_listener_thread.started.connect(self.hotkey_listener_worker.run)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_worker.deleteLater)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_thread.deleteLater)
        self.hotkey_listener_thread.start()

    @Slot()
    def toggle_typing_process(self):
        if self.is_typing_active: self.stop_typing_process()
        else: self.start_typing_process()

    def start_typing_process(self):
        if self.is_typing_active: return
        text = self.entry_text.text()
        interval = self.spin_interval.value()
        repetitions = self.spin_repetitions.value()
        if not text: QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập văn bản hoặc phím cần nhấn."); return
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            if self.autotyper_worker: self.autotyper_worker.request_stop()
            self.autotyper_thread.quit()
            if not self.autotyper_thread.wait(300): pass
        self.is_typing_active = True
        self.btn_start.setEnabled(False); self.btn_start.setText("...")
        self.btn_stop.setEnabled(True)
        self.status_label.setText(f"Chuẩn bị... (Nhấn '{self.current_hotkey_name}' để dừng)"); QApplication.processEvents()
        self.autotyper_thread = QThread(self)
        self.autotyper_worker = AutoTyperWorker(text, interval, repetitions, self.current_hotkey_name)
        self.autotyper_worker.moveToThread(self.autotyper_thread)
        self.autotyper_worker.update_status_signal.connect(self.update_status_label)
        self.autotyper_worker.error_signal.connect(self.show_error_message_box)
        self.autotyper_worker.typing_finished_signal.connect(self.handle_worker_really_finished)
        self.autotyper_worker.typing_finished_signal.connect(self.autotyper_worker.deleteLater)
        self.autotyper_thread.started.connect(self.autotyper_worker.run)
        self.autotyper_thread.finished.connect(self.handle_thread_really_finished)
        self.autotyper_thread.finished.connect(self.autotyper_thread.deleteLater)
        self.autotyper_thread.start()

    @Slot()
    def stop_typing_process(self):
        if not self.is_typing_active: self._update_ui_stopped(); return
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        else: self._reset_typing_state_and_ui(); return
        self.btn_stop.setEnabled(False); self.status_label.setText("Đang yêu cầu dừng...")

    @Slot(str)
    def update_status_label(self, message): self.status_label.setText(message)
    @Slot(str)
    def show_error_message_box(self, message): QMessageBox.critical(self, "Lỗi AutoTyper", message)

    def _update_ui_stopped(self):
        self.btn_start.setEnabled(True); self.btn_start.setText(f"Start ({self.current_hotkey_name})")
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"Đã dừng. Nhấn '{self.current_hotkey_name}' để bắt đầu.")

    def _reset_typing_state_and_ui(self):
        self.is_typing_active = False; self._update_ui_stopped()
        if self.autotyper_thread and self.autotyper_thread.isRunning(): self.autotyper_thread.quit()

    @Slot()
    def handle_worker_really_finished(self):
        self._reset_typing_state_and_ui()
        if self.autotyper_thread and self.autotyper_thread.isRunning(): self.autotyper_thread.quit()

    @Slot()
    def handle_thread_really_finished(self):
        self.autotyper_worker = None; self.autotyper_thread = None
        if self.is_typing_active: self._reset_typing_state_and_ui()
        else: self.status_label.setText(f"Đã dừng (hoàn toàn). Nhấn '{self.current_hotkey_name}' để bắt đầu.")

    def closeEvent(self, event):
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit(); self.autotyper_thread.wait(200)
        if self.hotkey_listener_worker: self.hotkey_listener_worker.request_stop()
        if self.hotkey_listener_thread and self.hotkey_listener_thread.isRunning():
            self.hotkey_listener_thread.quit(); self.hotkey_listener_thread.wait(200)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    QApplication.setFont(font)
    window = AutoTyperWindow()
    window.show()
    sys.exit(app.exec())