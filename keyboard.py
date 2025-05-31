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

# --- Worker gõ phím ---
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
                # self.typing_finished_signal.emit() # Sẽ được emit trong finally
                return

            if self.interval_s <= 0:
                self.error_signal.emit("Khoảng thời gian phải lớn hơn 0.")
                # self.typing_finished_signal.emit()
                return

            if self.repetitions < 0:
                self.error_signal.emit("Số lần lặp lại phải là số không âm.")
                # self.typing_finished_signal.emit()
                return

            count = 0
            initial_delay = 0.75
            start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request:
                    # self.typing_finished_signal.emit()
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
            
            # self.typing_finished_signal.emit() # Sẽ được emit trong finally

        except Exception as e:
            self.error_signal.emit(f"Lỗi trong quá trình chạy: {str(e)}")
            # self.typing_finished_signal.emit()
        finally:
            # Luôn emit finished_signal để đảm bảo thread và worker được dọn dẹp
            self.typing_finished_signal.emit()


    @Slot()
    def request_stop(self):
        self._is_running_request = False

# --- Worker lắng nghe Hotkey ---
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
            # print(f"Hotkey debug: Key pressed: {key}") # DEBUG
            if not self._keep_listening:
                return False 
            try:
                if key == self.hotkey_to_listen:
                    # print(f"Hotkey debug: {self.hotkey_to_listen} detected, emitting signal.") # DEBUG
                    self.hotkey_pressed_signal.emit()
            except AttributeError:
                pass 
            return self._keep_listening

        # print("Hotkey debug: Listener starting...") # DEBUG
        self._pynput_listener = PynputListener(on_press=on_press)
        self._pynput_listener.start() 
        self._pynput_listener.join()
        # print("Hotkey debug: Listener joined/stopped.") # DEBUG


    @Slot()
    def request_stop(self):
        self._keep_listening = False
        if self._pynput_listener:
            PynputListener.stop(self._pynput_listener) # an toàn thread
            # print("Hotkey debug: Listener stop requested.") # DEBUG

# --- Cửa sổ chính của ứng dụng ---
class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    DEFAULT_HOTKEY_NAME = "F9"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AutoTyper Poetic - Hotkey: {self.DEFAULT_HOTKEY_NAME}")
        self.setMinimumSize(480, 360)

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
        # K.trúc UI chính (ko đổi nhiều)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setObjectName("mainWidget")

        app_layout = QVBoxLayout(main_widget)
        app_layout.setContentsMargins(20, 20, 20, 20)
        app_layout.setSpacing(15)

        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        form_layout = QFormLayout(input_frame)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(12)

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
        # Áp dụng QSS (ko đổi)
        font_family = "Segoe UI, Arial, sans-serif"
        qss = f"""
            QMainWindow {{ background-color: rgb(12, 14, 26); }}
            QWidget#mainWidget {{ background-color: rgb(18, 20, 36); border-radius: 15px; }}
            QFrame#inputFrame {{ background-color: rgba(30, 30, 46, 0.7); border-radius: 12px; padding: 15px; border: 1px solid rgba(216, 191, 216, 0.2); }}
            QLabel {{ color: rgb(230, 230, 230); font-family: "{font_family}"; font-size: 10pt; padding: 2px; }}
            QLineEdit, QSpinBox {{ background-color: rgba(40, 42, 58, 0.8); color: rgb(220, 220, 220); border: 1px solid rgba(216, 191, 216, 0.3); border-radius: 8px; padding: 8px 10px; font-family: "{font_family}"; font-size: 10pt; min-height: 22px; }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1.5px solid rgb(216, 191, 216); background-color: rgba(45, 48, 65, 0.9); }}
            QSpinBox::up-button, QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: right; width: 18px; border: 1px solid rgba(216, 191, 216, 0.3); border-radius: 4px; background-color: rgba(60, 63, 80, 0.8); margin: 1px 2px 1px 1px; }}
            QSpinBox::up-button {{ top: 1px; height: 11px;}} 
            QSpinBox::down-button {{ bottom: 1px; height: 11px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: rgba(80, 83, 100, 0.9); }}
            QPushButton {{ color: rgb(230, 230, 230); background-color: rgba(30, 30, 46, 0.8); border: 1.5px solid rgba(216, 191, 216, 0.6); padding: 10px 20px; border-radius: 10px; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; min-width: 120px; }}
            QPushButton#startButton {{ background-color: rgba(255, 170, 170, 0.25); border-color: rgba(255, 170, 170, 0.8); }}
            QPushButton#startButton:hover {{ background-color: rgba(255, 170, 170, 0.4); border-color: rgb(255, 170, 170); }}
            QPushButton#startButton:pressed {{ background-color: rgba(255, 170, 170, 0.2); }}
            QPushButton#stopButton:hover {{ background-color: rgba(216, 191, 216, 0.4); border-color: rgb(216, 191, 216); }}
            QPushButton#stopButton:pressed {{ background-color: rgba(216, 191, 216, 0.2); }}
            QPushButton:disabled {{ background-color: rgba(60, 63, 80, 0.5); color: rgba(192, 192, 192, 0.7); border-color: rgba(216, 191, 216, 0.2); }}
            QLabel#statusLabel {{ color: rgb(192, 192, 192); background-color: rgba(30, 30, 46, 0.6); border: 1px solid rgba(69, 71, 90, 0.5); border-radius: 8px; padding: 10px; font-size: 9pt; margin-top: 10px; }}
            QMessageBox {{ background-color: rgb(22, 24, 40); font-family: "{font_family}"; }}
            QMessageBox QLabel {{ color: rgb(220, 220, 220); font-size: 10pt; }}
            QMessageBox QPushButton {{ background-color: rgba(255, 170, 170, 0.25); border-color: rgba(255, 170, 170, 0.8); color: rgb(230, 230, 230); padding: 8px 18px; border-radius: 8px; min-width: 80px; }}
            QMessageBox QPushButton:hover {{ background-color: rgba(255, 170, 170, 0.4); }}
        """
        self.setStyleSheet(qss)

    def init_hotkey_listener(self):
        self.hotkey_listener_thread = QThread(self)
        self.hotkey_listener_worker = HotkeyListenerWorker(self.current_hotkey)
        self.hotkey_listener_worker.moveToThread(self.hotkey_listener_thread)
        
        self.hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_typing_process)
        self.hotkey_listener_thread.started.connect(self.hotkey_listener_worker.run)
        
        # Dọn dẹp khi thread listener kết thúc (thường là khi app đóng)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_worker.deleteLater)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_thread.deleteLater)
        
        self.hotkey_listener_thread.start()

    @Slot()
    def toggle_typing_process(self):
        # print(f"DEBUG: toggle_typing_process called. is_typing_active: {self.is_typing_active}") # DEBUG
        if self.is_typing_active:
            self.stop_typing_process()
        else:
            self.start_typing_process()

    def start_typing_process(self):
        # print("DEBUG: start_typing_process called") # DEBUG
        if self.is_typing_active:
            return

        text = self.entry_text.text()
        interval = self.spin_interval.value()
        repetitions = self.spin_repetitions.value()

        if not text:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập văn bản hoặc phím cần nhấn.")
            return
        
        # Dọn worker/thread cũ nếu click start nhiều lần
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            # print("DEBUG: Previous autotyper_thread is running, requesting stop and quitting.") # DEBUG
            if self.autotyper_worker:
                self.autotyper_worker.request_stop() # Yêu cầu worker dừng
            self.autotyper_thread.quit() # Yêu cầu thread thoát
            if not self.autotyper_thread.wait(300): # Chờ tối đa 300ms
                # print("DEBUG: Previous autotyper_thread did not quit in time.") # DEBUG
                # Nếu thread không dừng, có thể cần terminate, nhưng nên tránh
                pass
        # Các đối tượng sẽ tự deleteLater khi signal finished được emit

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
        
        # Kết nối signal hoàn thành của worker
        self.autotyper_worker.typing_finished_signal.connect(self.handle_worker_really_finished)
        self.autotyper_worker.typing_finished_signal.connect(self.autotyper_worker.deleteLater) 
        
        self.autotyper_thread.started.connect(self.autotyper_worker.run)
        # Kết nối signal hoàn thành của thread
        self.autotyper_thread.finished.connect(self.handle_thread_really_finished)
        self.autotyper_thread.finished.connect(self.autotyper_thread.deleteLater)
        
        self.autotyper_thread.start()
        # print("DEBUG: New autotyper_thread started.") # DEBUG


    @Slot()
    def stop_typing_process(self):
        # print("DEBUG: stop_typing_process called") # DEBUG
        if not self.is_typing_active:
            self._update_ui_stopped() # Đảm bảo UI đúng nếu có gọi thừa
            return

        if self.autotyper_worker:
            self.autotyper_worker.request_stop()
        else:
            # Nếu không có worker mà is_typing_active = true -> có lỗi -> reset
            # print("DEBUG: No worker but is_typing_active is True. Resetting.") # DEBUG
            self._reset_typing_state_and_ui()
            return

        # Cập nhật UI sơ bộ
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Đang yêu cầu dừng...")
        # Các nút khác và is_typing_active sẽ được cập nhật trong handle_worker_really_finished


    @Slot(str)
    def update_status_label(self, message):
        self.status_label.setText(message)

    @Slot(str)
    def show_error_message_box(self, message):
        QMessageBox.critical(self, "Lỗi AutoTyper", message)
        # worker.typing_finished_signal sẽ được emit từ finally block của worker.run()
        # nên handle_worker_really_finished sẽ được gọi.

    def _update_ui_stopped(self):
        # Hàm tiện ích để cập nhật UI về trạng thái dừng
        self.btn_start.setEnabled(True)
        self.btn_start.setText(f"Start ({self.current_hotkey_name})")
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"Đã dừng. Nhấn '{self.current_hotkey_name}' để bắt đầu.")

    def _reset_typing_state_and_ui(self):
        # Hàm tiện ích để reset cả trạng thái logic và UI
        self.is_typing_active = False
        self._update_ui_stopped()
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit()
            # Thread sẽ tự deleteLater


    @Slot()
    def handle_worker_really_finished(self):
        # Được gọi KHI worker THỰC SỰ xong việc hoặc bị stop bởi request_stop
        # print(f"DEBUG: handle_worker_really_finished called. Current is_typing_active: {self.is_typing_active}") # DEBUG
        
        # Đặt lại trạng thái logic và cập nhật UI
        self._reset_typing_state_and_ui()
        
        # Worker đã emit typing_finished, nó sẽ được deleteLater do kết nối signal.
        # Yêu cầu thread thoát, nó sẽ emit finished và tự deleteLater.
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            # print("DEBUG: Requesting autotyper_thread to quit.") # DEBUG
            self.autotyper_thread.quit() 


    @Slot()
    def handle_thread_really_finished(self):
        # Được gọi KHI QThread của autotyper THỰC SỰ kết thúc.
        # print("DEBUG: handle_thread_really_finished called.") # DEBUG
        
        # Worker (nếu còn) và Thread đã được deleteLater do kết nối signal.
        # Chỉ cần dọn dẹp tham chiếu Python.
        self.autotyper_worker = None 
        self.autotyper_thread = None 

        # Đảm bảo UI cuối cùng là đúng, phòng trường hợp handle_worker_really_finished chưa kịp cập nhật
        # hoặc trạng thái is_typing_active không nhất quán.
        if self.is_typing_active: # Nếu vì lý do nào đó, is_typing_active vẫn là True
             # print("DEBUG: is_typing_active was still True in handle_thread_really_finished. Resetting.") # DEBUG
             self._reset_typing_state_and_ui()
        else: # Nếu is_typing_active đã là False, chỉ cập nhật lại status text cho chắc
            self.status_label.setText(f"Đã dừng (hoàn toàn). Nhấn '{self.current_hotkey_name}' để bắt đầu.")


    def closeEvent(self, event):
        # print("DEBUG: closeEvent called.") #DEBUG
        # Dừng worker trước
        if self.autotyper_worker:
            self.autotyper_worker.request_stop() 
        
        # Sau đó dừng thread của worker
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit()
            if not self.autotyper_thread.wait(200): # Chờ một chút
                # print("DEBUG: Autotyper thread did not quit in time during closeEvent.") # DEBUG
                pass

        # Dừng listener
        if self.hotkey_listener_worker:
            self.hotkey_listener_worker.request_stop()
        if self.hotkey_listener_thread and self.hotkey_listener_thread.isRunning():
            self.hotkey_listener_thread.quit()
            if not self.hotkey_listener_thread.wait(200):
                # print("DEBUG: Hotkey listener thread did not quit in time during closeEvent.") #DEBUG
                pass
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    QApplication.setFont(font)
    
    window = AutoTyperWindow()
    window.show()
    sys.exit(app.exec())