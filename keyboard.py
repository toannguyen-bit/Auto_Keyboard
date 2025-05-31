import sys
import time
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox, QFormLayout,
    QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot
from PySide6.QtGui import QFont
from pynput.keyboard import Controller as PynputController, Listener as PynputListener, Key as PynputKey
import os # Them os de lay duong dan

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
            if not self.text_to_type:
                self.error_signal.emit("Vui lòng nhập văn bản/phím cần nhấn.")
                return

            if self.interval_s <= 0:
                self.error_signal.emit("Khoảng thời gian phải lớn hơn 0.")
                return

            if self.repetitions < 0:
                self.error_signal.emit("Số lần lặp lại phải là số không âm.")
                return

            count = 0
            initial_delay = 0.75
            start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request:
                    return
                time.sleep(0.05)

            while self._is_running_request:
                if self.repetitions != 0 and count >= self.repetitions:
                    break

                special_keys_map = {
                    "<enter>": PynputKey.enter, "<tab>": PynputKey.tab, "<esc>": PynputKey.esc,
                    "<space>": PynputKey.space, "<up>": PynputKey.up, "<down>": PynputKey.down,
                    "<left>": PynputKey.left, "<right>": PynputKey.right,
                    **{f"<f{i}>": getattr(PynputKey, f"f{i}") for i in range(1, 13)},
                }

                if self.text_to_type.lower() in special_keys_map:
                    key_to_press = special_keys_map[self.text_to_type.lower()]
                    self.keyboard_controller.press(key_to_press)
                    self.keyboard_controller.release(key_to_press)
                else:
                    self.keyboard_controller.type(self.text_to_type)

                count += 1
                rep_text = f"{self.repetitions}" if self.repetitions != 0 else "∞"
                self.update_status_signal.emit(
                    f"Đang chạy... (Lần {count}/{rep_text}). Nhấn {self.hotkey_display_name} để dừng."
                )
                
                sleep_start_time = time.perf_counter()
                while time.perf_counter() - sleep_start_time < self.interval_s:
                    if not self._is_running_request:
                        break
                    time.sleep(0.05) 

                if not self._is_running_request:
                    break
            
        except Exception as e:
            self.error_signal.emit(f"Lỗi trong quá trình chạy: {str(e)}")
        finally:
            self.typing_finished_signal.emit()


    @Slot()
    def request_stop(self):
        self._is_running_request = False

# --- Worker lắng nghe Hotkey (ko đổi) ---
class HotkeyListenerWorker(QObject):
    hotkey_pressed_signal = Signal()

    def __init__(self, hotkey_to_listen):
        super().__init__()
        self.hotkey_to_listen = hotkey_to_listen
        self._pynput_listener = None
        self._keep_listening = True

    @Slot()
    def run(self):
        def on_press(key):
            if not self._keep_listening:
                return False 
            try:
                if key == self.hotkey_to_listen:
                    self.hotkey_pressed_signal.emit()
            except AttributeError:
                pass 
            return self._keep_listening

        self._pynput_listener = PynputListener(on_press=on_press)
        self._pynput_listener.start() 
        self._pynput_listener.join()  

    @Slot()
    def request_stop(self):
        self._keep_listening = False
        if self._pynput_listener:
            PynputListener.stop(self._pynput_listener)

# --- Cửa sổ chính của ứng dụng ---
class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    DEFAULT_HOTKEY_NAME = "F9"

    def __init__(self):
        super().__init__()
        # Lay duong dan den thu muc chua script
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.background_image_path = os.path.join(self.base_path, "stellar.jpg").replace("\\", "/") # Ten file bg

        self.setWindowTitle(f"AutoTyper Poetic - Hotkey: {self.DEFAULT_HOTKEY_NAME}")
        self.setMinimumSize(520, 400) # Tang k.thuoc chut cho bg

        self.is_typing_active = False
        self.current_hotkey = self.DEFAULT_HOTKEY
        self.current_hotkey_name = self.DEFAULT_HOTKEY_NAME

        self.autotyper_thread = None
        self.autotyper_worker = None
        self.hotkey_listener_thread = None
        self.hotkey_listener_worker = None

        self.init_ui()
        self.apply_styles()
        self.init_hotkey_listener()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setObjectName("mainWidget") # Quan trong cho QSS bg

        app_layout = QVBoxLayout(main_widget)
        app_layout.setContentsMargins(25, 25, 25, 25) # Tang padding
        app_layout.setSpacing(18)

        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        form_layout = QFormLayout(input_frame)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(15)

        self.entry_text = QLineEdit()
        self.entry_text.setPlaceholderText("Nhập văn bản hoặc <key_name>...")
        self.entry_text.setObjectName("textInput")
        form_layout.addRow(QLabel("Văn bản/Phím:"), self.entry_text)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(50, 600000)
        self.spin_interval.setValue(1000)
        self.spin_interval.setSuffix(" ms")
        self.spin_interval.setObjectName("intervalInput")
        form_layout.addRow(QLabel("Khoảng thời gian:"), self.spin_interval)

        self.spin_repetitions = QSpinBox()
        self.spin_repetitions.setRange(0, 1000000)
        self.spin_repetitions.setValue(0)
        self.spin_repetitions.setSpecialValueText("Vô hạn (0)")
        self.spin_repetitions.setObjectName("repetitionsInput")
        form_layout.addRow(QLabel("Số lần lặp:"), self.spin_repetitions)
        
        app_layout.addWidget(input_frame)

        button_layout_container = QWidget()
        button_layout = QHBoxLayout(button_layout_container)
        button_layout.setContentsMargins(0,0,0,0)

        self.btn_start = QPushButton(f"Start ({self.current_hotkey_name})")
        self.btn_start.setObjectName("startButton")
        self.btn_start.clicked.connect(self.toggle_typing_process)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_typing_process)

        button_layout.addStretch()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_stop)
        button_layout.addStretch()
        app_layout.addWidget(button_layout_container)

        self.status_label = QLabel(f"Sẵn sàng. Nhấn '{self.current_hotkey_name}' để bắt đầu.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_layout.addWidget(self.status_label)

    def apply_styles(self):
        font_family = "Segoe UI, Arial, sans-serif"
        
        # --- MAU SAC ---
        # Nen chinh app (tuong tu --background-color)
        app_bg_color = "rgb(12, 14, 26)"
        # Nen widget chinh (co the la mainWidget hoac QMainWindow neu muon full bg)
        main_widget_bg_color = f"url({self.background_image_path})" # Them background image
        # Nen cho input frame (tuong tu --card-background-rgb voi alpha)
        input_frame_bg_color = "rgba(30, 30, 46, 0.85)" # Tang alpha de ro hon tren bg
        input_frame_border_color = "rgba(216, 191, 216, 0.25)" # --highlight-color-poetic
        # Chu chinh
        text_color = "rgb(230, 230, 230)" # --text-color-poetic
        # Chu phu, placeholder
        subtext_color = "rgb(192, 192, 192)" # --subtext-color-poetic
        # Input field
        input_bg_color = "rgba(25, 25, 38, 0.9)" # Dam hon chut, gan giong app_bg_color
        input_border_color = "rgba(216, 191, 216, 0.4)"
        input_focus_border_color = "rgb(216, 191, 216)"
        input_focus_bg_color = "rgba(30, 30, 46, 0.95)"
        # Buttons
        button_text_color = text_color
        button_bg_color = "rgba(45, 48, 68, 0.8)" # Mau toi hon card-bg
        button_border_color = "rgba(216, 191, 216, 0.65)"
        
        start_button_bg_color = "rgba(255, 170, 170, 0.3)" # --primary-color
        start_button_border_color = "rgba(255, 170, 170, 0.85)"
        start_button_hover_bg = "rgba(255, 170, 170, 0.45)"
        start_button_pressed_bg = "rgba(255, 170, 170, 0.2)"

        stop_button_hover_bg = "rgba(216, 191, 216, 0.45)" # --highlight-color-poetic
        stop_button_pressed_bg = "rgba(216, 191, 216, 0.25)"
        
        disabled_bg_color = "rgba(60, 63, 80, 0.6)"
        disabled_text_color = "rgba(192, 192, 192, 0.75)"
        disabled_border_color = "rgba(216, 191, 216, 0.25)"
        
        # Status label
        status_bg_color = "rgba(30, 30, 46, 0.75)"
        status_border_color = "rgba(69, 71, 90, 0.6)" # --border-color
        
        # MessageBox
        msgbox_bg_color = "rgb(22, 24, 40)" # Dam hon chut so voi input_frame_bg
        msgbox_text_color = "rgb(220, 220, 220)"
        msgbox_button_bg = start_button_bg_color
        msgbox_button_border = start_button_border_color
        msgbox_button_hover_bg = start_button_hover_bg

        qss = f"""
            QMainWindow {{
                background-color: {app_bg_color};
            }}
            QWidget#mainWidget {{
                background-image: {main_widget_bg_color};
                background-repeat: no-repeat;
                background-position: center;
                background-attachment: fixed; /* Quan trọng để bg ko cuộn theo nội dung */
                border-radius: 0px; /* Bỏ bo góc cửa sổ chính nếu dùng full bg */
            }}
            QFrame#inputFrame {{
                background-color: {input_frame_bg_color};
                border-radius: 12px;
                padding: 18px; /* Tang padding */
                border: 1px solid {input_frame_border_color};
                /* Them box-shadow mo phong */
                /* Qt ko ho tro box-shadow truc tiep nhu CSS web, day la cach gian tiep */
                /* Se lam vien day hon. Can nhắc bỏ nếu không đẹp. */
                /* border-top: 1px solid rgba(255,255,255,0.05); */
                /* border-left: 1px solid rgba(255,255,255,0.05); */
            }}
            QLabel {{
                color: {text_color};
                font-family: "{font_family}";
                font-size: 10pt;
                padding: 3px;
                background-color: transparent; /* De label trong suot tren inputFrame */
            }}
            QLineEdit, QSpinBox {{
                background-color: {input_bg_color};
                color: {text_color};
                border: 1.5px solid {input_border_color}; /* Vien day hon */
                border-radius: 8px;
                padding: 9px 12px; /* Tang padding */
                font-family: "{font_family}";
                font-size: 10pt;
                min-height: 24px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1.5px solid {input_focus_border_color};
                background-color: {input_focus_bg_color};
            }}
            QLineEdit::placeholder {{
                color: {subtext_color};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: right;
                width: 20px; /* Tang rong */
                border: 1.5px solid {input_border_color};
                border-radius: 5px; /* Bo tron hon */
                background-color: {button_bg_color};
                margin: 2px 3px 2px 2px; 
            }}
            QSpinBox::up-button {{ top: 2px; height: 12px;}} 
            QSpinBox::down-button {{ bottom: 2px; height: 12px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: rgba(80, 83, 100, 0.9);
            }}
            QPushButton {{
                color: {button_text_color};
                background-color: {button_bg_color};
                border: 1.5px solid {button_border_color};
                padding: 11px 22px; /* Tang padding */
                border-radius: 10px;
                font-family: "{font_family}";
                font-size: 10pt;
                font-weight: bold;
                min-width: 130px; /* Tang min-width */
            }}
            QPushButton#startButton {{
                background-color: {start_button_bg_color};
                border-color: {start_button_border_color};
            }}
            QPushButton#startButton:hover {{
                background-color: {start_button_hover_bg};
                border-color: rgb(255, 170, 170);
            }}
            QPushButton#startButton:pressed {{
                background-color: {start_button_pressed_bg};
            }}
            QPushButton#stopButton:hover {{
                background-color: {stop_button_hover_bg};
                border-color: rgb(216, 191, 216);
            }}
            QPushButton#stopButton:pressed {{
                background-color: {stop_button_pressed_bg};
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg_color};
                color: {disabled_text_color};
                border-color: {disabled_border_color};
            }}
            QLabel#statusLabel {{
                color: {subtext_color};
                background-color: {status_bg_color};
                border: 1px solid {status_border_color};
                border-radius: 8px;
                padding: 12px; /* Tang padding */
                font-size: 9pt;
                margin-top: 12px;
            }}
            QMessageBox {{
                 background-color: {msgbox_bg_color};
                 font-family: "{font_family}";
            }}
            QMessageBox QLabel {{
                color: {msgbox_text_color};
                 font-size: 10pt;
            }}
             QMessageBox QPushButton {{
                background-color: {msgbox_button_bg};
                border-color: {msgbox_button_border};
                color: {button_text_color};
                padding: 8px 18px;
                border-radius: 8px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {msgbox_button_hover_bg};
            }}
        """
        self.setStyleSheet(qss)

    # Cac phuong thuc con lai (init_hotkey_listener, toggle_typing_process, ...) giu nguyen nhu phien ban truoc
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
        if self.is_typing_active:
            self.stop_typing_process()
        else:
            self.start_typing_process()

    def start_typing_process(self):
        if self.is_typing_active:
            return

        text = self.entry_text.text()
        interval = self.spin_interval.value()
        repetitions = self.spin_repetitions.value()

        if not text:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập văn bản hoặc phím cần nhấn.")
            return
        
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            if self.autotyper_worker:
                self.autotyper_worker.request_stop() 
            self.autotyper_thread.quit() 
            if not self.autotyper_thread.wait(300): 
                pass

        self.is_typing_active = True
        self.btn_start.setEnabled(False)
        self.btn_start.setText("...")
        self.btn_stop.setEnabled(True)
        self.status_label.setText(f"Chuẩn bị... (Nhấn '{self.current_hotkey_name}' để dừng)")
        QApplication.processEvents()

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
        if not self.is_typing_active:
            self._update_ui_stopped() 
            return

        if self.autotyper_worker:
            self.autotyper_worker.request_stop()
        else:
            self._reset_typing_state_and_ui()
            return

        self.btn_stop.setEnabled(False)
        self.status_label.setText("Đang yêu cầu dừng...")

    @Slot(str)
    def update_status_label(self, message):
        self.status_label.setText(message)

    @Slot(str)
    def show_error_message_box(self, message):
        QMessageBox.critical(self, "Lỗi AutoTyper", message)

    def _update_ui_stopped(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText(f"Start ({self.current_hotkey_name})")
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"Đã dừng. Nhấn '{self.current_hotkey_name}' để bắt đầu.")

    def _reset_typing_state_and_ui(self):
        self.is_typing_active = False
        self._update_ui_stopped()
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit()

    @Slot()
    def handle_worker_really_finished(self):
        self._reset_typing_state_and_ui()
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit() 

    @Slot()
    def handle_thread_really_finished(self):
        self.autotyper_worker = None 
        self.autotyper_thread = None 
        if self.is_typing_active: 
             self._reset_typing_state_and_ui()
        else: 
            self.status_label.setText(f"Đã dừng (hoàn toàn). Nhấn '{self.current_hotkey_name}' để bắt đầu.")

    def closeEvent(self, event):
        if self.autotyper_worker:
            self.autotyper_worker.request_stop() 
        
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit()
            if not self.autotyper_thread.wait(200):
                pass

        if self.hotkey_listener_worker:
            self.hotkey_listener_worker.request_stop()
        if self.hotkey_listener_thread and self.hotkey_listener_thread.isRunning():
            self.hotkey_listener_thread.quit()
            if not self.hotkey_listener_thread.wait(200):
                pass
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    QApplication.setFont(font)
    
    window = AutoTyperWindow()
    window.show()
    sys.exit(app.exec())