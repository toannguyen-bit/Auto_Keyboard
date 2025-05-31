# gui/recorder_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QMessageBox, QFormLayout, QGroupBox, QTableWidget, QHeaderView,
    QTableWidgetItem, QAbstractItemView, QApplication
)
from PySide6.QtCore import Qt, QThread, Slot, Signal

from core.translations import Translations
from core.workers import (
    KeyboardRecorderWorker, RecordedPlayerWorker, HotkeyListenerWorker,
    get_pynput_key_display_name
)
from .constants import (
    DEFAULT_START_RECORD_HOTKEY, DEFAULT_PLAY_RECORD_HOTKEY,
    DEFAULT_RECORD_REPETITIONS, SETTING_START_RECORD_HOTKEY, SETTING_PLAY_RECORD_HOTKEY
)

class RecorderPageWidget(QWidget):
    request_single_key_listener_signal = Signal(int)
    setting_hotkey_status_changed_signal = Signal(bool, int) # is_setting, hotkey_type
    request_countdown_overlay_signal = Signal(bool, str) # show, text

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setObjectName("recorderPageWidget")

        self.is_recording = False; self.is_playing_recording = False
        self.recorded_events = []

        self.current_start_record_hotkey = DEFAULT_START_RECORD_HOTKEY
        self.current_start_record_hotkey_name = get_pynput_key_display_name(DEFAULT_START_RECORD_HOTKEY)
        self.current_play_record_hotkey = DEFAULT_PLAY_RECORD_HOTKEY
        self.current_play_record_hotkey_name = get_pynput_key_display_name(DEFAULT_PLAY_RECORD_HOTKEY)

        self.recorder_thread = None; self.recorder_worker = None
        self.player_thread = None; self.player_worker = None
        self.start_record_hotkey_listener_thread = None; self.start_record_hotkey_listener_worker = None
        self.play_record_hotkey_listener_thread = None; self.play_record_hotkey_listener_worker = None

        self._init_ui()
        self._connect_signals()
        # retranslate_ui va _update_controls_state se duoc goi boi main_window
        # self.init_record_play_hotkey_listeners() # Cung se duoc goi sau khi load settings

    def _init_ui(self):
        content_layout = QVBoxLayout(self); content_layout.setContentsMargins(20, 15, 20, 20); content_layout.setSpacing(12)
        self.record_play_hotkey_group = QGroupBox(); self.record_play_hotkey_group.setObjectName("hotkeyGroup")
        rec_play_hk_layout = QFormLayout(self.record_play_hotkey_group); rec_play_hk_layout.setSpacing(10)
        self.lbl_current_start_record_hotkey_static = QLabel()
        start_rec_hk_val_layout = QHBoxLayout(); self.lbl_current_start_record_hotkey_value = QLabel(self.current_start_record_hotkey_name); self.lbl_current_start_record_hotkey_value.setObjectName("currentHotkeyDisplay")
        self.btn_set_start_record_hotkey = QPushButton(); self.btn_set_start_record_hotkey.setObjectName("setHotkeyButtonSmall")
        start_rec_hk_val_layout.addWidget(self.lbl_current_start_record_hotkey_value); start_rec_hk_val_layout.addWidget(self.btn_set_start_record_hotkey); start_rec_hk_val_layout.addStretch()
        rec_play_hk_layout.addRow(self.lbl_current_start_record_hotkey_static, start_rec_hk_val_layout)
        self.lbl_current_play_record_hotkey_static = QLabel()
        play_rec_hk_val_layout = QHBoxLayout(); self.lbl_current_play_record_hotkey_value = QLabel(self.current_play_record_hotkey_name); self.lbl_current_play_record_hotkey_value.setObjectName("currentHotkeyDisplay")
        self.btn_set_play_record_hotkey = QPushButton(); self.btn_set_play_record_hotkey.setObjectName("setHotkeyButtonSmall")
        play_rec_hk_val_layout.addWidget(self.lbl_current_play_record_hotkey_value); play_rec_hk_val_layout.addWidget(self.btn_set_play_record_hotkey); play_rec_hk_val_layout.addStretch()
        rec_play_hk_layout.addRow(self.lbl_current_play_record_hotkey_static, play_rec_hk_val_layout)
        content_layout.addWidget(self.record_play_hotkey_group)
        self.recorded_events_table = QTableWidget(); self.recorded_events_table.setObjectName("recordedEventsTable"); self.recorded_events_table.setColumnCount(3)
        self.recorded_events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.recorded_events_table.verticalHeader().setVisible(False)
        self.recorded_events_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.recorded_events_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        content_layout.addWidget(self.recorded_events_table, 1)
        playback_options_container = QWidget(); playback_options_layout = QHBoxLayout(playback_options_container); playback_options_layout.setContentsMargins(0, 5, 0, 5)
        self.label_for_record_repetitions = QLabel(); self.spin_record_repetitions = QSpinBox(); self.spin_record_repetitions.setRange(0, 1000000); self.spin_record_repetitions.setValue(DEFAULT_RECORD_REPETITIONS); self.spin_record_repetitions.setObjectName("recordRepetitionsInput")
        playback_options_layout.addStretch(1); playback_options_layout.addWidget(self.label_for_record_repetitions); playback_options_layout.addWidget(self.spin_record_repetitions); playback_options_layout.addStretch(1)
        content_layout.addWidget(playback_options_container)
        recorder_button_layout = QHBoxLayout(); self.btn_start_record = QPushButton(); self.btn_start_record.setObjectName("recordButton"); self.btn_play_record = QPushButton(); self.btn_play_record.setObjectName("playRecordButton"); self.btn_clear_record = QPushButton(); self.btn_clear_record.setObjectName("clearRecordButton")
        recorder_button_layout.addStretch(); recorder_button_layout.addWidget(self.btn_start_record); recorder_button_layout.addWidget(self.btn_play_record); recorder_button_layout.addWidget(self.btn_clear_record); recorder_button_layout.addStretch()
        content_layout.addLayout(recorder_button_layout)
        self.recorder_status_label = QLabel(); self.recorder_status_label.setObjectName("statusLabel"); self.recorder_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.recorder_status_label)

    def _connect_signals(self):
        self.btn_set_start_record_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey(SETTING_START_RECORD_HOTKEY))
        self.btn_set_play_record_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey(SETTING_PLAY_RECORD_HOTKEY))
        self.btn_start_record.clicked.connect(self.toggle_recording_process)
        self.btn_play_record.clicked.connect(self.toggle_playing_process)
        self.btn_clear_record.clicked.connect(self._clear_recorded_events)

    def retranslate_ui(self):
        self.record_play_hotkey_group.setTitle(Translations.get("label_record_play_group"))
        self.lbl_current_start_record_hotkey_static.setText(Translations.get("label_start_record_hotkey"))
        self.lbl_current_start_record_hotkey_value.setText(self.current_start_record_hotkey_name)
        self.lbl_current_play_record_hotkey_static.setText(Translations.get("label_play_record_hotkey"))
        self.lbl_current_play_record_hotkey_value.setText(self.current_play_record_hotkey_name)
        self.label_for_record_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_record_repetitions.setSpecialValueText(Translations.get("repetitions_infinite"))
        self.spin_record_repetitions.setSuffix("") # Khong co suffix
        is_setting_rec_hk = (self.parent_window.is_setting_hotkey_type == SETTING_START_RECORD_HOTKEY)
        self.btn_set_start_record_hotkey.setText(Translations.get("button_setting_hotkey_wait") if is_setting_rec_hk else Translations.get("button_set_start_record_hotkey"))
        is_setting_play_hk = (self.parent_window.is_setting_hotkey_type == SETTING_PLAY_RECORD_HOTKEY)
        self.btn_set_play_record_hotkey.setText(Translations.get("button_setting_hotkey_wait") if is_setting_play_hk else Translations.get("button_set_play_record_hotkey"))
        # Logic cap nhat status va text nut
        cur_status = self.recorder_status_label.text()
        rec_idle_en = Translations.get("status_recorder_idle", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        rec_stop_en = Translations.get("status_recorder_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        play_ready_en = Translations.get("status_player_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        play_stop_en = Translations.get("status_player_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        play_err_en = Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("! ")[0]

        if self.is_recording: self.btn_start_record.setText(Translations.get("button_stop_recording", hotkey_name=self.current_start_record_hotkey_name))
        else:
            self.btn_start_record.setText(Translations.get("button_start_recording", hotkey_name=self.current_start_record_hotkey_name))
            if not self.is_playing_recording and (not cur_status or any(p in cur_status for p in [rec_idle_en, rec_stop_en])) and play_err_en not in cur_status:
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))
        if self.is_playing_recording: self.btn_play_record.setText(Translations.get("button_stop_playing_recording", hotkey_name=self.current_play_record_hotkey_name))
        else:
            self.btn_play_record.setText(Translations.get("button_play_recording", hotkey_name=self.current_play_record_hotkey_name))
            if len(self.recorded_events)>0 and not self.is_recording and (not cur_status or any(p in cur_status for p in [play_ready_en, play_stop_en, play_err_en, rec_idle_en, rec_stop_en])):
                if play_err_en not in cur_status: self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
            elif len(self.recorded_events)==0 and not self.is_recording and (not cur_status or any(p in cur_status for p in [rec_idle_en, rec_stop_en])) and play_err_en not in cur_status:
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))
        self.btn_clear_record.setText(Translations.get("button_clear_recording"))
        self.recorded_events_table.setHorizontalHeaderLabels([Translations.get("table_header_key"), Translations.get("table_header_action"), Translations.get("table_header_delay")])
        if not self.recorder_status_label.text() and not self.is_recording and not self.is_playing_recording: self.recorder_status_label.setText(Translations.get("recorder_status_label_default"))

    def init_record_play_hotkey_listeners(self):
        self._init_single_hk_listener('start_record_hotkey_listener_thread', 'start_record_hotkey_listener_worker', self.current_start_record_hotkey, self.toggle_recording_process)
        self._init_single_hk_listener('play_record_hotkey_listener_thread', 'play_record_hotkey_listener_worker', self.current_play_record_hotkey, self.toggle_playing_process)

    def _init_single_hk_listener(self, thread_attr, worker_attr, hk_obj, slot_fn):
        self.parent_window._cleanup_thread_worker(thread_attr, worker_attr, self)
        if not hk_obj: return
        thread = QThread(self.parent_window); worker = HotkeyListenerWorker(hk_obj)
        worker.moveToThread(thread); worker.hotkey_pressed_signal.connect(slot_fn)
        thread.started.connect(worker.run); thread.finished.connect(worker.deleteLater); thread.finished.connect(thread.deleteLater)
        thread.start(); setattr(self, thread_attr, thread); setattr(self, worker_attr, worker)

    def _can_proceed_action(self):
        if self.parent_window.is_setting_hotkey_type != 0:
            if self.parent_window.single_key_listener_worker: self.parent_window.single_key_listener_worker.cancel_current_listening_operation()
            return False
        if hasattr(self.parent_window, 'autotyper_page') and self.parent_window.autotyper_page.is_typing_active: return False
        return True

    @Slot()
    def toggle_recording_process(self):
        if not self._can_proceed_action(): return
        if self.is_playing_recording: return # Ko cho ghi khi dang phat
        if self.is_recording: self._stop_recording()
        else: self._start_recording()

    def _start_recording(self):
        if self.is_recording: return
        self.is_recording = True; self.recorded_events.clear(); self._update_recorded_events_table(); self._update_controls_state()
        self.parent_window._cleanup_thread_worker('recorder_thread', 'recorder_worker', self)
        self.recorder_thread = QThread(self.parent_window)
        self.recorder_worker = KeyboardRecorderWorker(self.current_start_record_hotkey, self.current_start_record_hotkey_name)
        self.recorder_worker.moveToThread(self.recorder_thread)
        self.recorder_worker.key_event_recorded.connect(self._add_recorded_event)
        self.recorder_worker.recording_status_update.connect(self._update_recorder_status_label)
        self.recorder_worker.recording_finished.connect(self._handle_recorder_worker_finished)
        self.recorder_thread.started.connect(self.recorder_worker.run)
        self.recorder_thread.finished.connect(self.recorder_worker.deleteLater); self.recorder_thread.finished.connect(self._handle_recorder_thread_finished)
        self.recorder_thread.start()

    def _stop_recording(self):
        if not self.is_recording or not self.recorder_worker: return
        self.recorder_worker.request_stop()

    @Slot(object, str, str, float)
    def _add_recorded_event(self, key_obj, key_name_display, action_canonical, delay_ms):
        self.recorded_events.append((key_obj, key_name_display, action_canonical, delay_ms)); self._update_recorded_events_table()

    @Slot(str)
    def _update_recorder_status_label(self, status):
        self.recorder_status_label.setText(status)
        countdown_prefix = Translations.get("status_recorder_countdown", seconds="").split("...")[0]
        is_countdown = status.startswith(countdown_prefix.strip()) and "..." in status
        if is_countdown: self.request_countdown_overlay_signal.emit(True, status.replace(countdown_prefix.strip(), "").strip())
        else: self.request_countdown_overlay_signal.emit(False, "")

    def _reset_recorder_state_and_ui(self):
        if not self.is_recording and self.recorder_worker is None and self.recorder_thread is None: return
        was_recording = self.is_recording; self.is_recording = False; self._update_controls_state()
        if was_recording: self.recorder_status_label.setText(Translations.get("status_recorder_stopped", hotkey_name=self.current_start_record_hotkey_name))
        if self.recorder_thread and self.recorder_thread.isRunning(): self.recorder_thread.quit()
        self.request_countdown_overlay_signal.emit(False, "")

    @Slot()
    def _handle_recorder_worker_finished(self): self._reset_recorder_state_and_ui()

    @Slot()
    def _handle_recorder_thread_finished(self):
        self.recorder_worker = None
        if self.recorder_thread: self.recorder_thread.deleteLater(); self.recorder_thread = None
        if not self.is_recording and not self.is_playing_recording:
            if len(self.recorded_events)>0: self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
            else: self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))
        self.request_countdown_overlay_signal.emit(False, "")

    @Slot()
    def toggle_playing_process(self):
        if not self._can_proceed_action(): return
        if self.is_recording: return # Ko cho phat khi dang ghi
        if self.is_playing_recording: self._stop_playing_recording()
        else: self._start_playing_recording()

    def _start_playing_recording(self):
        if self.is_playing_recording or not self.recorded_events:
            if not self.recorded_events: QMessageBox.information(self.parent_window, Translations.get("msgbox_no_recording_title"), Translations.get("msgbox_no_recording_text"))
            return
        reps = self.spin_record_repetitions.value(); self.is_playing_recording = True; self._update_controls_state()
        self.parent_window._cleanup_thread_worker('player_thread', 'player_worker', self)
        self.player_thread = QThread(self.parent_window)
        events = [(evt[0], evt[2], evt[3]) for evt in self.recorded_events]
        self.player_worker = RecordedPlayerWorker(events, reps, self.current_play_record_hotkey_name)
        self.player_worker.moveToThread(self.player_thread)
        self.player_worker.update_status_signal.connect(self._update_recorder_status_label)
        self.player_worker.error_signal.connect(self._handle_player_error)
        self.player_worker.playing_finished_signal.connect(self._handle_player_worker_finished)
        self.player_thread.started.connect(self.player_worker.run)
        self.player_thread.finished.connect(self.player_worker.deleteLater); self.player_thread.finished.connect(self._handle_player_thread_finished)
        self.player_thread.start()

    def _stop_playing_recording(self):
        if not self.is_playing_recording or not self.player_worker: return
        self.player_worker.request_stop()

    def _reset_player_state_and_ui(self, error_occurred=False):
        if not self.is_playing_recording and self.player_worker is None and self.player_thread is None:
            if error_occurred and Translations.get("status_player_error",hotkey_name="_",lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                 self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
            return
        was_playing = self.is_playing_recording; self.is_playing_recording = False; self._update_controls_state()
        if error_occurred: self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
        else:
            if was_playing and Translations.get("status_player_error",hotkey_name="_",lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                self.recorder_status_label.setText(Translations.get("status_player_stopped", hotkey_name=self.current_play_record_hotkey_name))
        if self.player_thread and self.player_thread.isRunning(): self.player_thread.quit()

    @Slot(str)
    def _handle_player_error(self, error_message):
        QMessageBox.critical(self.parent_window, Translations.get("msgbox_autotyper_error_title"), error_message)
        self._reset_player_state_and_ui(error_occurred=True)

    @Slot()
    def _handle_player_worker_finished(self): self._reset_player_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_player_thread_finished(self):
        self.player_worker = None
        if self.player_thread: self.player_thread.deleteLater(); self.player_thread = None
        cur_text = self.recorder_status_label.text(); err_prefix = Translations.get("status_player_error",hotkey_name="_",lang=Translations.LANG_EN).split("!")[0]
        if not self.is_playing_recording and not self.is_recording and err_prefix not in cur_text:
            if len(self.recorded_events) > 0: self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
            else: self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

    def _update_controls_state(self):
        is_idle_hk = not self.is_recording and not self.is_playing_recording and self.parent_window.is_setting_hotkey_type == 0
        self.btn_start_record.setEnabled(not self.is_playing_recording and self.parent_window.is_setting_hotkey_type == 0)
        self.btn_play_record.setEnabled(not self.is_recording and self.parent_window.is_setting_hotkey_type == 0 and len(self.recorded_events) > 0)
        self.spin_record_repetitions.setEnabled(is_idle_hk)
        self.btn_clear_record.setEnabled(is_idle_hk and len(self.recorded_events) > 0)
        is_setting_rec = (self.parent_window.is_setting_hotkey_type == SETTING_START_RECORD_HOTKEY)
        self.btn_set_start_record_hotkey.setEnabled(is_idle_hk or is_setting_rec)
        is_setting_play = (self.parent_window.is_setting_hotkey_type == SETTING_PLAY_RECORD_HOTKEY)
        self.btn_set_play_record_hotkey.setEnabled(is_idle_hk or is_setting_play)

    def _update_recorded_events_table(self):
        self.recorded_events_table.setRowCount(0)
        for _k_obj, k_name, act, delay in self.recorded_events:
            row = self.recorded_events_table.rowCount(); self.recorded_events_table.insertRow(row)
            self.recorded_events_table.setItem(row, 0, QTableWidgetItem(k_name))
            self.recorded_events_table.setItem(row, 1, QTableWidgetItem(Translations.get(f"action_{act}_display")))
            self.recorded_events_table.setItem(row, 2, QTableWidgetItem(f"{delay:.2f}"))
        self.recorded_events_table.scrollToBottom(); self._update_controls_state()

    @Slot()
    def _clear_recorded_events(self):
        if not self.recorded_events: return
        if QMessageBox.question(self.parent_window, Translations.get("msgbox_confirm_clear_recording_title"), Translations.get("msgbox_confirm_clear_recording_text"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.recorded_events.clear(); self._update_recorded_events_table()
            if not self.is_recording and not self.is_playing_recording: self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

    @Slot(int)
    def _prompt_for_new_hotkey(self, hotkey_type_flag):
        if not self._can_proceed_action() and self.parent_window.is_setting_hotkey_type != hotkey_type_flag: return
        if self.parent_window.is_setting_hotkey_type == hotkey_type_flag: # Huy neu dang set chinh no
            if self.parent_window.single_key_listener_worker: self.parent_window.single_key_listener_worker.cancel_current_listening_operation()
            return
        elif self.parent_window.is_setting_hotkey_type != 0:
             QMessageBox.warning(self.parent_window, Translations.get("msgbox_error_set_hotkey_title"), "Đang trong quá trình cài đặt một hotkey khác. Vui lòng hoàn tất hoặc hủy thao tác đó trước.")
             return
        self.parent_window.is_setting_hotkey_type = hotkey_type_flag
        self.setting_hotkey_status_changed_signal.emit(True, hotkey_type_flag)
        self.retranslate_ui(); self._update_controls_state()
        self.request_single_key_listener_signal.emit(hotkey_type_flag)

    @Slot(int, object, str)
    def on_new_hotkey_captured(self, hotkey_type_captured, key_obj, key_name):
        if hotkey_type_captured == SETTING_START_RECORD_HOTKEY: self.current_start_record_hotkey, self.current_start_record_hotkey_name = key_obj, key_name
        elif hotkey_type_captured == SETTING_PLAY_RECORD_HOTKEY: self.current_play_record_hotkey, self.current_play_record_hotkey_name = key_obj, key_name
        self.init_record_play_hotkey_listeners()
        # self.retranslate_ui(); self._update_controls_state() # Goi boi on_set_hotkey_finished_or_cancelled

    @Slot(int) # hotkey_type
    def on_set_hotkey_finished_or_cancelled(self, hotkey_type):
        if hotkey_type == SETTING_START_RECORD_HOTKEY or hotkey_type == SETTING_PLAY_RECORD_HOTKEY:
            self.retranslate_ui(); self._update_controls_state()
            self.setting_hotkey_status_changed_signal.emit(False, hotkey_type)

    def load_settings(self, settings):
        rec_hk_data = settings.get("recorder_start_hotkey"); deser_rec_hk = self.parent_window._deserialize_key(rec_hk_data)
        if deser_rec_hk: self.current_start_record_hotkey, self.current_start_record_hotkey_name = deser_rec_hk, get_pynput_key_display_name(deser_rec_hk)
        else: self.current_start_record_hotkey, self.current_start_record_hotkey_name = DEFAULT_START_RECORD_HOTKEY, get_pynput_key_display_name(DEFAULT_START_RECORD_HOTKEY)
        play_hk_data = settings.get("recorder_play_hotkey"); deser_play_hk = self.parent_window._deserialize_key(play_hk_data)
        if deser_play_hk: self.current_play_record_hotkey, self.current_play_record_hotkey_name = deser_play_hk, get_pynput_key_display_name(deser_play_hk)
        else: self.current_play_record_hotkey, self.current_play_record_hotkey_name = DEFAULT_PLAY_RECORD_HOTKEY, get_pynput_key_display_name(DEFAULT_PLAY_RECORD_HOTKEY)
        self.spin_record_repetitions.setValue(settings.get("recorder_repetitions", DEFAULT_RECORD_REPETITIONS))
        self.recorded_events = []
        saved_evts = settings.get("recorded_events_v2", [])
        for sev in saved_evts:
            k_obj_s = sev.get("key_obj_s"); k_obj = self.parent_window._deserialize_key(k_obj_s)
            if k_obj:
                k_name_d = sev.get("key_name_display", get_pynput_key_display_name(k_obj))
                act_c, delay = sev.get("action_canonical"), sev.get("delay_ms")
                if act_c and delay is not None: self.recorded_events.append((k_obj, k_name_d, act_c, delay))
        self._update_recorded_events_table() # Cap nhat table sau khi load
        self.init_record_play_hotkey_listeners() # Init listener sau khi load
        self.retranslate_ui(); self._update_controls_state()

    def save_settings(self, settings_dict):
        settings_dict["recorder_start_hotkey"] = self.parent_window._serialize_key(self.current_start_record_hotkey)
        settings_dict["recorder_play_hotkey"] = self.parent_window._serialize_key(self.current_play_record_hotkey)
        settings_dict["recorder_repetitions"] = self.spin_record_repetitions.value()
        saved_evts_data = []
        for k_obj, k_name_d, act_c, delay in self.recorded_events:
            k_obj_s = self.parent_window._serialize_key(k_obj)
            if k_obj_s: saved_evts_data.append({"key_obj_s": k_obj_s, "key_name_display": k_name_d, "action_canonical": act_c, "delay_ms": delay})
        settings_dict["recorded_events_v2"] = saved_evts_data

    def cleanup_resources(self):
        self.parent_window._cleanup_thread_worker('recorder_thread', 'recorder_worker', self)
        self.parent_window._cleanup_thread_worker('player_thread', 'player_worker', self)
        self.parent_window._cleanup_thread_worker('start_record_hotkey_listener_thread', 'start_record_hotkey_listener_worker', self)
        self.parent_window._cleanup_thread_worker('play_record_hotkey_listener_thread', 'play_record_hotkey_listener_worker', self)