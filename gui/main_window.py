# gui/main_window.py
import sys
import os
import json # Them json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox, QFormLayout,
    QSizePolicy, QFrame, QStackedWidget, QGroupBox, QTableWidget, QHeaderView,
    QTableWidgetItem, QAbstractItemView, QStackedLayout
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot, QPoint, QSize, QRect
from PySide6.QtGui import QFont, QPixmap, QIcon, QMouseEvent, QKeyEvent, QScreen # them QScreen
from pynput.keyboard import Key as PynputKey, KeyCode # Them KeyCode

from core.translations import Translations
from core.workers import (AutoTyperWorker, HotkeyListenerWorker, SingleKeyListenerWorker,
                          get_pynput_key_display_name, KeyboardRecorderWorker, RecordedPlayerWorker)
from .custom_title_bar import CustomTitleBar

# Lop overlay dem nguoc
class CountdownOverlay(QWidget):
    def __init__(self, parent=None): # Parent mac dinh la None
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

    def setText(self, text):
        self.label.setText(text)
        self.adjustSize() 
        
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
            y = (screen_geometry.height() - self.height()) // 3 
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)

class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    DEFAULT_START_RECORD_HOTKEY = PynputKey.f10
    DEFAULT_PLAY_RECORD_HOTKEY = PynputKey.f11
    DEFAULT_RECORD_REPETITIONS = 1 

    RESIZE_MARGIN = 10
    NO_EDGE, TOP_EDGE, BOTTOM_EDGE, LEFT_EDGE, RIGHT_EDGE = 0x0, 0x1, 0x2, 0x4, 0x8
    TOP_LEFT_CORNER, TOP_RIGHT_CORNER = TOP_EDGE | LEFT_EDGE, TOP_EDGE | RIGHT_EDGE
    BOTTOM_LEFT_CORNER, BOTTOM_RIGHT_CORNER = BOTTOM_EDGE | LEFT_EDGE, BOTTOM_EDGE | RIGHT_EDGE

    SETTING_MAIN_HOTKEY = 1
    SETTING_START_RECORD_HOTKEY = 2
    SETTING_PLAY_RECORD_HOTKEY = 3

    CONFIG_FILE_NAME = "autokeyboard_config.json" 

    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.config_path = os.path.join(self.base_path, self.CONFIG_FILE_NAME) 
        self.background_image_filename = "stellar.jpg"
        self.background_image_path = os.path.join(self.base_path, "assets", self.background_image_filename).replace("\\", "/")

        
        Translations.set_language(Translations.LANG_VI)

        self.DEFAULT_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_HOTKEY)
        self.DEFAULT_START_RECORD_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_START_RECORD_HOTKEY)
        self.DEFAULT_PLAY_RECORD_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_PLAY_RECORD_HOTKEY)

        self.setMinimumSize(700, 600)
        self.resize(850, 700) 

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.is_typing_active = False
        self.current_hotkey = self.DEFAULT_HOTKEY
        self.current_hotkey_name = self.DEFAULT_HOTKEY_NAME
        self.autotyper_thread = None; self.autotyper_worker = None
        self.hotkey_listener_thread = None; self.hotkey_listener_worker = None

        self.current_start_record_hotkey = self.DEFAULT_START_RECORD_HOTKEY
        self.current_start_record_hotkey_name = self.DEFAULT_START_RECORD_HOTKEY_NAME
        self.current_play_record_hotkey = self.DEFAULT_PLAY_RECORD_HOTKEY
        self.current_play_record_hotkey_name = self.DEFAULT_PLAY_RECORD_HOTKEY_NAME

        self.start_record_hotkey_listener_thread = None; self.start_record_hotkey_listener_worker = None
        self.play_record_hotkey_listener_thread = None; self.play_record_hotkey_listener_worker = None

        self.recorder_thread = None; self.recorder_worker = None
        self.player_thread = None; self.player_worker = None

        self.is_recording = False
        self.is_playing_recording = False
        self.recorded_events = [] 

        self.is_setting_hotkey_type = 0 

        self.single_key_listener_thread = QThread(self)
        self.single_key_listener_worker = SingleKeyListenerWorker()
        self.single_key_listener_worker.moveToThread(self.single_key_listener_thread)
        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured_generic)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error_generic)
        self.single_key_listener_worker.listener_operation_finished_signal.connect(self._on_single_key_listener_operation_finished_generic)
        self.single_key_listener_thread.started.connect(self.single_key_listener_worker.run)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_worker.deleteLater) 
        self.single_key_listener_thread.finished.connect(self.single_key_listener_thread.deleteLater) 
        self.single_key_listener_thread.start()

        self.original_pixmap = QPixmap(self.background_image_path)
        self._is_dragging = False; self._drag_start_pos = QPoint()
        self._is_resizing = False; self._resize_edge = self.NO_EDGE
        self._resize_start_mouse_pos = QPoint(); self._resize_start_window_geometry = QRect()

        self.countdown_overlay = None 

        
        self.init_ui_elements()
        self._load_settings() 
        self.apply_styles() 

        
        self.init_main_hotkey_listener()
        self.init_start_record_hotkey_listener()
        self.init_play_record_hotkey_listener()

        self._retranslate_ui() 
        self.setMouseTracking(True)

    def init_ui_elements(self):
        self.main_container_widget = QWidget(); self.main_container_widget.setObjectName("mainContainerWidget")
        self.setCentralWidget(self.main_container_widget)
        overall_layout = QVBoxLayout(self.main_container_widget); overall_layout.setContentsMargins(0,0,0,0); overall_layout.setSpacing(0)

        
        self.custom_title_bar = CustomTitleBar(self, current_lang_code=Translations.current_lang)
        self.custom_title_bar.language_changed_signal.connect(self._handle_language_change)
        self.custom_title_bar.toggle_advanced_mode_signal.connect(self._toggle_view_mode)
        overall_layout.addWidget(self.custom_title_bar)

        
        main_area_widget = QWidget(); main_area_layout = QVBoxLayout(main_area_widget); main_area_layout.setContentsMargins(0,0,0,0); main_area_layout.setSpacing(0)

        
        self.view_stack = QStackedWidget()
        self.autotyper_page = self._create_autotyper_page_widget()
        self.view_stack.addWidget(self.autotyper_page)
        self.recorder_page = self._create_recorder_page_widget()
        self.view_stack.addWidget(self.recorder_page)

        
        main_area_stacked_layout = QStackedLayout(); main_area_stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.background_label = QLabel(); self.background_label.setObjectName("backgroundLabel")
        if self.original_pixmap.isNull(): self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.background_label.setStyleSheet("background-color: rgb(10, 12, 22); color: white;") 
        else: self._update_background_pixmap()
        self.background_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored) 
        main_area_stacked_layout.addWidget(self.background_label) 
        main_area_stacked_layout.addWidget(self.view_stack) 

        main_area_layout.addLayout(main_area_stacked_layout)
        overall_layout.addWidget(main_area_widget)

    def _create_autotyper_page_widget(self):
        page_widget = QWidget(); page_widget.setObjectName("autotyperPageWidget")
        content_layout = QVBoxLayout(page_widget); content_layout.setContentsMargins(30, 15, 30, 20); content_layout.setSpacing(15)

        
        input_frame = QFrame(); input_frame.setObjectName("inputFrame")
        self.form_layout = QFormLayout(input_frame); self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows); self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft); self.form_layout.setHorizontalSpacing(10); self.form_layout.setVerticalSpacing(12)
        self.label_for_text_entry = QLabel(); self.entry_text = QLineEdit(); self.entry_text.setObjectName("textInput"); self.form_layout.addRow(self.label_for_text_entry, self.entry_text)
        self.label_for_interval = QLabel(); self.spin_interval = QSpinBox(); self.spin_interval.setRange(1,600000); self.spin_interval.setValue(1000); self.spin_interval.setObjectName("intervalInput"); self.form_layout.addRow(self.label_for_interval, self.spin_interval)
        self.label_for_repetitions = QLabel(); self.spin_repetitions = QSpinBox(); self.spin_repetitions.setRange(0,1000000); self.spin_repetitions.setValue(0); self.spin_repetitions.setObjectName("repetitionsInput"); self.form_layout.addRow(self.label_for_repetitions, self.spin_repetitions)
        content_layout.addWidget(input_frame)

        
        self.autotyper_hotkey_group = QGroupBox(); self.autotyper_hotkey_group.setObjectName("hotkeyGroup")
        hotkey_group_layout = QVBoxLayout(self.autotyper_hotkey_group); hotkey_group_layout.setSpacing(8)
        current_hotkey_layout = QHBoxLayout()
        self.lbl_current_hotkey_static = QLabel() 
        self.lbl_current_hotkey_value = QLabel(self.current_hotkey_name) 
        self.lbl_current_hotkey_value.setObjectName("currentHotkeyDisplay")
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_static)
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_value)
        current_hotkey_layout.addStretch()
        hotkey_group_layout.addLayout(current_hotkey_layout)
        self.btn_set_hotkey = QPushButton(); self.btn_set_hotkey.setObjectName("setHotkeyButton"); self.btn_set_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey_generic(self.SETTING_MAIN_HOTKEY))
        self.btn_set_hotkey.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) 
        hotkey_group_layout.addWidget(self.btn_set_hotkey, 0, Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(self.autotyper_hotkey_group)

        
        button_layout_container = QWidget(); button_layout = QHBoxLayout(button_layout_container); button_layout.setContentsMargins(0,8,0,0) 
        self.btn_start = QPushButton(); self.btn_start.setObjectName("startButton"); self.btn_start.clicked.connect(self.toggle_typing_process)
        self.btn_stop = QPushButton(); self.btn_stop.setObjectName("stopButton"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_typing_process)
        button_layout.addStretch(); button_layout.addWidget(self.btn_start); button_layout.addWidget(self.btn_stop); button_layout.addStretch()
        content_layout.addWidget(button_layout_container)

        
        self.status_label = QLabel(); self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        content_layout.addStretch() 
        return page_widget

    def _create_recorder_page_widget(self):
        page_widget = QWidget(); page_widget.setObjectName("recorderPageWidget")
        content_layout = QVBoxLayout(page_widget); content_layout.setContentsMargins(20, 15, 20, 20); content_layout.setSpacing(12)

        
        self.record_play_hotkey_group = QGroupBox(); self.record_play_hotkey_group.setObjectName("hotkeyGroup")
        record_play_hotkey_layout = QFormLayout(self.record_play_hotkey_group) 
        record_play_hotkey_layout.setSpacing(10)

        self.lbl_current_start_record_hotkey_static = QLabel()
        start_rec_hotkey_val_layout = QHBoxLayout() 
        self.lbl_current_start_record_hotkey_value = QLabel(self.current_start_record_hotkey_name)
        self.lbl_current_start_record_hotkey_value.setObjectName("currentHotkeyDisplay")
        self.btn_set_start_record_hotkey = QPushButton()
        self.btn_set_start_record_hotkey.setObjectName("setHotkeyButtonSmall") 
        self.btn_set_start_record_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey_generic(self.SETTING_START_RECORD_HOTKEY))
        start_rec_hotkey_val_layout.addWidget(self.lbl_current_start_record_hotkey_value)
        start_rec_hotkey_val_layout.addWidget(self.btn_set_start_record_hotkey)
        start_rec_hotkey_val_layout.addStretch()
        record_play_hotkey_layout.addRow(self.lbl_current_start_record_hotkey_static, start_rec_hotkey_val_layout)

        self.lbl_current_play_record_hotkey_static = QLabel()
        play_rec_hotkey_val_layout = QHBoxLayout()
        self.lbl_current_play_record_hotkey_value = QLabel(self.current_play_record_hotkey_name)
        self.lbl_current_play_record_hotkey_value.setObjectName("currentHotkeyDisplay")
        self.btn_set_play_record_hotkey = QPushButton()
        self.btn_set_play_record_hotkey.setObjectName("setHotkeyButtonSmall")
        self.btn_set_play_record_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey_generic(self.SETTING_PLAY_RECORD_HOTKEY))
        play_rec_hotkey_val_layout.addWidget(self.lbl_current_play_record_hotkey_value)
        play_rec_hotkey_val_layout.addWidget(self.btn_set_play_record_hotkey)
        play_rec_hotkey_val_layout.addStretch()
        record_play_hotkey_layout.addRow(self.lbl_current_play_record_hotkey_static, play_rec_hotkey_val_layout)
        content_layout.addWidget(self.record_play_hotkey_group)

        
        self.recorded_events_table = QTableWidget(); self.recorded_events_table.setObjectName("recordedEventsTable")
        self.recorded_events_table.setColumnCount(3) 
        self.recorded_events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) 
        self.recorded_events_table.verticalHeader().setVisible(False) 
        self.recorded_events_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) 
        self.recorded_events_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) 
        content_layout.addWidget(self.recorded_events_table, 1) 
        
        
        playback_options_container = QWidget() 
        playback_options_layout = QHBoxLayout(playback_options_container)
        playback_options_layout.setContentsMargins(0, 5, 0, 5) 
        self.label_for_record_repetitions = QLabel()
        self.spin_record_repetitions = QSpinBox()
        self.spin_record_repetitions.setRange(0, 1000000) 
        self.spin_record_repetitions.setValue(self.DEFAULT_RECORD_REPETITIONS) 
        self.spin_record_repetitions.setObjectName("recordRepetitionsInput")
        playback_options_layout.addStretch(1)
        playback_options_layout.addWidget(self.label_for_record_repetitions)
        playback_options_layout.addWidget(self.spin_record_repetitions)
        playback_options_layout.addStretch(1)
        content_layout.addWidget(playback_options_container)


        
        recorder_button_layout = QHBoxLayout()
        self.btn_start_record = QPushButton(); self.btn_start_record.setObjectName("recordButton"); self.btn_start_record.clicked.connect(self.toggle_recording_process)
        self.btn_play_record = QPushButton(); self.btn_play_record.setObjectName("playRecordButton"); self.btn_play_record.clicked.connect(self.toggle_playing_process)
        self.btn_clear_record = QPushButton(); self.btn_clear_record.setObjectName("clearRecordButton"); self.btn_clear_record.clicked.connect(self._clear_recorded_events)
        recorder_button_layout.addStretch()
        recorder_button_layout.addWidget(self.btn_start_record)
        recorder_button_layout.addWidget(self.btn_play_record)
        recorder_button_layout.addWidget(self.btn_clear_record)
        recorder_button_layout.addStretch()
        content_layout.addLayout(recorder_button_layout)

        
        self.recorder_status_label = QLabel(); self.recorder_status_label.setObjectName("statusLabel"); self.recorder_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.recorder_status_label)
        return page_widget

    @Slot(bool)
    def _toggle_view_mode(self, to_advanced_mode, from_load=False): 
        current_target_widget = self.recorder_page if to_advanced_mode else self.autotyper_page
        if self.view_stack.currentWidget() != current_target_widget or from_load: 
            self.view_stack.setCurrentWidget(current_target_widget)
            self.custom_title_bar.set_mode_button_state(to_advanced_mode) 

        
        if to_advanced_mode:
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group"))
        else:
            self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))

        if not from_load: 
            self._retranslate_ui()


    def _retranslate_ui(self):
        
        current_widget = self.view_stack.currentWidget()
        if current_widget == self.autotyper_page:
            self.setWindowTitle(Translations.get("window_title")) 
            self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))
        elif current_widget == self.recorder_page:
            self.setWindowTitle(Translations.get("label_record_play_group")) 
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group"))
        self.custom_title_bar.retranslate_ui_texts() 

        
        if self.original_pixmap.isNull():
            
            if not hasattr(self, "_bg_error_logged") or self._bg_error_logged != Translations.current_lang:
                print(Translations.get("error_loading_background_msg_console", path=self.background_image_path))
                self._bg_error_logged = Translations.current_lang 
            self.background_label.setText(Translations.get("error_loading_background_ui"))

        
        self.label_for_text_entry.setText(Translations.get("label_text_key"))
        self.entry_text.setPlaceholderText(Translations.get("text_input_placeholder"))
        self.label_for_interval.setText(Translations.get("label_interval"))
        self.spin_interval.setSuffix(Translations.get("interval_suffix"))
        self.label_for_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_repetitions.setSpecialValueText(Translations.get("repetitions_infinite")) 
        self.autotyper_hotkey_group.setTitle(Translations.get("label_hotkey_setting_group"))
        self.lbl_current_hotkey_static.setText(Translations.get("label_current_hotkey"))
        self.lbl_current_hotkey_value.setText(self.current_hotkey_name) 

        
        if self.is_setting_hotkey_type == self.SETTING_MAIN_HOTKEY:
            self.btn_set_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_hotkey.setText(Translations.get("button_set_hotkey"))

        
        if self.is_typing_active: 
            self.btn_start.setText(Translations.get("button_start_loading")) 
            
        else: 
            self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name))
            
            current_status = self.status_label.text() 
            
            ready_status_prefix_en = Translations.get("status_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_status_prefix_en = Translations.get("status_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_fully_prefix_en = Translations.get("status_stopped_fully", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]

            
            is_idle_status = any(
                prefix_en in current_status for prefix_en in
                [ready_status_prefix_en, stopped_status_prefix_en, stopped_fully_prefix_en]
            )

            if current_status == Translations.get("status_requesting_stop"): 
                pass
            
            elif self.autotyper_worker is None and self.autotyper_thread is None and not self.is_typing_active:
                 self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))
            
            elif not self.is_typing_active and (is_idle_status or not current_status):
                self.status_label.setText(Translations.get("status_ready", hotkey_name=self.current_hotkey_name))
            
        self.btn_stop.setText(Translations.get("button_stop"))


        
        self.record_play_hotkey_group.setTitle(Translations.get("label_record_play_group")) 
        self.lbl_current_start_record_hotkey_static.setText(Translations.get("label_start_record_hotkey"))
        self.lbl_current_start_record_hotkey_value.setText(self.current_start_record_hotkey_name)
        self.lbl_current_play_record_hotkey_static.setText(Translations.get("label_play_record_hotkey"))
        self.lbl_current_play_record_hotkey_value.setText(self.current_play_record_hotkey_name)
        
        
        self.label_for_record_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_record_repetitions.setSpecialValueText(Translations.get("repetitions_infinite"))
        self.spin_record_repetitions.setSuffix("") 


        
        if self.is_setting_hotkey_type == self.SETTING_START_RECORD_HOTKEY:
            self.btn_set_start_record_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_start_record_hotkey.setText(Translations.get("button_set_start_record_hotkey"))

        
        if self.is_setting_hotkey_type == self.SETTING_PLAY_RECORD_HOTKEY:
            self.btn_set_play_record_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_play_record_hotkey.setText(Translations.get("button_set_play_record_hotkey"))

        
        current_recorder_status = self.recorder_status_label.text() 
        
        recorder_idle_prefix_en = Translations.get("status_recorder_idle", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        recorder_stopped_prefix_en = Translations.get("status_recorder_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_ready_prefix_en = Translations.get("status_player_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_stopped_prefix_en = Translations.get("status_player_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_error_prefix_en = Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("! ")[0] 

        if self.is_recording:
            self.btn_start_record.setText(Translations.get("button_stop_recording", hotkey_name=self.current_start_record_hotkey_name))
            
        else: 
            self.btn_start_record.setText(Translations.get("button_start_recording", hotkey_name=self.current_start_record_hotkey_name))
            
            if not self.is_playing_recording and (not current_recorder_status or \
                any(p in current_recorder_status for p in [recorder_idle_prefix_en, recorder_stopped_prefix_en])) and \
                player_error_prefix_en not in current_recorder_status: 
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))


        if self.is_playing_recording:
            self.btn_play_record.setText(Translations.get("button_stop_playing_recording", hotkey_name=self.current_play_record_hotkey_name))
            
        else: 
            self.btn_play_record.setText(Translations.get("button_play_recording", hotkey_name=self.current_play_record_hotkey_name))
            
            if len(self.recorded_events) > 0 and not self.is_recording and \
               (not current_recorder_status or any(p in current_recorder_status for p in [player_ready_prefix_en, player_stopped_prefix_en, player_error_prefix_en, recorder_idle_prefix_en, recorder_stopped_prefix_en])):
                if player_error_prefix_en not in current_recorder_status: 
                     self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
                
            
            elif len(self.recorded_events) == 0 and not self.is_recording and \
                 (not current_recorder_status or any(p in current_recorder_status for p in [recorder_idle_prefix_en, recorder_stopped_prefix_en])) and \
                 player_error_prefix_en not in current_recorder_status : 
                     self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))


        self.btn_clear_record.setText(Translations.get("button_clear_recording"))
        self.recorded_events_table.setHorizontalHeaderLabels([
            Translations.get("table_header_key"),
            Translations.get("table_header_action"),
            Translations.get("table_header_delay")
        ])

        
        if not self.recorder_status_label.text() and not self.is_recording and not self.is_playing_recording:
            self.recorder_status_label.setText(Translations.get("recorder_status_label_default"))


    @Slot(str)
    def _handle_language_change(self, lang_code):
        Translations.set_language(lang_code)
        self._retranslate_ui() 
        self.apply_styles() 

    def apply_styles(self):
        font_family = "Segoe UI, Arial, sans-serif"
        if Translations.current_lang == Translations.LANG_JA:
            font_family = "Meiryo, Segoe UI, Arial, sans-serif" 

        
        app_main_container_bg = "rgb(10, 12, 22)"; title_bar_bg = "rgba(15, 18, 30, 0.9)"; title_bar_text_color = "rgb(224, 218, 230)"
        title_bar_button_bg = "transparent"; title_bar_button_hover_bg = "rgba(224, 218, 230, 0.15)"; title_bar_button_pressed_bg = "rgba(224, 218, 230, 0.08)"
        close_button_hover_bg = "rgba(200, 90, 110, 0.75)"; close_button_pressed_bg = "rgba(190, 80, 100, 0.6)"
        input_frame_bg_color = "rgba(20, 24, 40, 0.88)"; input_frame_border_color = "rgba(170, 150, 200, 0.4)"
        text_color = "rgb(238, 235, 245)"; subtext_color = "rgb(175, 170, 185)" 
        input_bg_color = "rgba(12, 15, 28, 0.92)"; input_border_color = "rgba(170, 150, 200, 0.55)"
        input_focus_border_color = "rgb(210, 190, 250)"; input_focus_bg_color = "rgba(22, 25, 45, 0.96)"
        button_text_color = text_color; button_bg_color = "rgba(75, 80, 115, 0.92)"; button_border_color = "rgba(210, 190, 250, 0.7)"
        start_button_bg_color = "rgba(96, 125, 199, 0.65)"; start_button_border_color = "rgba(126, 155, 229, 0.85)" 
        start_button_hover_bg = "rgba(116, 145, 219, 0.75)"; start_button_pressed_bg = "rgba(86, 115, 189, 0.6)"; start_button_hover_border_color_val = "rgb(116, 145, 219)"
        stop_button_hover_bg = "rgba(210, 190, 250, 0.6)"; stop_button_pressed_bg = "rgba(210, 190, 250, 0.4)"
        disabled_bg_color = "rgba(60, 63, 90, 0.7)"; disabled_text_color = "rgba(160, 155, 170, 0.75)"; disabled_border_color = "rgba(170, 150, 200, 0.3)"
        status_bg_color = "rgba(20, 24, 40, 0.85)"; status_border_color = "rgba(100, 105, 140, 0.7)"
        msgbox_bg_color = "rgb(20, 22, 40)"; msgbox_text_color = "rgb(230, 225, 235)"; msgbox_button_bg = start_button_bg_color
        msgbox_button_border = start_button_border_color; msgbox_button_hover_bg = start_button_hover_bg
        combo_box_bg = input_bg_color; combo_box_border = input_border_color; combo_box_dropdown_bg = "rgb(25, 28, 48)"; combo_box_dropdown_item_hover_bg = "rgba(96, 125, 199, 0.4)"
        hotkey_group_border_color = input_frame_border_color; hotkey_value_color = "rgb(180, 210, 255)"; 
        set_hotkey_button_padding = "6px 15px"; set_hotkey_button_min_width = "120px";
        table_bg = "rgba(15, 18, 30, 0.85)"; table_grid_color = "rgba(100, 105, 140, 0.5)"; table_header_bg = "rgba(25, 30, 50, 0.9)";
        record_button_bg = "rgba(200, 80, 80, 0.7)"; record_button_hover_bg = "rgba(220, 90, 90, 0.8)"; record_button_pressed_bg = "rgba(180, 70, 70, 0.6)"; 
        play_button_bg = "rgba(80, 150, 200, 0.7)"; play_button_hover_bg = "rgba(90, 170, 220, 0.8)"; play_button_pressed_bg = "rgba(70, 130, 180, 0.6)"; 
        clear_button_bg = "rgba(120, 120, 120, 0.7)"; clear_button_hover_bg = "rgba(140, 140, 140, 0.8)"; clear_button_pressed_bg = "rgba(100, 100, 100, 0.6)"; 
        toggle_mode_button_padding = "5px 12px"; toggle_mode_button_font_size = "9pt";

        qss = f"""
            QMainWindow {{ background: transparent; }} 
            QWidget#mainContainerWidget {{ background-color: {app_main_container_bg}; border-radius: 10px; }} 
            QWidget#autotyperPageWidget, QWidget#recorderPageWidget {{ background-color: transparent; }} 
            QLabel#backgroundLabel {{ border-radius: 10px; }} 

            
            QWidget#customTitleBar {{ background-color: {title_bar_bg}; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid rgba(224, 218, 230, 0.1); }}
            QLabel#titleBarLabel {{ color: {title_bar_text_color}; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; padding-left: 5px; background-color: transparent; }}

            QPushButton#toggleModeButton {{
                background-color: {button_bg_color}; color: {button_text_color};
                border: 1px solid {button_border_color}; border-radius: 6px;
                padding: {toggle_mode_button_padding}; font-family: "{font_family}"; font-size: {toggle_mode_button_font_size};
                min-width: 80px; 
            }}
            QPushButton#toggleModeButton:hover {{ background-color: {start_button_hover_bg}; }}
            QPushButton#toggleModeButton:checked {{ background-color: {start_button_bg_color}; }} 


            
            QPushButton#minimizeButton, QPushButton#maximizeRestoreButton, QPushButton#closeButton {{
                background-color: {title_bar_button_bg}; border: none; border-radius: 6px;
                color: {subtext_color}; font-family: "{font_family}"; font-size: 12pt; font-weight: bold;
                min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0px;
            }}
            QPushButton#minimizeButton:hover, QPushButton#maximizeRestoreButton:hover {{ background-color: {title_bar_button_hover_bg}; color: {text_color};}}
            QPushButton#closeButton:hover {{ background-color: {close_button_hover_bg}; color: white; }}
            QPushButton#minimizeButton:pressed, QPushButton#maximizeRestoreButton:pressed {{ background-color: {title_bar_button_pressed_bg}; }}
            QPushButton#closeButton:pressed {{ background-color: {close_button_pressed_bg}; }}

            
            QComboBox#languageComboBox {{
                background-color: {combo_box_bg}; color: {text_color};
                border: 1px solid {combo_box_border}; border-radius: 6px;
                padding: 4px 8px; 
                font-family: "{font_family}"; font-size: 9pt; min-height: 20px; 
            }}
            QComboBox#languageComboBox:hover {{ border-color: {input_focus_border_color}; }}
            QComboBox#languageComboBox::drop-down {{ 
                subcontrol-origin: padding; subcontrol-position: top right; width: 18px;
                border-left-width: 1px; border-left-color: {combo_box_border}; border-left-style: solid;
                border-top-right-radius: 6px; border-bottom-right-radius: 6px;
            }}
            QComboBox QAbstractItemView {{ 
                background-color: {combo_box_dropdown_bg}; color: {text_color};
                border: 1px solid {input_focus_border_color};
                selection-background-color: {combo_box_dropdown_item_hover_bg}; 
                padding: 3px; border-radius: 4px; font-family: "{font_family}"; font-size: 9pt;
            }}

            
            QFrame#inputFrame {{ background-color: {input_frame_bg_color}; border-radius: 14px; padding: 20px; border: 1.5px solid {input_frame_border_color}; }}
            QGroupBox#hotkeyGroup {{
                font-family: "{font_family}"; font-size: 10pt; color: {text_color};
                border: 1.5px solid {hotkey_group_border_color}; border-radius: 10px;
                margin-top: 8px; 
                padding: 15px 15px 10px 15px; 
                background-color: transparent; 
            }}
            QGroupBox#hotkeyGroup::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 5px 0 5px; 
                left: 10px; 
                color: {subtext_color}; 
            }}

            
            QLabel {{ color: {text_color}; font-family: "{font_family}"; font-size: 10pt; padding: 2px; background-color: transparent; }}
            QLabel#currentHotkeyDisplay {{ color: {hotkey_value_color}; font-weight: bold; font-size: 10pt; padding-left: 5px;}}
            QLineEdit, QSpinBox {{
                background-color: {input_bg_color}; color: {text_color};
                border: 1.5px solid {input_border_color}; border-radius: 9px;
                padding: 9px 12px; font-family: "{font_family}"; font-size: 10pt;
                min-height: 24px; 
            }}
            QSpinBox#recordRepetitionsInput {{ 
                min-width: 70px; 
                max-width: 100px;
            }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1.5px solid {input_focus_border_color}; background-color: {input_focus_bg_color}; }}
            QLineEdit::placeholder {{ color: {subtext_color}; }} 

            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border; subcontrol-position: right; 
                width: 18px; border: 1.5px solid {input_border_color}; border-radius: 5px;
                background-color: {button_bg_color}; margin: 2px 3px 2px 2px; 
            }}
            QSpinBox::up-button {{ top: 1px; height: 11px;}} 
            QSpinBox::down-button {{ bottom: 1px; height: 11px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: rgba(95, 100, 135, 0.95); }}
            

            
            QPushButton {{
                color: {button_text_color}; background-color: {button_bg_color};
                border: 1.5px solid {button_border_color};
                padding: 10px 22px; border-radius: 10px;
                font-family: "{font_family}"; font-size: 10pt; font-weight: bold;
                min-width: 130px; 
            }}
            QPushButton#startButton {{ background-color: {start_button_bg_color}; border-color: {start_button_border_color}; }}
            QPushButton#startButton:hover {{ background-color: {start_button_hover_bg}; border-color: {start_button_hover_border_color_val};}}
            QPushButton#startButton:pressed {{ background-color: {start_button_pressed_bg}; }}
            QPushButton#stopButton:hover {{ background-color: {stop_button_hover_bg}; border-color: rgb(210, 190, 250);}}
            QPushButton#stopButton:pressed {{ background-color: {stop_button_pressed_bg}; }}

            QPushButton#setHotkeyButton {{ 
                padding: {set_hotkey_button_padding}; min-width: {set_hotkey_button_min_width}; max-width: 180px; 
                font-size: 9pt; 
            }}
            QPushButton#setHotkeyButtonSmall {{ 
                padding: 5px 12px; min-width: 100px; max-width: 150px; font-size: 9pt;
                background-color: {button_bg_color}; border-color: {button_border_color}; 
            }}
            QPushButton#setHotkeyButtonSmall:hover {{ background-color: {start_button_hover_bg}; }} 


            
            QPushButton#recordButton {{ background-color: {record_button_bg}; }}
            QPushButton#recordButton:hover {{ background-color: {record_button_hover_bg}; }}
            QPushButton#recordButton:pressed {{ background-color: {record_button_pressed_bg}; }}

            QPushButton#playRecordButton {{ background-color: {play_button_bg}; }}
            QPushButton#playRecordButton:hover {{ background-color: {play_button_hover_bg}; }}
            QPushButton#playRecordButton:pressed {{ background-color: {play_button_pressed_bg}; }}

            QPushButton#clearRecordButton {{ background-color: {clear_button_bg}; }}
            QPushButton#clearRecordButton:hover {{ background-color: {clear_button_hover_bg}; }}
            QPushButton#clearRecordButton:pressed {{ background-color: {clear_button_pressed_bg}; }}


            QPushButton:disabled {{ background-color: {disabled_bg_color}; color: {disabled_text_color}; border-color: {disabled_border_color}; }}

            
            QLabel#statusLabel {{
                color: {subtext_color}; background-color: {status_bg_color};
                border: 1px solid {status_border_color}; border-radius: 9px;
                padding: 12px; font-size: 9pt; margin-top: 10px; 
                font-family: "{font_family}";
            }}

            
            QTableWidget#recordedEventsTable {{
                background-color: {table_bg}; color: {text_color}; gridline-color: {table_grid_color};
                border: 1.5px solid {input_frame_border_color}; border-radius: 8px;
                font-family: "{font_family}"; font-size: 9pt;
            }}
            QHeaderView::section {{ 
                background-color: {table_header_bg}; color: {text_color};
                padding: 5px; border: 1px solid {table_grid_color}; font-weight: bold;
            }}
            QTableWidget::item {{ padding: 5px; }} 
            QTableWidget::item:selected {{ background-color: {start_button_hover_bg}; color: white; }}


            
            QMessageBox {{ background-color: {msgbox_bg_color}; font-family: "{font_family}"; border-radius: 8px; border: 1px solid {input_frame_border_color}; }}
            QMessageBox QLabel {{ color: {msgbox_text_color}; font-size: 10pt; background-color: transparent; font-family: "{font_family}";}} 
            QMessageBox QPushButton {{ 
                background-color: {msgbox_button_bg}; border-color: {msgbox_button_border}; color: {button_text_color};
                padding: 8px 18px; border-radius: 8px; min-width: 80px; font-family: "{font_family}";
            }}
            QMessageBox QPushButton:hover {{ background-color: {msgbox_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }}
        """
        
        app_font = QFont("Segoe UI", 10) 
        if Translations.current_lang == Translations.LANG_JA: app_font = QFont("Meiryo", 9) 
        QApplication.setFont(app_font)

        self.setStyleSheet(qss) 
        self.update(); 
        if self.parent(): self.parent().update() 

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

    def resizeEvent(self, event): self._update_background_pixmap(); super().resizeEvent(event)

    
    def _get_current_resize_edge(self, local_pos: QPoint) -> int:
        edge = self.NO_EDGE; rect = self.rect()
        if local_pos.x() < self.RESIZE_MARGIN: edge |= self.LEFT_EDGE
        if local_pos.x() > rect.width() - self.RESIZE_MARGIN: edge |= self.RIGHT_EDGE
        if local_pos.y() < self.RESIZE_MARGIN: edge |= self.TOP_EDGE 
        if local_pos.y() > rect.height() - self.RESIZE_MARGIN: edge |= self.BOTTOM_EDGE
        return edge

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint(); global_pos = event.globalPosition().toPoint()

            
            self._resize_edge = self._get_current_resize_edge(local_pos)
            
            is_on_title_bar_geom = self.custom_title_bar.geometry().contains(local_pos)

            if self._resize_edge != self.NO_EDGE and not (is_on_title_bar_geom and self._resize_edge != self.TOP_EDGE) :
                self._is_resizing = True; self._is_dragging = False
                self._resize_start_mouse_pos = global_pos; self._resize_start_window_geometry = self.geometry()
                event.accept(); return

            
            is_on_interactive_title_widget = False
            
            interactive_widgets_on_title = self.custom_title_bar.findChildren(QPushButton) + \
                                           [self.custom_title_bar.lang_combo, self.custom_title_bar.btn_toggle_mode]
            for child_widget in interactive_widgets_on_title:
                
                if child_widget.isVisible() and child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(global_pos)):
                    is_on_interactive_title_widget = True; break

            if is_on_title_bar_geom and not is_on_interactive_title_widget:
                self._is_dragging = True; self._is_resizing = False
                self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                event.accept(); return

        super().mousePressEvent(event) 

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton: 
            if self._is_resizing:
                delta = event.globalPosition().toPoint() - self._resize_start_mouse_pos; start_geom = self._resize_start_window_geometry; new_geom = QRect(start_geom)
                min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
                if self._resize_edge & self.LEFT_EDGE: new_left = start_geom.left() + delta.x(); new_width = max(min_w, start_geom.width() - delta.x()); new_geom.setLeft(start_geom.right() - new_width); new_geom.setWidth(new_width)
                if self._resize_edge & self.RIGHT_EDGE: new_geom.setWidth(max(min_w, start_geom.width() + delta.x()))
                if self._resize_edge & self.TOP_EDGE: new_top = start_geom.top() + delta.y(); new_height = max(min_h, start_geom.height() - delta.y()); new_geom.setTop(start_geom.bottom() - new_height); new_geom.setHeight(new_height)
                if self._resize_edge & self.BOTTOM_EDGE: new_geom.setHeight(max(min_h, start_geom.height() + delta.y()))
                self.setGeometry(new_geom); event.accept(); return
            elif self._is_dragging: self.move(event.globalPosition().toPoint() - self._drag_start_pos); event.accept(); return

        
        if not (self._is_resizing or self._is_dragging):
            local_pos = event.position().toPoint(); current_hover_edge = self._get_current_resize_edge(local_pos)
            is_on_title_bar_geom = self.custom_title_bar.geometry().contains(local_pos)

            
            is_on_interactive_title_widget = False
            interactive_widgets_on_title = self.custom_title_bar.findChildren(QPushButton) + \
                                           [self.custom_title_bar.lang_combo, self.custom_title_bar.btn_toggle_mode]
            for child_widget in interactive_widgets_on_title:
                if child_widget.isVisible() and child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(event.globalPosition().toPoint())) : is_on_interactive_title_widget = True; break

            if is_on_interactive_title_widget: self.unsetCursor() 
            elif current_hover_edge == self.TOP_LEFT_CORNER or current_hover_edge == self.BOTTOM_RIGHT_CORNER: self.setCursor(Qt.SizeFDiagCursor)
            elif current_hover_edge == self.TOP_RIGHT_CORNER or current_hover_edge == self.BOTTOM_LEFT_CORNER: self.setCursor(Qt.SizeBDiagCursor)
            elif current_hover_edge & self.LEFT_EDGE or current_hover_edge & self.RIGHT_EDGE: self.setCursor(Qt.SizeHorCursor)
            elif current_hover_edge & self.TOP_EDGE or current_hover_edge & self.BOTTOM_EDGE: self.setCursor(Qt.SizeVerCursor)
            else: self.unsetCursor() 
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            changed_state = False
            if self._is_resizing: self._is_resizing = False; changed_state = True
            if self._is_dragging: self._is_dragging = False; changed_state = True
            if changed_state: self._resize_edge = self.NO_EDGE; self.unsetCursor(); event.accept(); return
        super().mouseReleaseEvent(event)

    
    def _cleanup_thread_worker(self, thread_attr, worker_attr):
        worker = getattr(self, worker_attr, None)
        thread = getattr(self, thread_attr, None)

        if worker:
            if hasattr(worker, 'request_stop'): worker.request_stop()
            

        if thread and thread.isRunning():
            thread.quit() 
            if not thread.wait(1000): 
                
                thread.terminate() 
                thread.wait() 
        
        


    
    def init_main_hotkey_listener(self):
        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker')
        if not self.current_hotkey: return 

        self.hotkey_listener_thread = QThread(self)
        self.hotkey_listener_worker = HotkeyListenerWorker(self.current_hotkey)
        self.hotkey_listener_worker.moveToThread(self.hotkey_listener_thread)
        self.hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_typing_process)
        self.hotkey_listener_thread.started.connect(self.hotkey_listener_worker.run)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_worker.deleteLater)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_thread.deleteLater)
        self.hotkey_listener_thread.start()

    def init_start_record_hotkey_listener(self):
        self._cleanup_thread_worker('start_record_hotkey_listener_thread', 'start_record_hotkey_listener_worker')
        if not self.current_start_record_hotkey: return

        self.start_record_hotkey_listener_thread = QThread(self)
        self.start_record_hotkey_listener_worker = HotkeyListenerWorker(self.current_start_record_hotkey)
        self.start_record_hotkey_listener_worker.moveToThread(self.start_record_hotkey_listener_thread)
        self.start_record_hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_recording_process)
        self.start_record_hotkey_listener_thread.started.connect(self.start_record_hotkey_listener_worker.run)
        self.start_record_hotkey_listener_thread.finished.connect(self.start_record_hotkey_listener_worker.deleteLater)
        self.start_record_hotkey_listener_thread.finished.connect(self.start_record_hotkey_listener_thread.deleteLater)
        self.start_record_hotkey_listener_thread.start()

    def init_play_record_hotkey_listener(self):
        self._cleanup_thread_worker('play_record_hotkey_listener_thread', 'play_record_hotkey_listener_worker')
        if not self.current_play_record_hotkey: return

        self.play_record_hotkey_listener_thread = QThread(self)
        self.play_record_hotkey_listener_worker = HotkeyListenerWorker(self.current_play_record_hotkey)
        self.play_record_hotkey_listener_worker.moveToThread(self.play_record_hotkey_listener_thread)
        self.play_record_hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_playing_process)
        self.play_record_hotkey_listener_thread.started.connect(self.play_record_hotkey_listener_worker.run)
        self.play_record_hotkey_listener_thread.finished.connect(self.play_record_hotkey_listener_worker.deleteLater)
        self.play_record_hotkey_listener_thread.finished.connect(self.play_record_hotkey_listener_thread.deleteLater)
        self.play_record_hotkey_listener_thread.start()

    
    def _ensure_not_setting_hotkey_on_action_toggle(self):
        """
        Neu dang dat hotkey, huy.
        Tra ve True neu huy, False neu khong.
        """
        if self.is_setting_hotkey_type != 0:
            type_that_was_being_set = self.is_setting_hotkey_type
            
            if self.single_key_listener_worker:
                self.single_key_listener_worker.cancel_current_listening_operation()
            
            self._finish_set_hotkey_process(type_that_was_being_set)
            return True
        return False

    @Slot()
    def toggle_typing_process(self):
        self._ensure_not_setting_hotkey_on_action_toggle() 

        if self.is_recording: 
            # Khong hien msgbox khi player gay ra, hoac khi dang ghi
            # Neu user thuc su muon go khi dang ghi -> xung dot -> hanh vi hien tai la khong cho phep
            return 
        
        if self.is_playing_recording: 
            # Khong hien msgbox khi player gay ra hotkey nay. Player tiep tuc.
            return

        if self.view_stack.currentWidget() != self.autotyper_page: return 
        
        if self.is_typing_active: self.stop_typing_process()
        else: self.start_typing_process()

    def start_typing_process(self):
        if self.is_typing_active or self.is_setting_hotkey_type != 0 : return
        text = self.entry_text.text(); interval = self.spin_interval.value(); repetitions = self.spin_repetitions.value()
        if not text: QMessageBox.warning(self, Translations.get("msgbox_missing_info_title"), Translations.get("worker_empty_text_error")); return

        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker') 

        self.is_typing_active = True
        self._update_autotyper_controls_state() 
        self.status_label.setText(Translations.get("status_preparing", hotkey_name=self.current_hotkey_name)); QApplication.processEvents() 

        self.autotyper_thread = QThread(self)
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
        if not self.is_typing_active: self._update_autotyper_controls_state(); return 
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        self.btn_stop.setEnabled(False); self.status_label.setText(Translations.get("status_requesting_stop")) 

    def _update_autotyper_controls_state(self):
        
        is_idle = not self.is_typing_active and self.is_setting_hotkey_type == 0

        self.btn_start.setEnabled(is_idle)
        self.btn_start.setText(Translations.get("button_start_loading") if self.is_typing_active else Translations.get("button_start", hotkey_name=self.current_hotkey_name))
        self.btn_stop.setEnabled(self.is_typing_active) 
        self.btn_set_hotkey.setEnabled(is_idle) 

        self.entry_text.setEnabled(is_idle)
        self.spin_interval.setEnabled(is_idle)
        self.spin_repetitions.setEnabled(is_idle)

    @Slot(str)
    def update_status_label(self, message): self.status_label.setText(message)

    @Slot(str)
    def show_error_message_box(self, message):
        QMessageBox.critical(self, Translations.get("msgbox_autotyper_error_title"), message)
        self._reset_typing_state_and_ui(error_occurred=True) 

    def _reset_typing_state_and_ui(self, error_occurred=False):
        
        if not self.is_typing_active and self.autotyper_worker is None and self.autotyper_thread is None:
             
             if error_occurred and Translations.get("msgbox_autotyper_error_title") not in self.status_label.text() and " (Lỗi)" not in self.status_label.text(): 
                self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)")
             return

        was_typing = self.is_typing_active 
        self.is_typing_active = False
        self._update_autotyper_controls_state() 

        if error_occurred:
            self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)") 
        else: 
            
            error_suffix_vi = " (Lỗi)" 
            requesting_stop_text = Translations.get("status_requesting_stop")
            current_text = self.status_label.text()
            if was_typing and not current_text.endswith(error_suffix_vi) and current_text != requesting_stop_text:
                 self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name))

        
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit() 
            


    @Slot()
    def _handle_autotyper_worker_finished(self): 
        self._reset_typing_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_autotyper_thread_finished(self): 
        self.autotyper_worker = None 
        if self.autotyper_thread: 
            self.autotyper_thread.deleteLater() 
            self.autotyper_thread = None

        
        current_text = self.status_label.text()
        error_suffix_vi = " (Lỗi)"
        if not self.is_typing_active and not current_text.endswith(error_suffix_vi) and Translations.get("status_requesting_stop") not in current_text:
             self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))


    
    @Slot(int)
    def _prompt_for_new_hotkey_generic(self, hotkey_type_flag):
        
        if self.is_typing_active or self.is_recording or self.is_playing_recording:
            
            return

        
        if self.is_setting_hotkey_type == hotkey_type_flag:
            if self.single_key_listener_worker:
                self.single_key_listener_worker.cancel_current_listening_operation()
            
            return

        
        if self.is_setting_hotkey_type != 0:
            QMessageBox.warning(self, Translations.get("msgbox_error_set_hotkey_title"), "Đang trong quá trình cài đặt một hotkey khác. Vui lòng hoàn tất hoặc hủy thao tác đó trước.") 
            return

        self.is_setting_hotkey_type = hotkey_type_flag 
        self._update_set_hotkey_button_text(hotkey_type_flag, Translations.get("button_setting_hotkey_wait")) 
        self._set_controls_enabled_for_hotkey_setting(False) 

        
        if self.single_key_listener_worker:
            
            
            self.single_key_listener_worker.activate_listener_for_hotkey_type(hotkey_type_flag)

    def _update_set_hotkey_button_text(self, hotkey_type, text):
        if hotkey_type == self.SETTING_MAIN_HOTKEY: self.btn_set_hotkey.setText(text)
        elif hotkey_type == self.SETTING_START_RECORD_HOTKEY: self.btn_set_start_record_hotkey.setText(text)
        elif hotkey_type == self.SETTING_PLAY_RECORD_HOTKEY: self.btn_set_play_record_hotkey.setText(text)

    def _set_controls_enabled_for_hotkey_setting(self, enabled):
        
        self.btn_start.setEnabled(enabled)
        self.entry_text.setEnabled(enabled); self.spin_interval.setEnabled(enabled); self.spin_repetitions.setEnabled(enabled)
        
        self.btn_set_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_MAIN_HOTKEY else (not self.is_setting_hotkey_type or enabled))

        
        self.btn_start_record.setEnabled(enabled)
        self.btn_play_record.setEnabled(enabled)
        self.btn_clear_record.setEnabled(enabled)
        self.spin_record_repetitions.setEnabled(enabled) 
        self.btn_set_start_record_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_START_RECORD_HOTKEY else (not self.is_setting_hotkey_type or enabled))
        self.btn_set_play_record_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_PLAY_RECORD_HOTKEY else (not self.is_setting_hotkey_type or enabled))

        
        self.custom_title_bar.btn_toggle_mode.setEnabled(enabled)


    @Slot(int, object, str)
    def _handle_new_hotkey_captured_generic(self, hotkey_type_captured, key_obj, key_name):
        
        if self.is_setting_hotkey_type != hotkey_type_captured:
            return

        conflict_detected = False
        conflicting_action_description = ""

        
        if hotkey_type_captured != self.SETTING_MAIN_HOTKEY and \
           self.current_hotkey and key_obj == self.current_hotkey:
            conflict_detected = True
            conflicting_action_description = Translations.get("action_description_autotyper")

        
        if not conflict_detected and \
           hotkey_type_captured != self.SETTING_START_RECORD_HOTKEY and \
           self.current_start_record_hotkey and key_obj == self.current_start_record_hotkey:
            conflict_detected = True
            conflicting_action_description = Translations.get("action_description_record")

        
        if not conflict_detected and \
           hotkey_type_captured != self.SETTING_PLAY_RECORD_HOTKEY and \
           self.current_play_record_hotkey and key_obj == self.current_play_record_hotkey:
            conflict_detected = True
            conflicting_action_description = Translations.get("action_description_play")

        if conflict_detected:
            error_msg = Translations.get("msgbox_hotkey_conflict_text",
                                         new_hotkey_name=key_name,
                                         action_description=conflicting_action_description)
            QMessageBox.warning(self,
                                Translations.get("msgbox_hotkey_conflict_title"),
                                error_msg)
            
            return

        
        new_hotkey_name_trans = Translations.get("msgbox_hotkey_set_text", new_hotkey_name=key_name)
        QMessageBox.information(self, Translations.get("msgbox_hotkey_set_title"), new_hotkey_name_trans)

        
        if hotkey_type_captured == self.SETTING_MAIN_HOTKEY:
            self.current_hotkey = key_obj; self.current_hotkey_name = key_name
            self.lbl_current_hotkey_value.setText(key_name)
            if self.view_stack.currentWidget() == self.autotyper_page: 
                self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=key_name))
            self.btn_start.setText(Translations.get("button_start", hotkey_name=key_name)) 
            if not self.is_typing_active : self.status_label.setText(Translations.get("status_ready", hotkey_name=key_name)) 
            self.init_main_hotkey_listener() 
        elif hotkey_type_captured == self.SETTING_START_RECORD_HOTKEY:
            self.current_start_record_hotkey = key_obj; self.current_start_record_hotkey_name = key_name
            self.lbl_current_start_record_hotkey_value.setText(key_name)
            self.btn_start_record.setText(Translations.get("button_start_recording", hotkey_name=key_name))
            if not self.is_recording and not self.is_playing_recording: self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=key_name))
            self.init_start_record_hotkey_listener()
        elif hotkey_type_captured == self.SETTING_PLAY_RECORD_HOTKEY:
            self.current_play_record_hotkey = key_obj; self.current_play_record_hotkey_name = key_name
            self.lbl_current_play_record_hotkey_value.setText(key_name)
            self.btn_play_record.setText(Translations.get("button_play_recording", hotkey_name=key_name))
            if not self.is_playing_recording and not self.is_recording and len(self.recorded_events) > 0: self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=key_name))
            self.init_play_record_hotkey_listener()
        

    @Slot(int, str)
    def _handle_set_hotkey_error_generic(self, hotkey_type_errored, error_message):
        if self.is_setting_hotkey_type != hotkey_type_errored: return
        QMessageBox.critical(self, Translations.get("msgbox_error_set_hotkey_title"), error_message)
        

    @Slot(int)
    def _on_single_key_listener_operation_finished_generic(self, hotkey_type_finished):
        
        if self.is_setting_hotkey_type == hotkey_type_finished: 
            self._finish_set_hotkey_process(hotkey_type_finished)


    def _finish_set_hotkey_process(self, hotkey_type_processed):
        
        if self.is_setting_hotkey_type != hotkey_type_processed:
            return

        
        original_text_for_button = ""
        if hotkey_type_processed == self.SETTING_MAIN_HOTKEY:
            original_text_for_button = Translations.get("button_set_hotkey")
        elif hotkey_type_processed == self.SETTING_START_RECORD_HOTKEY:
            original_text_for_button = Translations.get("button_set_start_record_hotkey")
        elif hotkey_type_processed == self.SETTING_PLAY_RECORD_HOTKEY:
            original_text_for_button = Translations.get("button_set_play_record_hotkey")

        self.is_setting_hotkey_type = 0 
        self._update_set_hotkey_button_text(hotkey_type_processed, original_text_for_button)
        self._set_controls_enabled_for_hotkey_setting(True) 


    
    @Slot()
    def toggle_recording_process(self):
        self._ensure_not_setting_hotkey_on_action_toggle()

        if self.is_typing_active: 
            # Khong hien msgbox khi player gay ra, hoac khi dang go
            return
        
        if self.is_playing_recording: 
            # Khong hien msgbox loi khi player gay ra hotkey nay. Player tiep tuc.
            # Player se tu xu ly (vd: dung lai neu hotkey la hotkey dung player)
            # hoac bo qua neu hotkey khong phai hotkey cua player
            return

        if self.view_stack.currentWidget() != self.recorder_page: return

        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self.is_recording: return 
        self.is_recording = True

        self.recorded_events.clear() 
        self._update_recorded_events_table() 
        self._update_recorder_controls_state() 

        self._cleanup_thread_worker('recorder_thread', 'recorder_worker')
        self.recorder_thread = QThread(self)
        
        self.recorder_worker = KeyboardRecorderWorker(self.current_start_record_hotkey, self.current_start_record_hotkey_name)
        self.recorder_worker.moveToThread(self.recorder_thread)

        self.recorder_worker.key_event_recorded.connect(self._add_recorded_event)
        self.recorder_worker.recording_status_update.connect(self._update_recorder_status_label) 
        self.recorder_worker.recording_finished.connect(self._handle_recorder_worker_finished)

        self.recorder_thread.started.connect(self.recorder_worker.run)
        self.recorder_thread.finished.connect(self.recorder_worker.deleteLater)
        self.recorder_thread.finished.connect(self._handle_recorder_thread_finished)
        self.recorder_thread.start()

    def _stop_recording(self):
        if not self.is_recording or not self.recorder_worker: return
        self.recorder_worker.request_stop() 
        

    @Slot(object, str, str, float)
    def _add_recorded_event(self, key_obj, key_name_display, action_canonical, delay_ms):
        
        self.recorded_events.append((key_obj, key_name_display, action_canonical, delay_ms))
        self._update_recorded_events_table() 

    @Slot(str)
    def _update_recorder_status_label(self, status):
        self.recorder_status_label.setText(status)

        
        is_countdown_status = False
        
        current_lang_countdown_prefix = Translations.get("status_recorder_countdown", seconds="").split("...")[0] 
        
        

        if status.startswith(current_lang_countdown_prefix.strip()) and "..." in status:
            is_countdown_status = True

        if is_countdown_status:
            if not self.countdown_overlay:
                self.countdown_overlay = CountdownOverlay(None) 
            
            try:
                
                countdown_text_content = status.replace(current_lang_countdown_prefix.strip(), "").strip()
                self.countdown_overlay.setText(countdown_text_content) 
            except Exception: 
                self.countdown_overlay.setText(status)

            if not self.countdown_overlay.isVisible():
                 self.countdown_overlay.show()
                 self.countdown_overlay.activateWindow() 
                 self.countdown_overlay.raise_()
        else: 
            if self.countdown_overlay and self.countdown_overlay.isVisible():
                self.countdown_overlay.hide()


    def _reset_recorder_state_and_ui(self):
        
        if not self.is_recording and self.recorder_worker is None and self.recorder_thread is None:
            return

        was_recording = self.is_recording 
        self.is_recording = False
        self._update_recorder_controls_state() 

        if was_recording: 
            self.recorder_status_label.setText(Translations.get("status_recorder_stopped", hotkey_name=self.current_start_record_hotkey_name))

        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.quit()

        if self.countdown_overlay and self.countdown_overlay.isVisible(): 
            self.countdown_overlay.hide()

    @Slot()
    def _handle_recorder_worker_finished(self):
        self._reset_recorder_state_and_ui()

    @Slot()
    def _handle_recorder_thread_finished(self):
        self.recorder_worker = None
        if self.recorder_thread:
            self.recorder_thread.deleteLater()
            self.recorder_thread = None

        
        
        if not self.is_recording and not self.is_playing_recording: 
            if len(self.recorded_events) > 0:
                 self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
            else:
                 self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

        if self.countdown_overlay and self.countdown_overlay.isVisible(): 
            self.countdown_overlay.hide()


    @Slot()
    def toggle_playing_process(self):
        self._ensure_not_setting_hotkey_on_action_toggle() 

        if self.is_typing_active or self.is_recording: # Neu dang go hoac ghi
            relevant_action = Translations.get("action_description_autotyper") if self.is_typing_active else Translations.get("action_description_record")
            
            status_running_text_part_key = "worker_status_running" if self.is_typing_active else "status_recorder_recording"
            status_running_text_part = Translations.get(status_running_text_part_key, count="", rep_text="", hotkey_name="", hotkey_display_name="").split("...")[0].strip()
            if not status_running_text_part: status_running_text_part = Translations.get("button_stop").lower()


            QMessageBox.information(self,
                                    Translations.get("label_record_play_group"),
                                    Translations.get("msgbox_hotkey_conflict_text",
                                                     new_hotkey_name=self.current_play_record_hotkey_name,
                                                     action_description=f"{relevant_action} ({status_running_text_part})"))
            return

        if self.view_stack.currentWidget() != self.recorder_page: return

        if self.is_playing_recording:
            self._stop_playing_recording()
        else:
            self._start_playing_recording()

    def _start_playing_recording(self):
        if self.is_playing_recording: return
        if not self.recorded_events:
            QMessageBox.information(self, Translations.get("msgbox_no_recording_title"), Translations.get("msgbox_no_recording_text"))
            return
        
        record_repetitions = self.spin_record_repetitions.value()

        self.is_playing_recording = True
        self._update_recorder_controls_state() 

        self._cleanup_thread_worker('player_thread', 'player_worker')
        self.player_thread = QThread(self)

        
        
        events_for_worker = [(evt[0], evt[2], evt[3]) for evt in self.recorded_events]


        self.player_worker = RecordedPlayerWorker(events_for_worker, record_repetitions, self.current_play_record_hotkey_name)
        self.player_worker.moveToThread(self.player_thread)

        self.player_worker.update_status_signal.connect(self._update_recorder_status_label)
        self.player_worker.error_signal.connect(self._handle_player_error)
        self.player_worker.playing_finished_signal.connect(self._handle_player_worker_finished)

        self.player_thread.started.connect(self.player_worker.run)
        self.player_thread.finished.connect(self.player_worker.deleteLater)
        self.player_thread.finished.connect(self._handle_player_thread_finished)
        self.player_thread.start()

    def _stop_playing_recording(self):
        if not self.is_playing_recording or not self.player_worker: return
        self.player_worker.request_stop() 

    def _reset_player_state_and_ui(self, error_occurred=False):
        if not self.is_playing_recording and self.player_worker is None and self.player_thread is None:
            if error_occurred and Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                 self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
            return

        was_playing = self.is_playing_recording
        self.is_playing_recording = False
        self._update_recorder_controls_state() 

        if error_occurred:
            self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
        else: 
            if was_playing and Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                self.recorder_status_label.setText(Translations.get("status_player_stopped", hotkey_name=self.current_play_record_hotkey_name))

        if self.player_thread and self.player_thread.isRunning():
            self.player_thread.quit()


    @Slot(str)
    def _handle_player_error(self, error_message):
        QMessageBox.critical(self, Translations.get("msgbox_autotyper_error_title"), error_message) 
        self._reset_player_state_and_ui(error_occurred=True)

    @Slot()
    def _handle_player_worker_finished(self): 
        self._reset_player_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_player_thread_finished(self):
        self.player_worker = None
        if self.player_thread:
            self.player_thread.deleteLater()
            self.player_thread = None

        
        
        current_text = self.recorder_status_label.text()
        error_prefix_en = Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0]

        if not self.is_playing_recording and not self.is_recording: 
            if error_prefix_en not in current_text: 
                if len(self.recorded_events) > 0:
                    self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
                else: 
                    self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))
            

    def _update_recorder_controls_state(self):
        
        is_idle_for_hotkey_setting = not self.is_recording and not self.is_playing_recording and self.is_setting_hotkey_type == 0

        
        self.btn_start_record.setEnabled(not self.is_playing_recording and self.is_setting_hotkey_type == 0) 
        self.btn_start_record.setText(
            Translations.get("button_stop_recording", hotkey_name=self.current_start_record_hotkey_name) if self.is_recording
            else Translations.get("button_start_recording", hotkey_name=self.current_start_record_hotkey_name)
        )

        
        self.btn_play_record.setEnabled(not self.is_recording and self.is_setting_hotkey_type == 0 and len(self.recorded_events) > 0) 
        self.btn_play_record.setText(
            Translations.get("button_stop_playing_recording", hotkey_name=self.current_play_record_hotkey_name) if self.is_playing_recording
            else Translations.get("button_play_recording", hotkey_name=self.current_play_record_hotkey_name)
        )
        
        
        self.spin_record_repetitions.setEnabled(not self.is_recording and not self.is_playing_recording and self.is_setting_hotkey_type == 0)


        
        self.btn_clear_record.setEnabled(is_idle_for_hotkey_setting and len(self.recorded_events) > 0) 
        self.btn_set_start_record_hotkey.setEnabled(is_idle_for_hotkey_setting if self.is_setting_hotkey_type != self.SETTING_START_RECORD_HOTKEY else True)
        self.btn_set_play_record_hotkey.setEnabled(is_idle_for_hotkey_setting if self.is_setting_hotkey_type != self.SETTING_PLAY_RECORD_HOTKEY else True)
        self.custom_title_bar.btn_toggle_mode.setEnabled(is_idle_for_hotkey_setting) 

    def _update_recorded_events_table(self):
        self.recorded_events_table.setRowCount(0) 
        for _key_obj, key_name_display, action_canonical, delay_ms in self.recorded_events:
            row_pos = self.recorded_events_table.rowCount()
            self.recorded_events_table.insertRow(row_pos)
            self.recorded_events_table.setItem(row_pos, 0, QTableWidgetItem(key_name_display))
            
            action_display = Translations.get(f"action_{action_canonical}_display")
            self.recorded_events_table.setItem(row_pos, 1, QTableWidgetItem(action_display))
            self.recorded_events_table.setItem(row_pos, 2, QTableWidgetItem(f"{delay_ms:.2f}")) 
        self.recorded_events_table.scrollToBottom() 
        self._update_recorder_controls_state() 

    @Slot()
    def _clear_recorded_events(self):
        if not self.recorded_events: return 
        reply = QMessageBox.question(self,
                                     Translations.get("msgbox_confirm_clear_recording_title"),
                                     Translations.get("msgbox_confirm_clear_recording_text"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) 
        if reply == QMessageBox.StandardButton.Yes:
            self.recorded_events.clear()
            self._update_recorded_events_table() 
            if not self.is_recording and not self.is_playing_recording: 
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

    
    def _serialize_key(self, key_obj):
        if isinstance(key_obj, PynputKey): 
            return {"type": "special", "value": key_obj.name}
        elif isinstance(key_obj, KeyCode): 
            
            if key_obj.char is not None:
                return {"type": "keycode_char", "value": key_obj.char}
            
            elif hasattr(key_obj, 'vk'):
                 return {"type": "keycode_vk", "value": key_obj.vk}
        elif isinstance(key_obj, str): 
            return {"type": "char_str", "value": key_obj}
        return None 

    def _deserialize_key(self, key_data):
        if not key_data or "type" not in key_data or "value" not in key_data:
            return None
        key_type = key_data["type"]
        key_value = key_data["value"]
        try:
            if key_type == "special":
                return getattr(PynputKey, key_value)
            elif key_type == "keycode_char":
                return KeyCode.from_char(key_value)
            elif key_type == "keycode_vk":
                 return KeyCode.from_vk(key_value)
            elif key_type == "char_str": 
                return KeyCode.from_char(key_value)
        except AttributeError: 
            
            return None
        except Exception as e: 
            
            return None
        return None


    def _load_settings(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                
                lang_code = settings.get("language", Translations.LANG_VI)
                Translations.set_language(lang_code)
                
                if hasattr(self, 'custom_title_bar'): 
                    cb_idx = self.custom_title_bar.lang_combo.findData(lang_code)
                    if cb_idx != -1: self.custom_title_bar.lang_combo.setCurrentIndex(cb_idx)


                
                geom_rect_array = settings.get("window_geometry")
                if geom_rect_array: self.setGeometry(QRect(*geom_rect_array))
                if settings.get("window_maximized", False): self.showMaximized()


                
                self.entry_text.setText(settings.get("autotyper_text", ""))
                self.spin_interval.setValue(settings.get("autotyper_interval", 1000))
                self.spin_repetitions.setValue(settings.get("autotyper_repetitions", 0))

                hk_data = settings.get("autotyper_hotkey")
                deserialized_hk = self._deserialize_key(hk_data)
                if deserialized_hk:
                    self.current_hotkey = deserialized_hk
                    self.current_hotkey_name = get_pynput_key_display_name(self.current_hotkey)
                


                
                rec_hk_data = settings.get("recorder_start_hotkey")
                deserialized_rec_hk = self._deserialize_key(rec_hk_data)
                if deserialized_rec_hk:
                    self.current_start_record_hotkey = deserialized_rec_hk
                    self.current_start_record_hotkey_name = get_pynput_key_display_name(self.current_start_record_hotkey)

                play_hk_data = settings.get("recorder_play_hotkey")
                deserialized_play_hk = self._deserialize_key(play_hk_data)
                if deserialized_play_hk:
                    self.current_play_record_hotkey = deserialized_play_hk
                    self.current_play_record_hotkey_name = get_pynput_key_display_name(self.current_play_record_hotkey)

                
                self.spin_record_repetitions.setValue(settings.get("recorder_repetitions", self.DEFAULT_RECORD_REPETITIONS))


                
                self.recorded_events = []
                saved_events = settings.get("recorded_events_v2", []) 
                for sev in saved_events:
                    key_obj_s = sev.get("key_obj_s")
                    key_obj = self._deserialize_key(key_obj_s)
                    if key_obj:
                        
                        key_name_d = sev.get("key_name_display", get_pynput_key_display_name(key_obj))
                        action_c = sev.get("action_canonical")
                        delay_ms = sev.get("delay_ms")
                        if action_c and delay_ms is not None:
                            self.recorded_events.append((key_obj, key_name_d, action_c, delay_ms))
                self._update_recorded_events_table()


                
                is_advanced_mode = settings.get("advanced_mode_active", False)
                if hasattr(self, 'view_stack'): 
                     self._toggle_view_mode(is_advanced_mode, from_load=True)

            else: 
                print(Translations.get("config_file_not_found", filepath=self.config_path))
                
        except Exception as e:
            print(Translations.get("config_loaded_error", filepath=self.config_path, error=str(e)))
            

        
        if hasattr(self, 'custom_title_bar'): 
            self._retranslate_ui()
            self._update_autotyper_controls_state()
            self._update_recorder_controls_state()

    def _save_settings(self):
        settings = {
            "language": Translations.current_lang,
            "window_geometry": self.geometry().getRect() if not self.isMaximized() else self.normalGeometry().getRect(),
            "window_maximized": self.isMaximized(),

            "autotyper_text": self.entry_text.text(),
            "autotyper_interval": self.spin_interval.value(),
            "autotyper_repetitions": self.spin_repetitions.value(),
            "autotyper_hotkey": self._serialize_key(self.current_hotkey),

            "recorder_start_hotkey": self._serialize_key(self.current_start_record_hotkey),
            "recorder_play_hotkey": self._serialize_key(self.current_play_record_hotkey),
            "recorder_repetitions": self.spin_record_repetitions.value(), 

            "advanced_mode_active": self.view_stack.currentWidget() == self.recorder_page,
        }

        
        saved_events_data = []
        for key_obj, key_name_d, action_c, delay_ms in self.recorded_events:
            key_obj_s = self._serialize_key(key_obj)
            if key_obj_s: 
                saved_events_data.append({
                    "key_obj_s": key_obj_s,
                    "key_name_display": key_name_d, 
                    "action_canonical": action_c,
                    "delay_ms": delay_ms
                })
        settings["recorded_events_v2"] = saved_events_data


        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            
        except Exception as e:
            print(Translations.get("config_saved_error", filepath=self.config_path, error=str(e)))
            


    def closeEvent(self, event):
        self._save_settings() 

        
        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker')
        self.autotyper_worker = None; self.autotyper_thread = None 

        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker')
        self.hotkey_listener_worker = None; self.hotkey_listener_thread = None

        
        if self.single_key_listener_worker:
            self.single_key_listener_worker.request_stop_worker_thread() 
        if self.single_key_listener_thread: 
            self.single_key_listener_thread.quit()
            if not self.single_key_listener_thread.wait(1500): 
                
                self.single_key_listener_thread.terminate()
                self.single_key_listener_thread.wait()
        self.single_key_listener_worker = None; self.single_key_listener_thread = None


        self._cleanup_thread_worker('recorder_thread', 'recorder_worker')
        self.recorder_worker = None; self.recorder_thread = None

        self._cleanup_thread_worker('player_thread', 'player_worker')
        self.player_worker = None; self.player_thread = None

        self._cleanup_thread_worker('start_record_hotkey_listener_thread', 'start_record_hotkey_listener_worker')
        self.start_record_hotkey_listener_worker = None; self.start_record_hotkey_listener_thread = None

        self._cleanup_thread_worker('play_record_hotkey_listener_thread', 'play_record_hotkey_listener_worker')
        self.play_record_hotkey_listener_worker = None; self.play_record_hotkey_listener_thread = None


        if self.countdown_overlay: 
            self.countdown_overlay.close()
            self.countdown_overlay = None

        event.accept()