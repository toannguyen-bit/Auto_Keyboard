# gui/autotyper_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QMessageBox, QFormLayout, QFrame, QGroupBox, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QThread, Slot, Signal

from core.translations import Translations
from core.workers import AutoTyperWorker, HotkeyListenerWorker, get_pynput_key_display_name
from .constants import DEFAULT_HOTKEY, SETTING_MAIN_HOTKEY

class AutoTyperPageWidget(QWidget):
    request_single_key_listener_signal = Signal(int)
    update_window_title_signal = Signal(str)
    setting_hotkey_status_changed_signal = Signal(bool, int)

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setObjectName("autotyperPageWidget")

        self.is_typing_active = False
        self.current_hotkey = DEFAULT_HOTKEY
        self.current_hotkey_name = get_pynput_key_display_name(DEFAULT_HOTKEY)

        self.autotyper_thread = None; self.autotyper_worker = None
        self.hotkey_listener_thread = None; self.hotkey_listener_worker = None

        self._init_ui()
        self._connect_signals()


    def _init_ui(self):
        content_layout = QVBoxLayout(self); content_layout.setContentsMargins(30, 15, 30, 20); content_layout.setSpacing(15)
        input_frame = QFrame(); input_frame.setObjectName("inputFrame")
        self.form_layout = QFormLayout(input_frame); self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows); self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft); self.form_layout.setHorizontalSpacing(10); self.form_layout.setVerticalSpacing(12)
        self.label_for_text_entry = QLabel(); self.entry_text = QLineEdit(); self.entry_text.setObjectName("textInput"); self.form_layout.addRow(self.label_for_text_entry, self.entry_text)
        self.label_for_interval = QLabel(); self.spin_interval = QSpinBox(); self.spin_interval.setRange(1,600000); self.spin_interval.setValue(1000); self.spin_interval.setObjectName("intervalInput"); self.form_layout.addRow(self.label_for_interval, self.spin_interval)
        self.label_for_repetitions = QLabel(); self.spin_repetitions = QSpinBox(); self.spin_repetitions.setRange(0,1000000); self.spin_repetitions.setValue(0); self.spin_repetitions.setObjectName("repetitionsInput"); self.form_layout.addRow(self.label_for_repetitions, self.spin_repetitions)
        content_layout.addWidget(input_frame)
        self.autotyper_hotkey_group = QGroupBox(); self.autotyper_hotkey_group.setObjectName("hotkeyGroup")
        hotkey_group_layout = QVBoxLayout(self.autotyper_hotkey_group); hotkey_group_layout.setSpacing(8)
        current_hotkey_layout = QHBoxLayout()
        self.lbl_current_hotkey_static = QLabel(); self.lbl_current_hotkey_value = QLabel(self.current_hotkey_name); self.lbl_current_hotkey_value.setObjectName("currentHotkeyDisplay")
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_static); current_hotkey_layout.addWidget(self.lbl_current_hotkey_value); current_hotkey_layout.addStretch()
        hotkey_group_layout.addLayout(current_hotkey_layout)
        self.btn_set_hotkey = QPushButton(); self.btn_set_hotkey.setObjectName("setHotkeyButton"); self.btn_set_hotkey.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        hotkey_group_layout.addWidget(self.btn_set_hotkey, 0, Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(self.autotyper_hotkey_group)
        button_layout_container = QWidget(); button_layout = QHBoxLayout(button_layout_container); button_layout.setContentsMargins(0,8,0,0)
        self.btn_start = QPushButton(); self.btn_start.setObjectName("startButton")
        self.btn_stop = QPushButton(); self.btn_stop.setObjectName("stopButton"); self.btn_stop.setEnabled(False)
        button_layout.addStretch(); button_layout.addWidget(self.btn_start); button_layout.addWidget(self.btn_stop); button_layout.addStretch()
        content_layout.addWidget(button_layout_container)
        self.status_label = QLabel(); self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label); content_layout.addStretch()

    def _connect_signals(self):
        self.btn_start.clicked.connect(self.toggle_typing_process)
        self.btn_stop.clicked.connect(self.stop_typing_process)
        self.btn_set_hotkey.clicked.connect(self._prompt_for_new_hotkey)

    def retranslate_ui(self):
        if self.parent_window.view_stack.currentWidget() == self: # Chi cap nhat title neu page dang active
            self.update_window_title_signal.emit(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))
        self.label_for_text_entry.setText(Translations.get("label_text_key"))
        self.entry_text.setPlaceholderText(Translations.get("text_input_placeholder"))
        self.label_for_interval.setText(Translations.get("label_interval"))
        self.spin_interval.setSuffix(Translations.get("interval_suffix"))
        self.label_for_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_repetitions.setSpecialValueText(Translations.get("repetitions_infinite"))
        self.autotyper_hotkey_group.setTitle(Translations.get("label_hotkey_setting_group"))
        self.lbl_current_hotkey_static.setText(Translations.get("label_current_hotkey"))
        self.lbl_current_hotkey_value.setText(self.current_hotkey_name)
        is_this_hk_setting = (self.parent_window.is_setting_hotkey_type == SETTING_MAIN_HOTKEY)
        self.btn_set_hotkey.setText(Translations.get("button_setting_hotkey_wait") if is_this_hk_setting else Translations.get("button_set_hotkey"))
        if self.is_typing_active: self.btn_start.setText(Translations.get("button_start_loading"))
        else:
            self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name))
            # Logic cap nhat status_label
            current_status = self.status_label.text()
            ready_en = Translations.get("status_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_en = Translations.get("status_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_fully_en = Translations.get("status_stopped_fully", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            is_idle = any(p in current_status for p in [ready_en, stopped_en, stopped_fully_en])
            if current_status == Translations.get("status_requesting_stop"): pass
            elif self.autotyper_worker is None and self.autotyper_thread is None and not self.is_typing_active:
                 self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))
            elif not self.is_typing_active and (is_idle or not current_status):
                self.status_label.setText(Translations.get("status_ready", hotkey_name=self.current_hotkey_name))
        self.btn_stop.setText(Translations.get("button_stop"))

    def init_hotkey_listener(self):
        self.parent_window._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker', self)
        if not self.current_hotkey: return
        self.hotkey_listener_thread = QThread(self.parent_window)
        self.hotkey_listener_worker = HotkeyListenerWorker(self.current_hotkey)
        self.hotkey_listener_worker.moveToThread(self.hotkey_listener_thread)
        self.hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_typing_process)
        self.hotkey_listener_thread.started.connect(self.hotkey_listener_worker.run)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_worker.deleteLater)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_thread.deleteLater)
        self.hotkey_listener_thread.start()

    def _can_proceed_action(self):
        if self.parent_window.is_setting_hotkey_type != 0:
            # Huy thao tac set hotkey neu co
            if self.parent_window.single_key_listener_worker:
                self.parent_window.single_key_listener_worker.cancel_current_listening_operation()
            return False 
        if hasattr(self.parent_window, 'recorder_page') and \
           (self.parent_window.recorder_page.is_recording or self.parent_window.recorder_page.is_playing_recording):
            return False 
        return True

    @Slot()
    def toggle_typing_process(self):
        if not self._can_proceed_action(): return
        if self.is_typing_active: self.stop_typing_process()
        else: self.start_typing_process()

    def start_typing_process(self):
        if self.is_typing_active: return 
        text, interval, repetitions = self.entry_text.text(), self.spin_interval.value(), self.spin_repetitions.value()
        if not text: QMessageBox.warning(self.parent_window, Translations.get("msgbox_missing_info_title"), Translations.get("worker_empty_text_error")); return
        self.parent_window._cleanup_thread_worker('autotyper_thread', 'autotyper_worker', self)
        self.is_typing_active = True; self._update_controls_state()
        self.status_label.setText(Translations.get("status_preparing", hotkey_name=self.current_hotkey_name)); QApplication.processEvents()
        self.autotyper_thread = QThread(self.parent_window)
        self.autotyper_worker = AutoTyperWorker(text, interval, repetitions, self.current_hotkey_name)
        self.autotyper_worker.moveToThread(self.autotyper_thread)
        self.autotyper_worker.update_status_signal.connect(self.update_status_label)
        self.autotyper_worker.error_signal.connect(self.show_error_message_box)
        self.autotyper_worker.typing_finished_signal.connect(self._handle_autotyper_worker_finished)
        self.autotyper_thread.started.connect(self.autotyper_worker.run)
        self.autotyper_thread.finished.connect(self.autotyper_worker.deleteLater)
        self.autotyper_thread.finished.connect(self._handle_autotyper_thread_finished)
        self.autotyper_thread.start()

    @Slot()
    def stop_typing_process(self):
        if not self.is_typing_active: self._update_controls_state(); return
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        self.btn_stop.setEnabled(False); self.status_label.setText(Translations.get("status_requesting_stop"))

    def _update_controls_state(self):
        is_idle = not self.is_typing_active and self.parent_window.is_setting_hotkey_type == 0
        self.btn_start.setEnabled(is_idle)
        self.btn_start.setText(Translations.get("button_start_loading") if self.is_typing_active else Translations.get("button_start", hotkey_name=self.current_hotkey_name))
        self.btn_stop.setEnabled(self.is_typing_active)
        is_this_hk_setting = (self.parent_window.is_setting_hotkey_type == SETTING_MAIN_HOTKEY)
        self.btn_set_hotkey.setEnabled(is_idle or is_this_hk_setting)
        self.entry_text.setEnabled(is_idle); self.spin_interval.setEnabled(is_idle); self.spin_repetitions.setEnabled(is_idle)

    @Slot(str)
    def update_status_label(self, message): self.status_label.setText(message)

    @Slot(str)
    def show_error_message_box(self, message):
        QMessageBox.critical(self.parent_window, Translations.get("msgbox_autotyper_error_title"), message)
        self._reset_typing_state_and_ui(error_occurred=True)

    def _reset_typing_state_and_ui(self, error_occurred=False):
        if not self.is_typing_active and self.autotyper_worker is None and self.autotyper_thread is None:
             if error_occurred and " (Lỗi)" not in self.status_label.text():
                self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)")
             return
        was_typing = self.is_typing_active; self.is_typing_active = False; self._update_controls_state()
        if error_occurred: self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)")
        else:
            error_suffix = " (Lỗi)"; req_stop = Translations.get("status_requesting_stop"); cur_text = self.status_label.text()
            if was_typing and not cur_text.endswith(error_suffix) and cur_text != req_stop:
                 self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name))
        if self.autotyper_thread and self.autotyper_thread.isRunning(): self.autotyper_thread.quit()

    @Slot()
    def _handle_autotyper_worker_finished(self): self._reset_typing_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_autotyper_thread_finished(self):
        self.autotyper_worker = None
        if self.autotyper_thread: self.autotyper_thread.deleteLater(); self.autotyper_thread = None
        cur_text = self.status_label.text(); error_suffix = " (Lỗi)"
        if not self.is_typing_active and not cur_text.endswith(error_suffix) and Translations.get("status_requesting_stop") not in cur_text:
             self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))

    @Slot()
    def _prompt_for_new_hotkey(self):
        if not self._can_proceed_action() and self.parent_window.is_setting_hotkey_type != SETTING_MAIN_HOTKEY : return 
        if self.parent_window.is_setting_hotkey_type == SETTING_MAIN_HOTKEY: 
            if self.parent_window.single_key_listener_worker: self.parent_window.single_key_listener_worker.cancel_current_listening_operation()
            return
        elif self.parent_window.is_setting_hotkey_type != 0: 
             QMessageBox.warning(self.parent_window, Translations.get("msgbox_error_set_hotkey_title"), "Đang trong quá trình cài đặt một hotkey khác. Vui lòng hoàn tất hoặc hủy thao tác đó trước.")
             return
        self.parent_window.is_setting_hotkey_type = SETTING_MAIN_HOTKEY 
        self.setting_hotkey_status_changed_signal.emit(True, SETTING_MAIN_HOTKEY)
        self.retranslate_ui(); self._update_controls_state()
        self.request_single_key_listener_signal.emit(SETTING_MAIN_HOTKEY)

    @Slot(object, str)
    def on_new_hotkey_captured(self, key_obj, key_name): 
        self.current_hotkey = key_obj; self.current_hotkey_name = key_name
        self.lbl_current_hotkey_value.setText(key_name)
        self.init_hotkey_listener() 


    @Slot(int) # hotkey_type
    def on_set_hotkey_finished_or_cancelled(self, hotkey_type):
        if hotkey_type == SETTING_MAIN_HOTKEY:
            self.retranslate_ui(); self._update_controls_state()
            self.setting_hotkey_status_changed_signal.emit(False, SETTING_MAIN_HOTKEY)

    def load_settings(self, settings):
        self.entry_text.setText(settings.get("autotyper_text", ""))
        self.spin_interval.setValue(settings.get("autotyper_interval", 1000))
        self.spin_repetitions.setValue(settings.get("autotyper_repetitions", 0))
        hk_data = settings.get("autotyper_hotkey")
        deserialized_hk = self.parent_window._deserialize_key(hk_data)
        if deserialized_hk: self.current_hotkey = deserialized_hk; self.current_hotkey_name = get_pynput_key_display_name(self.current_hotkey)
        else: self.current_hotkey = DEFAULT_HOTKEY; self.current_hotkey_name = get_pynput_key_display_name(DEFAULT_HOTKEY)
        self.init_hotkey_listener()
        self.retranslate_ui(); self._update_controls_state()

    def save_settings(self, settings_dict):
        settings_dict["autotyper_text"] = self.entry_text.text()
        settings_dict["autotyper_interval"] = self.spin_interval.value()
        settings_dict["autotyper_repetitions"] = self.spin_repetitions.value()
        settings_dict["autotyper_hotkey"] = self.parent_window._serialize_key(self.current_hotkey)

    def cleanup_resources(self):
        self.parent_window._cleanup_thread_worker('autotyper_thread', 'autotyper_worker', self)
        self.parent_window._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker', self)