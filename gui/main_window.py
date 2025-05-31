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
            Qt.WindowType.Tool | # Important for not stealing focus as much
            Qt.WindowType.X11BypassWindowManagerHint # For Linux, helps with focus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating) # Khong kich hoat cua so khi hien

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.label = QLabel("...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.75);
                color: white;
                font-size: 26px; /* Font to, de doc */
                font-weight: bold;
                padding: 18px 28px; /* Padding rong rai */
                border-radius: 12px; /* Bo tron goc */
            }
        """)
        layout.addWidget(self.label)
        self.setFixedSize(self.label.sizeHint() + QSize(10,10)) # Them chut cho dep

    def setText(self, text):
        self.label.setText(text)
        self.adjustSize() # Tu dieu chinh kt
        # Goi centerOnScreen sau khi adjustSize de co kich thuoc dung
        target_screen = self.screen() # Neu parent la None, self.screen() co the la None
        if not target_screen and QApplication.instance(): # QApplication.instance() de tranh loi neu app chua co
            target_screen = QApplication.primaryScreen()
        self.centerOnScreen(target_screen)


    def centerOnScreen(self, target_screen=None):
        # Dam bao co screen object truoc khi truy cap
        current_screen_to_use = target_screen
        if not current_screen_to_use: # Neu target_screen ko duoc truyen vao
            current_screen_to_use = self.screen() # Thu lay screen cua widget nay
            if not current_screen_to_use and QApplication.instance():
                current_screen_to_use = QApplication.primaryScreen() # Fallback to primary screen

        if current_screen_to_use: # Neu van co screen (primaryScreen luon co neu app chay)
            screen_geometry = current_screen_to_use.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 3 # Hien cao hon chut
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)

class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    DEFAULT_START_RECORD_HOTKEY = PynputKey.f10
    DEFAULT_PLAY_RECORD_HOTKEY = PynputKey.f11
    DEFAULT_RECORD_REPETITIONS = 1 # Mac dinh phat 1 lan

    RESIZE_MARGIN = 10
    NO_EDGE, TOP_EDGE, BOTTOM_EDGE, LEFT_EDGE, RIGHT_EDGE = 0x0, 0x1, 0x2, 0x4, 0x8
    TOP_LEFT_CORNER, TOP_RIGHT_CORNER = TOP_EDGE | LEFT_EDGE, TOP_EDGE | RIGHT_EDGE
    BOTTOM_LEFT_CORNER, BOTTOM_RIGHT_CORNER = BOTTOM_EDGE | LEFT_EDGE, BOTTOM_EDGE | RIGHT_EDGE

    SETTING_MAIN_HOTKEY = 1
    SETTING_START_RECORD_HOTKEY = 2
    SETTING_PLAY_RECORD_HOTKEY = 3

    CONFIG_FILE_NAME = "autokeyboard_config.json" # Ten file config

    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.config_path = os.path.join(self.base_path, self.CONFIG_FILE_NAME) # Duong dan file config
        self.background_image_filename = "stellar.jpg"
        self.background_image_path = os.path.join(self.base_path, "assets", self.background_image_filename).replace("\\", "/")

        # Defaults, se bi ghi de boi config neu co
        Translations.set_language(Translations.LANG_VI)

        self.DEFAULT_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_HOTKEY)
        self.DEFAULT_START_RECORD_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_START_RECORD_HOTKEY)
        self.DEFAULT_PLAY_RECORD_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_PLAY_RECORD_HOTKEY)

        self.setMinimumSize(700, 600)
        self.resize(850, 700) # Kich thuoc mac dinh

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
        self.recorded_events = [] # Luu (key_obj, key_name_display, action_canonical, delay_ms)

        self.is_setting_hotkey_type = 0 # 0: none, 1: main, 2: record, 3: play

        self.single_key_listener_thread = QThread(self)
        self.single_key_listener_worker = SingleKeyListenerWorker()
        self.single_key_listener_worker.moveToThread(self.single_key_listener_thread)
        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured_generic)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error_generic)
        self.single_key_listener_worker.listener_operation_finished_signal.connect(self._on_single_key_listener_operation_finished_generic)
        self.single_key_listener_thread.started.connect(self.single_key_listener_worker.run)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_worker.deleteLater) # quan ly memory
        self.single_key_listener_thread.finished.connect(self.single_key_listener_thread.deleteLater) # quan ly memory
        self.single_key_listener_thread.start()

        self.original_pixmap = QPixmap(self.background_image_path)
        self._is_dragging = False; self._drag_start_pos = QPoint()
        self._is_resizing = False; self._resize_edge = self.NO_EDGE
        self._resize_start_mouse_pos = QPoint(); self._resize_start_window_geometry = QRect()

        self.countdown_overlay = None # Khoi tao overlay

        # Init UI truoc khi load settings de UI co san cho settings
        self.init_ui_elements()
        self._load_settings() # Load settings (bao gom lang, geometry,...)
        self.apply_styles() # Apply style sau khi co the da load lang

        # Init listeners sau khi hotkeys da duoc load hoac set default
        self.init_main_hotkey_listener()
        self.init_start_record_hotkey_listener()
        self.init_play_record_hotkey_listener()

        self._retranslate_ui() # Goi sau cung de dam bao tat ca text dung
        self.setMouseTracking(True)

    def init_ui_elements(self):
        self.main_container_widget = QWidget(); self.main_container_widget.setObjectName("mainContainerWidget")
        self.setCentralWidget(self.main_container_widget)
        overall_layout = QVBoxLayout(self.main_container_widget); overall_layout.setContentsMargins(0,0,0,0); overall_layout.setSpacing(0)

        # CustomTitleBar se lay current_lang tu Translations class
        self.custom_title_bar = CustomTitleBar(self, current_lang_code=Translations.current_lang)
        self.custom_title_bar.language_changed_signal.connect(self._handle_language_change)
        self.custom_title_bar.toggle_advanced_mode_signal.connect(self._toggle_view_mode)
        overall_layout.addWidget(self.custom_title_bar)

        # Main content area
        main_area_widget = QWidget(); main_area_layout = QVBoxLayout(main_area_widget); main_area_layout.setContentsMargins(0,0,0,0); main_area_layout.setSpacing(0)

        # Stacked widget for different views (Autotyper, Recorder)
        self.view_stack = QStackedWidget()
        self.autotyper_page = self._create_autotyper_page_widget()
        self.view_stack.addWidget(self.autotyper_page)
        self.recorder_page = self._create_recorder_page_widget()
        self.view_stack.addWidget(self.recorder_page)

        # Layout cho phep background va view_stack chong len nhau
        main_area_stacked_layout = QStackedLayout(); main_area_stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.background_label = QLabel(); self.background_label.setObjectName("backgroundLabel")
        if self.original_pixmap.isNull(): self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.background_label.setStyleSheet("background-color: rgb(10, 12, 22); color: white;") # Fallback
        else: self._update_background_pixmap()
        self.background_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored) # De background scale
        main_area_stacked_layout.addWidget(self.background_label) # Add bg truoc
        main_area_stacked_layout.addWidget(self.view_stack) # Add view_stack sau (tren cung)

        main_area_layout.addLayout(main_area_stacked_layout)
        overall_layout.addWidget(main_area_widget)

    def _create_autotyper_page_widget(self):
        page_widget = QWidget(); page_widget.setObjectName("autotyperPageWidget")
        content_layout = QVBoxLayout(page_widget); content_layout.setContentsMargins(30, 15, 30, 20); content_layout.setSpacing(15)

        # Input frame
        input_frame = QFrame(); input_frame.setObjectName("inputFrame")
        self.form_layout = QFormLayout(input_frame); self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows); self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft); self.form_layout.setHorizontalSpacing(10); self.form_layout.setVerticalSpacing(12)
        self.label_for_text_entry = QLabel(); self.entry_text = QLineEdit(); self.entry_text.setObjectName("textInput"); self.form_layout.addRow(self.label_for_text_entry, self.entry_text)
        self.label_for_interval = QLabel(); self.spin_interval = QSpinBox(); self.spin_interval.setRange(1,600000); self.spin_interval.setValue(1000); self.spin_interval.setObjectName("intervalInput"); self.form_layout.addRow(self.label_for_interval, self.spin_interval)
        self.label_for_repetitions = QLabel(); self.spin_repetitions = QSpinBox(); self.spin_repetitions.setRange(0,1000000); self.spin_repetitions.setValue(0); self.spin_repetitions.setObjectName("repetitionsInput"); self.form_layout.addRow(self.label_for_repetitions, self.spin_repetitions)
        content_layout.addWidget(input_frame)

        # Hotkey settings group
        self.autotyper_hotkey_group = QGroupBox(); self.autotyper_hotkey_group.setObjectName("hotkeyGroup")
        hotkey_group_layout = QVBoxLayout(self.autotyper_hotkey_group); hotkey_group_layout.setSpacing(8)
        current_hotkey_layout = QHBoxLayout()
        self.lbl_current_hotkey_static = QLabel() # "Current Hotkey:"
        self.lbl_current_hotkey_value = QLabel(self.current_hotkey_name) # "F9"
        self.lbl_current_hotkey_value.setObjectName("currentHotkeyDisplay")
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_static)
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_value)
        current_hotkey_layout.addStretch()
        hotkey_group_layout.addLayout(current_hotkey_layout)
        self.btn_set_hotkey = QPushButton(); self.btn_set_hotkey.setObjectName("setHotkeyButton"); self.btn_set_hotkey.clicked.connect(lambda: self._prompt_for_new_hotkey_generic(self.SETTING_MAIN_HOTKEY))
        self.btn_set_hotkey.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) # De nut ko gian ra
        hotkey_group_layout.addWidget(self.btn_set_hotkey, 0, Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(self.autotyper_hotkey_group)

        # Start/Stop buttons
        button_layout_container = QWidget(); button_layout = QHBoxLayout(button_layout_container); button_layout.setContentsMargins(0,8,0,0) # Them chut margin top
        self.btn_start = QPushButton(); self.btn_start.setObjectName("startButton"); self.btn_start.clicked.connect(self.toggle_typing_process)
        self.btn_stop = QPushButton(); self.btn_stop.setObjectName("stopButton"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_typing_process)
        button_layout.addStretch(); button_layout.addWidget(self.btn_start); button_layout.addWidget(self.btn_stop); button_layout.addStretch()
        content_layout.addWidget(button_layout_container)

        # Status label
        self.status_label = QLabel(); self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        content_layout.addStretch() # Day moi thu len tren
        return page_widget

    def _create_recorder_page_widget(self):
        page_widget = QWidget(); page_widget.setObjectName("recorderPageWidget")
        content_layout = QVBoxLayout(page_widget); content_layout.setContentsMargins(20, 15, 20, 20); content_layout.setSpacing(12)

        # Hotkey settings group for Record/Play
        self.record_play_hotkey_group = QGroupBox(); self.record_play_hotkey_group.setObjectName("hotkeyGroup")
        record_play_hotkey_layout = QFormLayout(self.record_play_hotkey_group) # QFormLayout cho dep
        record_play_hotkey_layout.setSpacing(10)

        self.lbl_current_start_record_hotkey_static = QLabel()
        start_rec_hotkey_val_layout = QHBoxLayout() # De dat label va button tren 1 hang
        self.lbl_current_start_record_hotkey_value = QLabel(self.current_start_record_hotkey_name)
        self.lbl_current_start_record_hotkey_value.setObjectName("currentHotkeyDisplay")
        self.btn_set_start_record_hotkey = QPushButton()
        self.btn_set_start_record_hotkey.setObjectName("setHotkeyButtonSmall") # Style rieng cho nut nho hon
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

        # Table for recorded events
        self.recorded_events_table = QTableWidget(); self.recorded_events_table.setObjectName("recordedEventsTable")
        self.recorded_events_table.setColumnCount(3) # Key, Action, Delay
        self.recorded_events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Chia deu cot
        self.recorded_events_table.verticalHeader().setVisible(False) # An header doc
        self.recorded_events_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Ko cho edit truc tiep
        self.recorded_events_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Chon ca hang
        content_layout.addWidget(self.recorded_events_table, 1) # Cho table gian ra (stretch factor 1)
        
        # Playback options (Repetitions)
        playback_options_container = QWidget() # Container de can giua
        playback_options_layout = QHBoxLayout(playback_options_container)
        playback_options_layout.setContentsMargins(0, 5, 0, 5) # Chut margin
        self.label_for_record_repetitions = QLabel()
        self.spin_record_repetitions = QSpinBox()
        self.spin_record_repetitions.setRange(0, 1000000) # 0 la vo han
        self.spin_record_repetitions.setValue(self.DEFAULT_RECORD_REPETITIONS) # Mac dinh
        self.spin_record_repetitions.setObjectName("recordRepetitionsInput")
        playback_options_layout.addStretch(1)
        playback_options_layout.addWidget(self.label_for_record_repetitions)
        playback_options_layout.addWidget(self.spin_record_repetitions)
        playback_options_layout.addStretch(1)
        content_layout.addWidget(playback_options_container)


        # Record/Play/Clear buttons
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

        # Status label for recorder/player
        self.recorder_status_label = QLabel(); self.recorder_status_label.setObjectName("statusLabel"); self.recorder_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.recorder_status_label)
        return page_widget

    @Slot(bool)
    def _toggle_view_mode(self, to_advanced_mode, from_load=False): # Them from_load
        current_target_widget = self.recorder_page if to_advanced_mode else self.autotyper_page
        if self.view_stack.currentWidget() != current_target_widget or from_load: # Chi chuyen neu khac hoac dang load
            self.view_stack.setCurrentWidget(current_target_widget)
            self.custom_title_bar.set_mode_button_state(to_advanced_mode) # Dong bo nut tren title bar

        # Cap nhat title va retranslate sau khi chuyen
        if to_advanced_mode:
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group"))
        else:
            self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))

        if not from_load: # Neu la user click thi retranslate, neu la load thi retranslate se dc goi sau
            self._retranslate_ui()


    def _retranslate_ui(self):
        # Update window title and custom title bar text based on current view
        current_widget = self.view_stack.currentWidget()
        if current_widget == self.autotyper_page:
            self.setWindowTitle(Translations.get("window_title")) # Nen la ten app chung
            self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))
        elif current_widget == self.recorder_page:
            self.setWindowTitle(Translations.get("label_record_play_group")) # Nen la ten app chung
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group"))
        self.custom_title_bar.retranslate_ui_texts() # Retranslate title bar (gom ca nut toggle mode)

        # Background error message
        if self.original_pixmap.isNull():
            # Tranh log loi nhieu lan neu ngon ngu ko doi
            if not hasattr(self, "_bg_error_logged") or self._bg_error_logged != Translations.current_lang:
                print(Translations.get("error_loading_background_msg_console", path=self.background_image_path))
                self._bg_error_logged = Translations.current_lang # Luu ngon ngu da log
            self.background_label.setText(Translations.get("error_loading_background_ui"))

        # Autotyper page texts
        self.label_for_text_entry.setText(Translations.get("label_text_key"))
        self.entry_text.setPlaceholderText(Translations.get("text_input_placeholder"))
        self.label_for_interval.setText(Translations.get("label_interval"))
        self.spin_interval.setSuffix(Translations.get("interval_suffix"))
        self.label_for_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_repetitions.setSpecialValueText(Translations.get("repetitions_infinite")) # Text cho gia tri 0
        self.autotyper_hotkey_group.setTitle(Translations.get("label_hotkey_setting_group"))
        self.lbl_current_hotkey_static.setText(Translations.get("label_current_hotkey"))
        self.lbl_current_hotkey_value.setText(self.current_hotkey_name) # Update ten hotkey hien tai

        # Nut set hotkey chinh
        if self.is_setting_hotkey_type == self.SETTING_MAIN_HOTKEY:
            self.btn_set_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_hotkey.setText(Translations.get("button_set_hotkey"))

        # Nut Start/Stop va status label cua Autotyper
        if self.is_typing_active: # Dang go
            self.btn_start.setText(Translations.get("button_start_loading")) # Text "..."
            # Status label se duoc worker cap nhat ("Running...")
        else: # Khong hoat dong (idle, stopped, error)
            self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name))
            # Xac dinh trang thai cho status_label khi idle
            current_status = self.status_label.text() # Lay text hien tai
            # Cac prefix cua trang thai "Ready" va "Stopped" (khong phu thuoc hotkey name)
            ready_status_prefix_en = Translations.get("status_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_status_prefix_en = Translations.get("status_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
            stopped_fully_prefix_en = Translations.get("status_stopped_fully", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]

            # Kiem tra xem status hien tai co phai la mot trong cac trang thai idle/stopped khong
            is_idle_status = any(
                prefix_en in current_status for prefix_en in
                [ready_status_prefix_en, stopped_status_prefix_en, stopped_fully_prefix_en]
            )

            if current_status == Translations.get("status_requesting_stop"): # Neu dang yeu cau dung thi giu nguyen
                pass
            # Neu worker/thread da reset hoan toan (khong con instance)
            elif self.autotyper_worker is None and self.autotyper_thread is None and not self.is_typing_active:
                 self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))
            # Neu la trang thai idle/stopped hoac status rong (moi khoi dong)
            elif not self.is_typing_active and (is_idle_status or not current_status):
                self.status_label.setText(Translations.get("status_ready", hotkey_name=self.current_hotkey_name))
            # Else: giu nguyen status hien tai (vd: error message)
        self.btn_stop.setText(Translations.get("button_stop"))


        # Recorder page texts
        self.record_play_hotkey_group.setTitle(Translations.get("label_record_play_group")) # Group title
        self.lbl_current_start_record_hotkey_static.setText(Translations.get("label_start_record_hotkey"))
        self.lbl_current_start_record_hotkey_value.setText(self.current_start_record_hotkey_name)
        self.lbl_current_play_record_hotkey_static.setText(Translations.get("label_play_record_hotkey"))
        self.lbl_current_play_record_hotkey_value.setText(self.current_play_record_hotkey_name)
        
        # Label va SpinBox cho so lan lap cua recorder
        self.label_for_record_repetitions.setText(Translations.get("label_repetitions"))
        self.spin_record_repetitions.setSpecialValueText(Translations.get("repetitions_infinite"))
        self.spin_record_repetitions.setSuffix("") # Khong can suffix "ms"


        # Nut set hotkey Ghi
        if self.is_setting_hotkey_type == self.SETTING_START_RECORD_HOTKEY:
            self.btn_set_start_record_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_start_record_hotkey.setText(Translations.get("button_set_start_record_hotkey"))

        # Nut set hotkey Phat
        if self.is_setting_hotkey_type == self.SETTING_PLAY_RECORD_HOTKEY:
            self.btn_set_play_record_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_play_record_hotkey.setText(Translations.get("button_set_play_record_hotkey"))

        # Nut Start/Stop Record & Play va status label cua Recorder
        current_recorder_status = self.recorder_status_label.text() # Lay text hien tai
        # Cac prefix trang thai (khong phu thuoc hotkey name)
        recorder_idle_prefix_en = Translations.get("status_recorder_idle", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        recorder_stopped_prefix_en = Translations.get("status_recorder_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_ready_prefix_en = Translations.get("status_player_ready", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_stopped_prefix_en = Translations.get("status_player_stopped", hotkey_name="_", lang=Translations.LANG_EN).split("'_'")[0]
        player_error_prefix_en = Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("! ")[0] # Lay phan truoc "!"

        if self.is_recording:
            self.btn_start_record.setText(Translations.get("button_stop_recording", hotkey_name=self.current_start_record_hotkey_name))
            # Status ("Recording...") se do worker cap nhat
        else: # Khong ghi
            self.btn_start_record.setText(Translations.get("button_start_recording", hotkey_name=self.current_start_record_hotkey_name))
            # Neu khong ghi, khong phat, va status hien tai la idle/stopped (hoac rong) -> set status_recorder_idle
            if not self.is_playing_recording and (not current_recorder_status or \
                any(p in current_recorder_status for p in [recorder_idle_prefix_en, recorder_stopped_prefix_en])) and \
                player_error_prefix_en not in current_recorder_status: # Khong phai loi player
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))


        if self.is_playing_recording:
            self.btn_play_record.setText(Translations.get("button_stop_playing_recording", hotkey_name=self.current_play_record_hotkey_name))
            # Status ("Playing...") se do worker cap nhat
        else: # Khong phat
            self.btn_play_record.setText(Translations.get("button_play_recording", hotkey_name=self.current_play_record_hotkey_name))
            # Neu co ban ghi, khong ghi, khong phat, va status hien tai la ready/stopped/error (hoac rong) -> set status_player_ready
            if len(self.recorded_events) > 0 and not self.is_recording and \
               (not current_recorder_status or any(p in current_recorder_status for p in [player_ready_prefix_en, player_stopped_prefix_en, player_error_prefix_en, recorder_idle_prefix_en, recorder_stopped_prefix_en])):
                if player_error_prefix_en not in current_recorder_status: # Neu khong phai loi, set ready
                     self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
                # Else (la loi player): status da duoc set boi _reset_player_state_and_ui, giu nguyen
            # Neu khong co ban ghi, khong ghi, khong phat, status la idle/rong -> set status_recorder_idle
            elif len(self.recorded_events) == 0 and not self.is_recording and \
                 (not current_recorder_status or any(p in current_recorder_status for p in [recorder_idle_prefix_en, recorder_stopped_prefix_en])) and \
                 player_error_prefix_en not in current_recorder_status : # Khong phai loi player
                     self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))


        self.btn_clear_record.setText(Translations.get("button_clear_recording"))
        self.recorded_events_table.setHorizontalHeaderLabels([
            Translations.get("table_header_key"),
            Translations.get("table_header_action"),
            Translations.get("table_header_delay")
        ])

        # Status mac dinh cho recorder page neu rong
        if not self.recorder_status_label.text() and not self.is_recording and not self.is_playing_recording:
            self.recorder_status_label.setText(Translations.get("recorder_status_label_default"))


    @Slot(str)
    def _handle_language_change(self, lang_code):
        Translations.set_language(lang_code)
        self._retranslate_ui() # Dich lai toan bo UI
        self.apply_styles() # Ap dung lai style (co the font thay doi)

    def apply_styles(self):
        font_family = "Segoe UI, Arial, sans-serif"
        if Translations.current_lang == Translations.LANG_JA:
            font_family = "Meiryo, Segoe UI, Arial, sans-serif" # Font tieng Nhat

        # --- Color Scheme ---
        app_main_container_bg = "rgb(10, 12, 22)"; title_bar_bg = "rgba(15, 18, 30, 0.9)"; title_bar_text_color = "rgb(224, 218, 230)"
        title_bar_button_bg = "transparent"; title_bar_button_hover_bg = "rgba(224, 218, 230, 0.15)"; title_bar_button_pressed_bg = "rgba(224, 218, 230, 0.08)"
        close_button_hover_bg = "rgba(200, 90, 110, 0.75)"; close_button_pressed_bg = "rgba(190, 80, 100, 0.6)"
        input_frame_bg_color = "rgba(20, 24, 40, 0.88)"; input_frame_border_color = "rgba(170, 150, 200, 0.4)"
        text_color = "rgb(238, 235, 245)"; subtext_color = "rgb(175, 170, 185)" # Cho placeholder, label phu
        input_bg_color = "rgba(12, 15, 28, 0.92)"; input_border_color = "rgba(170, 150, 200, 0.55)"
        input_focus_border_color = "rgb(210, 190, 250)"; input_focus_bg_color = "rgba(22, 25, 45, 0.96)"
        button_text_color = text_color; button_bg_color = "rgba(75, 80, 115, 0.92)"; button_border_color = "rgba(210, 190, 250, 0.7)"
        start_button_bg_color = "rgba(96, 125, 199, 0.65)"; start_button_border_color = "rgba(126, 155, 229, 0.85)" # Xanh hon
        start_button_hover_bg = "rgba(116, 145, 219, 0.75)"; start_button_pressed_bg = "rgba(86, 115, 189, 0.6)"; start_button_hover_border_color_val = "rgb(116, 145, 219)"
        stop_button_hover_bg = "rgba(210, 190, 250, 0.6)"; stop_button_pressed_bg = "rgba(210, 190, 250, 0.4)"
        disabled_bg_color = "rgba(60, 63, 90, 0.7)"; disabled_text_color = "rgba(160, 155, 170, 0.75)"; disabled_border_color = "rgba(170, 150, 200, 0.3)"
        status_bg_color = "rgba(20, 24, 40, 0.85)"; status_border_color = "rgba(100, 105, 140, 0.7)"
        msgbox_bg_color = "rgb(20, 22, 40)"; msgbox_text_color = "rgb(230, 225, 235)"; msgbox_button_bg = start_button_bg_color
        msgbox_button_border = start_button_border_color; msgbox_button_hover_bg = start_button_hover_bg
        combo_box_bg = input_bg_color; combo_box_border = input_border_color; combo_box_dropdown_bg = "rgb(25, 28, 48)"; combo_box_dropdown_item_hover_bg = "rgba(96, 125, 199, 0.4)"
        hotkey_group_border_color = input_frame_border_color; hotkey_value_color = "rgb(180, 210, 255)"; # Mau cho ten hotkey
        set_hotkey_button_padding = "6px 15px"; set_hotkey_button_min_width = "120px";
        table_bg = "rgba(15, 18, 30, 0.85)"; table_grid_color = "rgba(100, 105, 140, 0.5)"; table_header_bg = "rgba(25, 30, 50, 0.9)";
        record_button_bg = "rgba(200, 80, 80, 0.7)"; record_button_hover_bg = "rgba(220, 90, 90, 0.8)"; record_button_pressed_bg = "rgba(180, 70, 70, 0.6)"; # Mau do cho record
        play_button_bg = "rgba(80, 150, 200, 0.7)"; play_button_hover_bg = "rgba(90, 170, 220, 0.8)"; play_button_pressed_bg = "rgba(70, 130, 180, 0.6)"; # Mau xanh cho play
        clear_button_bg = "rgba(120, 120, 120, 0.7)"; clear_button_hover_bg = "rgba(140, 140, 140, 0.8)"; clear_button_pressed_bg = "rgba(100, 100, 100, 0.6)"; # Mau xam cho clear
        toggle_mode_button_padding = "5px 12px"; toggle_mode_button_font_size = "9pt";

        qss = f"""
            QMainWindow {{ background: transparent; }} /* Cua so chinh trong suot */
            QWidget#mainContainerWidget {{ background-color: {app_main_container_bg}; border-radius: 10px; }} /* Container chinh co mau nen va bo goc */
            QWidget#autotyperPageWidget, QWidget#recorderPageWidget {{ background-color: transparent; }} /* Cac trang trong suot de thay bg */
            QLabel#backgroundLabel {{ border-radius: 10px; }} /* De bg cung bo tron theo mainContainer */

            /* Custom Title Bar */
            QWidget#customTitleBar {{ background-color: {title_bar_bg}; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid rgba(224, 218, 230, 0.1); }}
            QLabel#titleBarLabel {{ color: {title_bar_text_color}; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; padding-left: 5px; background-color: transparent; }}

            QPushButton#toggleModeButton {{
                background-color: {button_bg_color}; color: {button_text_color};
                border: 1px solid {button_border_color}; border-radius: 6px;
                padding: {toggle_mode_button_padding}; font-family: "{font_family}"; font-size: {toggle_mode_button_font_size};
                min-width: 80px; /* Do rong toi thieu */
            }}
            QPushButton#toggleModeButton:hover {{ background-color: {start_button_hover_bg}; }}
            QPushButton#toggleModeButton:checked {{ background-color: {start_button_bg_color}; }} /* Khi duoc chon (advanced mode) */


            /* Nut Minimize, Maximize, Close */
            QPushButton#minimizeButton, QPushButton#maximizeRestoreButton, QPushButton#closeButton {{
                background-color: {title_bar_button_bg}; border: none; border-radius: 6px;
                color: {subtext_color}; font-family: "{font_family}"; font-size: 12pt; font-weight: bold;
                min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0px;
            }}
            QPushButton#minimizeButton:hover, QPushButton#maximizeRestoreButton:hover {{ background-color: {title_bar_button_hover_bg}; color: {text_color};}}
            QPushButton#closeButton:hover {{ background-color: {close_button_hover_bg}; color: white; }}
            QPushButton#minimizeButton:pressed, QPushButton#maximizeRestoreButton:pressed {{ background-color: {title_bar_button_pressed_bg}; }}
            QPushButton#closeButton:pressed {{ background-color: {close_button_pressed_bg}; }}

            /* ComboBox chon ngon ngu */
            QComboBox#languageComboBox {{
                background-color: {combo_box_bg}; color: {text_color};
                border: 1px solid {combo_box_border}; border-radius: 6px;
                padding: 4px 8px; /* Dieu chinh padding */
                font-family: "{font_family}"; font-size: 9pt; min-height: 20px; /* Chieu cao toi thieu */
            }}
            QComboBox#languageComboBox:hover {{ border-color: {input_focus_border_color}; }}
            QComboBox#languageComboBox::drop-down {{ /* Mui ten dropdown */
                subcontrol-origin: padding; subcontrol-position: top right; width: 18px;
                border-left-width: 1px; border-left-color: {combo_box_border}; border-left-style: solid;
                border-top-right-radius: 6px; border-bottom-right-radius: 6px;
            }}
            QComboBox QAbstractItemView {{ /* Danh sach item khi mo ra */
                background-color: {combo_box_dropdown_bg}; color: {text_color};
                border: 1px solid {input_focus_border_color};
                selection-background-color: {combo_box_dropdown_item_hover_bg}; /* Mau khi hover item */
                padding: 3px; border-radius: 4px; font-family: "{font_family}"; font-size: 9pt;
            }}

            /* Input Frame va GroupBox */
            QFrame#inputFrame {{ background-color: {input_frame_bg_color}; border-radius: 14px; padding: 20px; border: 1.5px solid {input_frame_border_color}; }}
            QGroupBox#hotkeyGroup {{
                font-family: "{font_family}"; font-size: 10pt; color: {text_color};
                border: 1.5px solid {hotkey_group_border_color}; border-radius: 10px;
                margin-top: 8px; /* Day groupbox xuong de title khong de len border frame tren */
                padding: 15px 15px 10px 15px; /* top, right, bottom, left */
                background-color: transparent; /* Cho groupbox trong suot voi inputFrame */
            }}
            QGroupBox#hotkeyGroup::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 5px 0 5px; /* top, right, bottom, left - de title khong sat border */
                left: 10px; /* Dich title sang phai chut */
                color: {subtext_color}; /* Mau title phu hon */
            }}

            /* Labels, LineEdits, SpinBoxes */
            QLabel {{ color: {text_color}; font-family: "{font_family}"; font-size: 10pt; padding: 2px; background-color: transparent; }}
            QLabel#currentHotkeyDisplay {{ color: {hotkey_value_color}; font-weight: bold; font-size: 10pt; padding-left: 5px;}}
            QLineEdit, QSpinBox {{
                background-color: {input_bg_color}; color: {text_color};
                border: 1.5px solid {input_border_color}; border-radius: 9px;
                padding: 9px 12px; font-family: "{font_family}"; font-size: 10pt;
                min-height: 24px; /* Dam bao chieu cao input */
            }}
            QSpinBox#recordRepetitionsInput {{ /* Style rieng cho spinbox lap cua recorder neu can */
                min-width: 70px; /* Cho phep spinbox nay hep hon */
                max-width: 100px;
            }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1.5px solid {input_focus_border_color}; background-color: {input_focus_bg_color}; }}
            QLineEdit::placeholder {{ color: {subtext_color}; }} /* Mau cho placeholder text */

            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border; subcontrol-position: right; /* right center */
                width: 18px; border: 1.5px solid {input_border_color}; border-radius: 5px;
                background-color: {button_bg_color}; margin: 2px 3px 2px 2px; /* top right bottom left */
            }}
            QSpinBox::up-button {{ top: 1px; height: 11px;}} /* Chinh vi tri va kt nut */
            QSpinBox::down-button {{ bottom: 1px; height: 11px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: rgba(95, 100, 135, 0.95); }}
            /* Arrow icons for SpinBox can be set here if needed */

            /* PushButtons (chung) */
            QPushButton {{
                color: {button_text_color}; background-color: {button_bg_color};
                border: 1.5px solid {button_border_color};
                padding: 10px 22px; border-radius: 10px;
                font-family: "{font_family}"; font-size: 10pt; font-weight: bold;
                min-width: 130px; /* Do rong toi thieu cho cac nut chinh */
            }}
            QPushButton#startButton {{ background-color: {start_button_bg_color}; border-color: {start_button_border_color}; }}
            QPushButton#startButton:hover {{ background-color: {start_button_hover_bg}; border-color: {start_button_hover_border_color_val};}}
            QPushButton#startButton:pressed {{ background-color: {start_button_pressed_bg}; }}
            QPushButton#stopButton:hover {{ background-color: {stop_button_hover_bg}; border-color: rgb(210, 190, 250);}}
            QPushButton#stopButton:pressed {{ background-color: {stop_button_pressed_bg}; }}

            QPushButton#setHotkeyButton {{ /* Nut set hotkey chinh */
                padding: {set_hotkey_button_padding}; min-width: {set_hotkey_button_min_width}; max-width: 180px; /* Gioi han do rong */
                font-size: 9pt; /* Font nho hon chut */
            }}
            QPushButton#setHotkeyButtonSmall {{ /* Nut set hotkey cho Record/Play */
                padding: 5px 12px; min-width: 100px; max-width: 150px; font-size: 9pt;
                background-color: {button_bg_color}; border-color: {button_border_color}; /* Giong nut thuong */
            }}
            QPushButton#setHotkeyButtonSmall:hover {{ background-color: {start_button_hover_bg}; }} /* Hover giong nut start */


            /* Nut cho Recorder Page */
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

            /* Status Label */
            QLabel#statusLabel {{
                color: {subtext_color}; background-color: {status_bg_color};
                border: 1px solid {status_border_color}; border-radius: 9px;
                padding: 12px; font-size: 9pt; margin-top: 10px; /* Cach xa nut ben tren */
                font-family: "{font_family}";
            }}

            /* Table for Recorded Events */
            QTableWidget#recordedEventsTable {{
                background-color: {table_bg}; color: {text_color}; gridline-color: {table_grid_color};
                border: 1.5px solid {input_frame_border_color}; border-radius: 8px;
                font-family: "{font_family}"; font-size: 9pt;
            }}
            QHeaderView::section {{ /* Header cua table */
                background-color: {table_header_bg}; color: {text_color};
                padding: 5px; border: 1px solid {table_grid_color}; font-weight: bold;
            }}
            QTableWidget::item {{ padding: 5px; }} /* Padding cho cell */
            QTableWidget::item:selected {{ background-color: {start_button_hover_bg}; color: white; }}


            /* QMessageBox */
            QMessageBox {{ background-color: {msgbox_bg_color}; font-family: "{font_family}"; border-radius: 8px; border: 1px solid {input_frame_border_color}; }}
            QMessageBox QLabel {{ color: {msgbox_text_color}; font-size: 10pt; background-color: transparent; font-family: "{font_family}";}} /* Label trong msgbox */
            QMessageBox QPushButton {{ /* Nut trong msgbox (Yes, No, OK, Cancel) */
                background-color: {msgbox_button_bg}; border-color: {msgbox_button_border}; color: {button_text_color};
                padding: 8px 18px; border-radius: 8px; min-width: 80px; font-family: "{font_family}";
            }}
            QMessageBox QPushButton:hover {{ background-color: {msgbox_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }}
        """
        # Apply global font first
        app_font = QFont("Segoe UI", 10) # Font mac dinh
        if Translations.current_lang == Translations.LANG_JA: app_font = QFont("Meiryo", 9) # Font cho tieng Nhat
        QApplication.setFont(app_font)

        self.setStyleSheet(qss) # Apply stylesheet
        self.update(); # Force repaint
        if self.parent(): self.parent().update() # Force repaint parent if any

    def _update_background_pixmap(self):
        if hasattr(self, 'background_label') and not self.original_pixmap.isNull():
            # Kich thuoc cua vung main area (duoi title bar)
            main_area_height = self.main_container_widget.height() - self.custom_title_bar.height()
            main_area_width = self.main_container_widget.width()

            if main_area_width <= 0 or main_area_height <= 0: return # Tranh loi khi dang init

            target_size_for_bg = QSize(main_area_width, main_area_height)
            # Scale anh nen de vua voi vung main area, giu aspect ratio va cat phan thua
            scaled_pixmap = self.original_pixmap.scaled(
                target_size_for_bg,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, # Gian ra de lap day, giu ti le
                Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event): self._update_background_pixmap(); super().resizeEvent(event)

    # --- Window dragging and resizing without native title bar ---
    def _get_current_resize_edge(self, local_pos: QPoint) -> int:
        edge = self.NO_EDGE; rect = self.rect()
        if local_pos.x() < self.RESIZE_MARGIN: edge |= self.LEFT_EDGE
        if local_pos.x() > rect.width() - self.RESIZE_MARGIN: edge |= self.RIGHT_EDGE
        if local_pos.y() < self.RESIZE_MARGIN: edge |= self.TOP_EDGE # Chi tinh tu duoi custom title bar
        if local_pos.y() > rect.height() - self.RESIZE_MARGIN: edge |= self.BOTTOM_EDGE
        return edge

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint(); global_pos = event.globalPosition().toPoint()

            # Kiem tra resize truoc
            self._resize_edge = self._get_current_resize_edge(local_pos)
            # Chi cho resize neu khong phai vung title bar (ngoai tru TOP_EDGE neu title bar o tren)
            is_on_title_bar_geom = self.custom_title_bar.geometry().contains(local_pos)

            if self._resize_edge != self.NO_EDGE and not (is_on_title_bar_geom and self._resize_edge != self.TOP_EDGE) :
                self._is_resizing = True; self._is_dragging = False
                self._resize_start_mouse_pos = global_pos; self._resize_start_window_geometry = self.geometry()
                event.accept(); return

            # Kiem tra drag neu click vao title bar (va khong phai widget tuong tac tren title bar)
            is_on_interactive_title_widget = False
            # Cac widget tuong tac tren title bar
            interactive_widgets_on_title = self.custom_title_bar.findChildren(QPushButton) + \
                                           [self.custom_title_bar.lang_combo, self.custom_title_bar.btn_toggle_mode]
            for child_widget in interactive_widgets_on_title:
                # Map global mouse pos to child widget's local coordinate system to check
                if child_widget.isVisible() and child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(global_pos)):
                    is_on_interactive_title_widget = True; break

            if is_on_title_bar_geom and not is_on_interactive_title_widget:
                self._is_dragging = True; self._is_resizing = False
                self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                event.accept(); return

        super().mousePressEvent(event) # Xu ly mac dinh cho cac TH khac

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton: # Neu dang giu chuot trai
            if self._is_resizing:
                delta = event.globalPosition().toPoint() - self._resize_start_mouse_pos; start_geom = self._resize_start_window_geometry; new_geom = QRect(start_geom)
                min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
                if self._resize_edge & self.LEFT_EDGE: new_left = start_geom.left() + delta.x(); new_width = max(min_w, start_geom.width() - delta.x()); new_geom.setLeft(start_geom.right() - new_width); new_geom.setWidth(new_width)
                if self._resize_edge & self.RIGHT_EDGE: new_geom.setWidth(max(min_w, start_geom.width() + delta.x()))
                if self._resize_edge & self.TOP_EDGE: new_top = start_geom.top() + delta.y(); new_height = max(min_h, start_geom.height() - delta.y()); new_geom.setTop(start_geom.bottom() - new_height); new_geom.setHeight(new_height)
                if self._resize_edge & self.BOTTOM_EDGE: new_geom.setHeight(max(min_h, start_geom.height() + delta.y()))
                self.setGeometry(new_geom); event.accept(); return
            elif self._is_dragging: self.move(event.globalPosition().toPoint() - self._drag_start_pos); event.accept(); return

        # Cap nhat con tro chuot khi hover vao ria cua so (neu khong dang drag/resize)
        if not (self._is_resizing or self._is_dragging):
            local_pos = event.position().toPoint(); current_hover_edge = self._get_current_resize_edge(local_pos)
            is_on_title_bar_geom = self.custom_title_bar.geometry().contains(local_pos)

            # Kiem tra co phai widget tuong tac tren title bar khong
            is_on_interactive_title_widget = False
            interactive_widgets_on_title = self.custom_title_bar.findChildren(QPushButton) + \
                                           [self.custom_title_bar.lang_combo, self.custom_title_bar.btn_toggle_mode]
            for child_widget in interactive_widgets_on_title:
                if child_widget.isVisible() and child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(event.globalPosition().toPoint())) : is_on_interactive_title_widget = True; break

            if is_on_interactive_title_widget: self.unsetCursor() # Neu la widget tuong tac thi dung cursor mac dinh cua widget
            elif current_hover_edge == self.TOP_LEFT_CORNER or current_hover_edge == self.BOTTOM_RIGHT_CORNER: self.setCursor(Qt.SizeFDiagCursor)
            elif current_hover_edge == self.TOP_RIGHT_CORNER or current_hover_edge == self.BOTTOM_LEFT_CORNER: self.setCursor(Qt.SizeBDiagCursor)
            elif current_hover_edge & self.LEFT_EDGE or current_hover_edge & self.RIGHT_EDGE: self.setCursor(Qt.SizeHorCursor)
            elif current_hover_edge & self.TOP_EDGE or current_hover_edge & self.BOTTOM_EDGE: self.setCursor(Qt.SizeVerCursor)
            else: self.unsetCursor() # Tra ve con tro mac dinh
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            changed_state = False
            if self._is_resizing: self._is_resizing = False; changed_state = True
            if self._is_dragging: self._is_dragging = False; changed_state = True
            if changed_state: self._resize_edge = self.NO_EDGE; self.unsetCursor(); event.accept(); return
        super().mouseReleaseEvent(event)

    # --- Thread and Worker Management ---
    def _cleanup_thread_worker(self, thread_attr, worker_attr):
        worker = getattr(self, worker_attr, None)
        thread = getattr(self, thread_attr, None)

        if worker:
            if hasattr(worker, 'request_stop'): worker.request_stop()
            # worker.deleteLater() # Khong can delete o day, thread finished se lo

        if thread and thread.isRunning():
            thread.quit() # Yeu cau thread thoat vong lap su kien
            if not thread.wait(1000): # Doi toi da 1s
                # print(f"Warning: Thread {thread_attr} did not quit gracefully, terminating.")
                thread.terminate() # Buoc dung neu ko thoat
                thread.wait() # Doi sau khi terminate
        # setattr(self, worker_attr, None) # Xoa ref sau khi thread ket thuc
        # setattr(self, thread_attr, None)


    # --- Hotkey Listener Initialization ---
    def init_main_hotkey_listener(self):
        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker')
        if not self.current_hotkey: return # Neu ko co hotkey thi ko init

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

    # --- Autotyper Logic ---
    @Slot()
    def toggle_typing_process(self):
        if self.is_setting_hotkey_type != 0 or self.view_stack.currentWidget() != self.autotyper_page: return # Neu dang set hotkey hoac ko o page autotyper
        if self.is_typing_active: self.stop_typing_process()
        else: self.start_typing_process()

    def start_typing_process(self):
        if self.is_typing_active or self.is_setting_hotkey_type != 0 : return
        text = self.entry_text.text(); interval = self.spin_interval.value(); repetitions = self.spin_repetitions.value()
        if not text: QMessageBox.warning(self, Translations.get("msgbox_missing_info_title"), Translations.get("worker_empty_text_error")); return

        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker') # Don dep thread cu neu co

        self.is_typing_active = True
        self._update_autotyper_controls_state() # Vo hieu hoa input, nut start, kich hoat nut stop
        self.status_label.setText(Translations.get("status_preparing", hotkey_name=self.current_hotkey_name)); QApplication.processEvents() # Update UI ngay

        self.autotyper_thread = QThread(self)
        self.autotyper_worker = AutoTyperWorker(text, interval, repetitions, self.current_hotkey_name)
        self.autotyper_worker.moveToThread(self.autotyper_thread)
        self.autotyper_worker.update_status_signal.connect(self.update_status_label)
        self.autotyper_worker.error_signal.connect(self.show_error_message_box) # Hien thi loi
        self.autotyper_worker.typing_finished_signal.connect(self._handle_autotyper_worker_finished) # Khi worker xong (ko loi)
        self.autotyper_thread.started.connect(self.autotyper_worker.run)
        self.autotyper_thread.finished.connect(self.autotyper_worker.deleteLater) # Quan ly memory
        self.autotyper_thread.finished.connect(self._handle_autotyper_thread_finished) # Khi thread that su ket thuc
        self.autotyper_thread.start()

    @Slot()
    def stop_typing_process(self):
        if not self.is_typing_active: self._update_autotyper_controls_state(); return # Neu ko chay thi chi update UI
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        self.btn_stop.setEnabled(False); self.status_label.setText(Translations.get("status_requesting_stop")) # Cap nhat UI ngay

    def _update_autotyper_controls_state(self):
        # Trang thai idle la khi khong go phim VA khong dang trong qua trinh set hotkey
        is_idle = not self.is_typing_active and self.is_setting_hotkey_type == 0

        self.btn_start.setEnabled(is_idle)
        self.btn_start.setText(Translations.get("button_start_loading") if self.is_typing_active else Translations.get("button_start", hotkey_name=self.current_hotkey_name))
        self.btn_stop.setEnabled(self.is_typing_active) # Chi enable nut Stop khi dang go
        self.btn_set_hotkey.setEnabled(is_idle) # Chi cho set hotkey khi idle

        self.entry_text.setEnabled(is_idle)
        self.spin_interval.setEnabled(is_idle)
        self.spin_repetitions.setEnabled(is_idle)

    @Slot(str)
    def update_status_label(self, message): self.status_label.setText(message)

    @Slot(str)
    def show_error_message_box(self, message):
        QMessageBox.critical(self, Translations.get("msgbox_autotyper_error_title"), message)
        self._reset_typing_state_and_ui(error_occurred=True) # Reset lai trang thai

    def _reset_typing_state_and_ui(self, error_occurred=False):
        # Neu da reset roi (vd: worker xong -> thread xong) thi ko lam gi
        if not self.is_typing_active and self.autotyper_worker is None and self.autotyper_thread is None:
             # Neu co loi va status chua phai la loi -> them (Loi)
             if error_occurred and Translations.get("msgbox_autotyper_error_title") not in self.status_label.text() and " (Lỗi)" not in self.status_label.text(): # " (Lỗi)" la hardcoded, can xem lai
                self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)")
             return

        was_typing = self.is_typing_active # Luu trang thai truoc khi reset
        self.is_typing_active = False
        self._update_autotyper_controls_state() # Kich hoat lai input, nut start, vo hieu hoa nut stop

        if error_occurred:
            self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name) + " (Lỗi)") # Hardcoded
        else: # Neu xong binh thuong (ko loi)
            # Chi set "Stopped" neu truoc do dang chay hoac chuan bi (khong phai da la loi, hoac dang yeu cau dung)
            error_suffix_vi = " (Lỗi)" # Can lam dong bo voi cac ngon ngu khac
            requesting_stop_text = Translations.get("status_requesting_stop")
            current_text = self.status_label.text()
            if was_typing and not current_text.endswith(error_suffix_vi) and current_text != requesting_stop_text:
                 self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name))

        # Don dep thread neu con chay (co the khong can neu request_stop thanh cong va thread tu ket thuc)
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit() # Yeu cau thoat
            # self.autotyper_thread.wait() # Doi thread ket thuc (co the gay lag UI)


    @Slot()
    def _handle_autotyper_worker_finished(self): # Worker bao xong (ko loi)
        self._reset_typing_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_autotyper_thread_finished(self): # Thread da ket thuc hoan toan
        self.autotyper_worker = None # Xoa ref worker
        if self.autotyper_thread: # tranh loi neu thread da dc gan lai
            self.autotyper_thread.deleteLater() # Schedule for deletion
            self.autotyper_thread = None

        # Set status "Stopped (fully)" neu thuc su da dung va ko co loi
        current_text = self.status_label.text()
        error_suffix_vi = " (Lỗi)"
        if not self.is_typing_active and not current_text.endswith(error_suffix_vi) and Translations.get("status_requesting_stop") not in current_text:
             self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))


    # --- Generic Hotkey Setting Logic ---
    @Slot(int)
    def _prompt_for_new_hotkey_generic(self, hotkey_type_flag):
        # Khong cho set hotkey neu dang go/ghi/phat
        if self.is_typing_active or self.is_recording or self.is_playing_recording:
            # Co the hien thong bao
            return

        # Neu dang set chinh hotkey nay -> huy
        if self.is_setting_hotkey_type == hotkey_type_flag:
            if self.single_key_listener_worker:
                self.single_key_listener_worker.cancel_current_listening_operation()
            # self._finish_set_hotkey_process se duoc goi boi signal listener_operation_finished
            return

        # Neu dang set mot hotkey khac -> bao loi
        if self.is_setting_hotkey_type != 0:
            QMessageBox.warning(self, Translations.get("msgbox_error_set_hotkey_title"), "Đang trong quá trình cài đặt một hotkey khác. Vui lòng hoàn tất hoặc hủy thao tác đó trước.") #TODO: Translate this
            return

        self.is_setting_hotkey_type = hotkey_type_flag # Dat co dang set hotkey nao
        self._update_set_hotkey_button_text(hotkey_type_flag, Translations.get("button_setting_hotkey_wait")) # Text "Nhan phim moi..."
        self._set_controls_enabled_for_hotkey_setting(False) # Vo hieu hoa cac control khac

        # Kich hoat worker lang nghe
        if self.single_key_listener_worker:
            # Goi slot activate_listener_for_hotkey_type cua worker
            # Worker se bat dau PynputListener trong thread rieng cua no
            self.single_key_listener_worker.activate_listener_for_hotkey_type(hotkey_type_flag)

    def _update_set_hotkey_button_text(self, hotkey_type, text):
        if hotkey_type == self.SETTING_MAIN_HOTKEY: self.btn_set_hotkey.setText(text)
        elif hotkey_type == self.SETTING_START_RECORD_HOTKEY: self.btn_set_start_record_hotkey.setText(text)
        elif hotkey_type == self.SETTING_PLAY_RECORD_HOTKEY: self.btn_set_play_record_hotkey.setText(text)

    def _set_controls_enabled_for_hotkey_setting(self, enabled):
        # Autotyper page controls
        self.btn_start.setEnabled(enabled)
        self.entry_text.setEnabled(enabled); self.spin_interval.setEnabled(enabled); self.spin_repetitions.setEnabled(enabled)
        # Nut set hotkey chinh: chi enable neu ko phai chinh no dang set, hoac la khi `enabled` la True (hoan tat)
        self.btn_set_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_MAIN_HOTKEY else (not self.is_setting_hotkey_type or enabled))

        # Recorder page controls
        self.btn_start_record.setEnabled(enabled)
        self.btn_play_record.setEnabled(enabled)
        self.btn_clear_record.setEnabled(enabled)
        self.spin_record_repetitions.setEnabled(enabled) # Quan ly spinbox lap
        self.btn_set_start_record_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_START_RECORD_HOTKEY else (not self.is_setting_hotkey_type or enabled))
        self.btn_set_play_record_hotkey.setEnabled(enabled if self.is_setting_hotkey_type != self.SETTING_PLAY_RECORD_HOTKEY else (not self.is_setting_hotkey_type or enabled))

        # Nut chuyen mode tren title bar
        self.custom_title_bar.btn_toggle_mode.setEnabled(enabled)


    @Slot(int, object, str)
    def _handle_new_hotkey_captured_generic(self, hotkey_type_captured, key_obj, key_name):
        # Chi xu ly neu dung loai hotkey dang set
        if self.is_setting_hotkey_type != hotkey_type_captured:
            return

        conflict_detected = False
        conflicting_action_description = ""

        # Ktra xung dot voi hotkey AutoTyper chinh
        if hotkey_type_captured != self.SETTING_MAIN_HOTKEY and \
           self.current_hotkey and key_obj == self.current_hotkey:
            conflict_detected = True
            conflicting_action_description = Translations.get("action_description_autotyper")

        # Ktra xung dot voi hotkey Ghi
        if not conflict_detected and \
           hotkey_type_captured != self.SETTING_START_RECORD_HOTKEY and \
           self.current_start_record_hotkey and key_obj == self.current_start_record_hotkey:
            conflict_detected = True
            conflicting_action_description = Translations.get("action_description_record")

        # Ktra xung dot voi hotkey Phat
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
            # Worker lang nghe se tu dung, signal finished se goi _finish_set_hotkey_process
            return

        # Neu ko co xung dot, tiep tuc
        new_hotkey_name_trans = Translations.get("msgbox_hotkey_set_text", new_hotkey_name=key_name)
        QMessageBox.information(self, Translations.get("msgbox_hotkey_set_title"), new_hotkey_name_trans)

        # Cap nhat hotkey tuong ung
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
        # _finish_set_hotkey_process se dc goi boi listener_operation_finished

    @Slot(int, str)
    def _handle_set_hotkey_error_generic(self, hotkey_type_errored, error_message):
        if self.is_setting_hotkey_type != hotkey_type_errored: return
        QMessageBox.critical(self, Translations.get("msgbox_error_set_hotkey_title"), error_message)
        # _finish_set_hotkey_process se duoc goi boi listener_operation_finished

    @Slot(int)
    def _on_single_key_listener_operation_finished_generic(self, hotkey_type_finished):
        # Duoc goi khi listener da bat duoc phim, hoac loi, hoac bi huy
        if self.is_setting_hotkey_type == hotkey_type_finished: # Chi reset neu dung la hotkey dang set
            self._finish_set_hotkey_process(hotkey_type_finished)


    def _finish_set_hotkey_process(self, hotkey_type_processed):
        # Kiem tra xem co con dang set hotkey do khong, tranh goi nhieu lan
        if self.is_setting_hotkey_type != hotkey_type_processed:
            return

        # Tra lai text goc cho nut set hotkey
        original_text_for_button = ""
        if hotkey_type_processed == self.SETTING_MAIN_HOTKEY:
            original_text_for_button = Translations.get("button_set_hotkey")
        elif hotkey_type_processed == self.SETTING_START_RECORD_HOTKEY:
            original_text_for_button = Translations.get("button_set_start_record_hotkey")
        elif hotkey_type_processed == self.SETTING_PLAY_RECORD_HOTKEY:
            original_text_for_button = Translations.get("button_set_play_record_hotkey")

        self.is_setting_hotkey_type = 0 # Reset co
        self._update_set_hotkey_button_text(hotkey_type_processed, original_text_for_button)
        self._set_controls_enabled_for_hotkey_setting(True) # Kich hoat lai cac control


    # --- Recorder/Player Logic ---
    @Slot()
    def toggle_recording_process(self):
        if self.is_setting_hotkey_type != 0 or self.view_stack.currentWidget() != self.recorder_page: return
        if self.is_playing_recording: # Neu dang phat
            QMessageBox.information(self, Translations.get("label_record_play_group"), Translations.get("msgbox_hotkey_conflict_text", new_hotkey_name=self.current_start_record_hotkey_name, action_description=Translations.get("action_description_play") + " (đang chạy)")) #TODO: Translate better
            return

        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self.is_recording: return # Neu da ghi roi thi ko lam gi
        self.is_recording = True

        self.recorded_events.clear() # Xoa ban ghi cu
        self._update_recorded_events_table() # Cap nhat bang (trong)
        self._update_recorder_controls_state() # Cap nhat UI (nut Stop Recording, vo hieu hoa Play/Clear)

        self._cleanup_thread_worker('recorder_thread', 'recorder_worker')
        self.recorder_thread = QThread(self)
        # start_record_hotkey ko con truyen vao worker
        self.recorder_worker = KeyboardRecorderWorker(self.current_start_record_hotkey, self.current_start_record_hotkey_name)
        self.recorder_worker.moveToThread(self.recorder_thread)

        self.recorder_worker.key_event_recorded.connect(self._add_recorded_event)
        self.recorder_worker.recording_status_update.connect(self._update_recorder_status_label) # Gom ca countdown
        self.recorder_worker.recording_finished.connect(self._handle_recorder_worker_finished)

        self.recorder_thread.started.connect(self.recorder_worker.run)
        self.recorder_thread.finished.connect(self.recorder_worker.deleteLater)
        self.recorder_thread.finished.connect(self._handle_recorder_thread_finished)
        self.recorder_thread.start()

    def _stop_recording(self):
        if not self.is_recording or not self.recorder_worker: return
        self.recorder_worker.request_stop() # Worker se emit finished khi dung
        # Khong can cap nhat UI ngay, _handle_recorder_worker_finished se lam

    @Slot(object, str, str, float)
    def _add_recorded_event(self, key_obj, key_name_display, action_canonical, delay_ms):
        # key_obj la PynputKey/KeyCode, action_canonical la "press"/"release"
        self.recorded_events.append((key_obj, key_name_display, action_canonical, delay_ms))
        self._update_recorded_events_table() # Them vao bang hien thi

    @Slot(str)
    def _update_recorder_status_label(self, status):
        self.recorder_status_label.setText(status)

        # Xu ly overlay dem nguoc
        is_countdown_status = False
        # Lay phan dau cua chuoi countdown (vd: "Bắt đầu ghi sau: ")
        current_lang_countdown_prefix = Translations.get("status_recorder_countdown", seconds="").split("...")[0] # Lay phan truoc "..." va seconds
        # Lay phan dau cua chuoi recording (vd: "Đang ghi...")
        # current_lang_recording_prefix = Translations.get("status_recorder_recording", hotkey_name="").split("...")[0]

        if status.startswith(current_lang_countdown_prefix.strip()) and "..." in status:
            is_countdown_status = True

        if is_countdown_status:
            if not self.countdown_overlay:
                self.countdown_overlay = CountdownOverlay(None) # Sua: Parent la None
            # Chi lay phan so va "..." de hien thi ngan gon
            try:
                # Tach phan text sau prefix va truoc "..."
                countdown_text_content = status.replace(current_lang_countdown_prefix.strip(), "").strip()
                self.countdown_overlay.setText(countdown_text_content) # setText se tu goi centerOnScreen
            except Exception: # Fallback
                self.countdown_overlay.setText(status)

            if not self.countdown_overlay.isVisible():
                 self.countdown_overlay.show()
                 self.countdown_overlay.activateWindow() # Thu focus de no len tren
                 self.countdown_overlay.raise_()
        else: # Neu ko phai dem nguoc (vd: "Recording...", "Stopped", "Idle")
            if self.countdown_overlay and self.countdown_overlay.isVisible():
                self.countdown_overlay.hide()


    def _reset_recorder_state_and_ui(self):
        # Neu da reset roi (worker/thread la None)
        if not self.is_recording and self.recorder_worker is None and self.recorder_thread is None:
            return

        was_recording = self.is_recording # Luu lai de biet co can set status "Stopped" khong
        self.is_recording = False
        self._update_recorder_controls_state() # Cap nhat nut (Start Recording, Play/Clear)

        if was_recording: # Chi set "Stopped" neu thuc su vua dung ghi
            self.recorder_status_label.setText(Translations.get("status_recorder_stopped", hotkey_name=self.current_start_record_hotkey_name))

        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.quit()

        if self.countdown_overlay and self.countdown_overlay.isVisible(): # An overlay
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

        # Sau khi ghi xong, neu co ban ghi thi chuyen sang trang thai "Ready to play"
        # Neu khong co ban ghi (ghi loi hoac ko ghi gi) thi "Idle"
        if not self.is_recording and not self.is_playing_recording: # Dam bao ko con process nao chay
            if len(self.recorded_events) > 0:
                 self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
            else:
                 self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

        if self.countdown_overlay and self.countdown_overlay.isVisible(): # An overlay khi thread xong
            self.countdown_overlay.hide()


    @Slot()
    def toggle_playing_process(self):
        if self.is_setting_hotkey_type != 0 or self.view_stack.currentWidget() != self.recorder_page: return
        if self.is_recording: # Neu dang ghi
            QMessageBox.information(self, Translations.get("label_record_play_group"), Translations.get("msgbox_hotkey_conflict_text", new_hotkey_name=self.current_play_record_hotkey_name, action_description=Translations.get("action_description_record") + " (đang chạy)")) #TODO: Translate better
            return

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
        self._update_recorder_controls_state() # Cap nhat UI (nut Stop Playing, vo hieu hoa Record/Clear)

        self._cleanup_thread_worker('player_thread', 'player_worker')
        self.player_thread = QThread(self)

        # Worker can (key_obj, action_canonical, delay_ms)
        # self.recorded_events da luu dung dinh dang nay
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
        self.player_worker.request_stop() # Worker se emit finished khi dung

    def _reset_player_state_and_ui(self, error_occurred=False):
        if not self.is_playing_recording and self.player_worker is None and self.player_thread is None:
            if error_occurred and Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                 self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
            return

        was_playing = self.is_playing_recording
        self.is_playing_recording = False
        self._update_recorder_controls_state() # Cap nhat nut (Play Recording, Record/Clear)

        if error_occurred:
            self.recorder_status_label.setText(Translations.get("status_player_error", hotkey_name=self.current_play_record_hotkey_name))
        else: # Dung binh thuong
            if was_playing and Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0] not in self.recorder_status_label.text():
                self.recorder_status_label.setText(Translations.get("status_player_stopped", hotkey_name=self.current_play_record_hotkey_name))

        if self.player_thread and self.player_thread.isRunning():
            self.player_thread.quit()


    @Slot(str)
    def _handle_player_error(self, error_message):
        QMessageBox.critical(self, Translations.get("msgbox_autotyper_error_title"), error_message) # Dung chung title loi
        self._reset_player_state_and_ui(error_occurred=True)

    @Slot()
    def _handle_player_worker_finished(self): # Phat xong (ko loi)
        self._reset_player_state_and_ui(error_occurred=False)

    @Slot()
    def _handle_player_thread_finished(self):
        self.player_worker = None
        if self.player_thread:
            self.player_thread.deleteLater()
            self.player_thread = None

        # Sau khi phat xong, neu ko co loi, chuyen sang trang thai "Ready to play" (neu con ban ghi)
        # Hoac "Idle" (neu ko con ban ghi hoac ban ghi trong)
        current_text = self.recorder_status_label.text()
        error_prefix_en = Translations.get("status_player_error", hotkey_name="_", lang=Translations.LANG_EN).split("!")[0]

        if not self.is_playing_recording and not self.is_recording: # Dam bao ko con process nao chay
            if error_prefix_en not in current_text: # Neu khong phai la trang thai loi
                if len(self.recorded_events) > 0:
                    self.recorder_status_label.setText(Translations.get("status_player_ready", hotkey_name=self.current_play_record_hotkey_name))
                else: # Ko con ban ghi
                    self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))
            # Else (la loi): status da duoc set, giu nguyen

    def _update_recorder_controls_state(self):
        # Trang thai idle de set hotkey la khi ko ghi, ko phat, VA ko dang set hotkey
        is_idle_for_hotkey_setting = not self.is_recording and not self.is_playing_recording and self.is_setting_hotkey_type == 0

        # Nut Start/Stop Record
        self.btn_start_record.setEnabled(not self.is_playing_recording and self.is_setting_hotkey_type == 0) # Ko cho ghi khi dang phat hoac set hotkey
        self.btn_start_record.setText(
            Translations.get("button_stop_recording", hotkey_name=self.current_start_record_hotkey_name) if self.is_recording
            else Translations.get("button_start_recording", hotkey_name=self.current_start_record_hotkey_name)
        )

        # Nut Play/Stop Recording
        self.btn_play_record.setEnabled(not self.is_recording and self.is_setting_hotkey_type == 0 and len(self.recorded_events) > 0) # Ko cho phat khi dang ghi, set hotkey, hoac ko co ban ghi
        self.btn_play_record.setText(
            Translations.get("button_stop_playing_recording", hotkey_name=self.current_play_record_hotkey_name) if self.is_playing_recording
            else Translations.get("button_play_recording", hotkey_name=self.current_play_record_hotkey_name)
        )
        
        # SpinBox so lan lap
        self.spin_record_repetitions.setEnabled(not self.is_recording and not self.is_playing_recording and self.is_setting_hotkey_type == 0)


        # Cac nut khac
        self.btn_clear_record.setEnabled(is_idle_for_hotkey_setting and len(self.recorded_events) > 0) # Chi cho xoa khi idle va co ban ghi
        self.btn_set_start_record_hotkey.setEnabled(is_idle_for_hotkey_setting if self.is_setting_hotkey_type != self.SETTING_START_RECORD_HOTKEY else True)
        self.btn_set_play_record_hotkey.setEnabled(is_idle_for_hotkey_setting if self.is_setting_hotkey_type != self.SETTING_PLAY_RECORD_HOTKEY else True)
        self.custom_title_bar.btn_toggle_mode.setEnabled(is_idle_for_hotkey_setting) # Nut chuyen mode

    def _update_recorded_events_table(self):
        self.recorded_events_table.setRowCount(0) # Xoa het hang cu
        for _key_obj, key_name_display, action_canonical, delay_ms in self.recorded_events:
            row_pos = self.recorded_events_table.rowCount()
            self.recorded_events_table.insertRow(row_pos)
            self.recorded_events_table.setItem(row_pos, 0, QTableWidgetItem(key_name_display))
            # Dich action_canonical ("press"/"release") sang ngon ngu hien tai de hien thi
            action_display = Translations.get(f"action_{action_canonical}_display")
            self.recorded_events_table.setItem(row_pos, 1, QTableWidgetItem(action_display))
            self.recorded_events_table.setItem(row_pos, 2, QTableWidgetItem(f"{delay_ms:.2f}")) # Format delay
        self.recorded_events_table.scrollToBottom() # Cuon xuong cuoi bang
        self._update_recorder_controls_state() # Cap nhat lai trang thai nut (vd: Play/Clear)

    @Slot()
    def _clear_recorded_events(self):
        if not self.recorded_events: return # Ko co gi de xoa
        reply = QMessageBox.question(self,
                                     Translations.get("msgbox_confirm_clear_recording_title"),
                                     Translations.get("msgbox_confirm_clear_recording_text"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # Mac dinh la No
        if reply == QMessageBox.StandardButton.Yes:
            self.recorded_events.clear()
            self._update_recorded_events_table() # Cap nhat bang (trong)
            if not self.is_recording and not self.is_playing_recording: # Neu dang idle
                self.recorder_status_label.setText(Translations.get("status_recorder_idle", hotkey_name=self.current_start_record_hotkey_name))

    # --- Settings Save/Load ---
    def _serialize_key(self, key_obj):
        if isinstance(key_obj, PynputKey): # Phim dac biet (Key.f9, Key.ctrl_l)
            return {"type": "special", "value": key_obj.name}
        elif isinstance(key_obj, KeyCode): # Phim co char (KeyCode(char='a'))
            # Luu char de KeyCode.from_char co the tai lai
            if key_obj.char is not None:
                return {"type": "keycode_char", "value": key_obj.char}
            # Neu la KeyCode khong co char (vd: vk), luu vk
            elif hasattr(key_obj, 'vk'):
                 return {"type": "keycode_vk", "value": key_obj.vk}
        elif isinstance(key_obj, str): # Neu luu hotkey la chuoi (vd: 'a') cho don gian
            return {"type": "char_str", "value": key_obj}
        return None # Khong serialize duoc

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
            elif key_type == "char_str": # Neu truoc do luu char string, coi no nhu KeyCode tu char
                return KeyCode.from_char(key_value)
        except AttributeError: # Khong tim thay key trong PynputKey
            # print(f"Error deserializing key (AttributeError): {key_data}")
            return None
        except Exception as e: # Loi khac (vd: from_char, from_vk)
            # print(f"Error deserializing key ({type(e).__name__}): {key_data} - {e}")
            return None
        return None


    def _load_settings(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                # Language
                lang_code = settings.get("language", Translations.LANG_VI)
                Translations.set_language(lang_code)
                # Dong bo ComboBox ngon ngu tren title bar
                if hasattr(self, 'custom_title_bar'): # Dam bao title bar da init
                    cb_idx = self.custom_title_bar.lang_combo.findData(lang_code)
                    if cb_idx != -1: self.custom_title_bar.lang_combo.setCurrentIndex(cb_idx)


                # Window geometry and state
                geom_rect_array = settings.get("window_geometry")
                if geom_rect_array: self.setGeometry(QRect(*geom_rect_array))
                if settings.get("window_maximized", False): self.showMaximized()


                # Autotyper settings
                self.entry_text.setText(settings.get("autotyper_text", ""))
                self.spin_interval.setValue(settings.get("autotyper_interval", 1000))
                self.spin_repetitions.setValue(settings.get("autotyper_repetitions", 0))

                hk_data = settings.get("autotyper_hotkey")
                deserialized_hk = self._deserialize_key(hk_data)
                if deserialized_hk:
                    self.current_hotkey = deserialized_hk
                    self.current_hotkey_name = get_pynput_key_display_name(self.current_hotkey)
                # else: dung default da set


                # Recorder settings
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

                # So lan lap cua recorder
                self.spin_record_repetitions.setValue(settings.get("recorder_repetitions", self.DEFAULT_RECORD_REPETITIONS))


                # Recorded events
                self.recorded_events = []
                saved_events = settings.get("recorded_events_v2", []) # v2 su dung key_obj serialization
                for sev in saved_events:
                    key_obj_s = sev.get("key_obj_s")
                    key_obj = self._deserialize_key(key_obj_s)
                    if key_obj:
                        # key_name_display se duoc tao lai hoac luu san
                        key_name_d = sev.get("key_name_display", get_pynput_key_display_name(key_obj))
                        action_c = sev.get("action_canonical")
                        delay_ms = sev.get("delay_ms")
                        if action_c and delay_ms is not None:
                            self.recorded_events.append((key_obj, key_name_d, action_c, delay_ms))
                self._update_recorded_events_table()


                # View mode (sau khi UI da co)
                is_advanced_mode = settings.get("advanced_mode_active", False)
                if hasattr(self, 'view_stack'): # Dam bao view_stack da init
                     self._toggle_view_mode(is_advanced_mode, from_load=True)

            else: # File ko ton tai
                print(Translations.get("config_file_not_found", filepath=self.config_path))
                # Dung defaults da set o __init__
        except Exception as e:
            print(Translations.get("config_loaded_error", filepath=self.config_path, error=str(e)))
            # Dung defaults neu co loi

        # Goi retranslate sau khi load xong de dam bao UI dung ngon ngu va text
        if hasattr(self, 'custom_title_bar'): # Dam bao UI da san sang
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
            "recorder_repetitions": self.spin_record_repetitions.value(), # Luu so lan lap

            "advanced_mode_active": self.view_stack.currentWidget() == self.recorder_page,
        }

        # recorded_events: (key_obj, key_name_display, action_canonical, delay_ms)
        saved_events_data = []
        for key_obj, key_name_d, action_c, delay_ms in self.recorded_events:
            key_obj_s = self._serialize_key(key_obj)
            if key_obj_s: # Chi luu neu serialize thanh cong
                saved_events_data.append({
                    "key_obj_s": key_obj_s,
                    "key_name_display": key_name_d, # Luu lai ten hien thi
                    "action_canonical": action_c,
                    "delay_ms": delay_ms
                })
        settings["recorded_events_v2"] = saved_events_data


        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            # print(f"Settings saved to {self.config_path}") # Log (optional)
        except Exception as e:
            print(Translations.get("config_saved_error", filepath=self.config_path, error=str(e)))
            # Co the hien QMessageBox o day neu can


    def closeEvent(self, event):
        self._save_settings() # Luu settings khi dong

        # Cleanup tat ca threads
        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker')
        self.autotyper_worker = None; self.autotyper_thread = None # Set None de chac chan

        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker')
        self.hotkey_listener_worker = None; self.hotkey_listener_thread = None

        # Dung single_key_listener_worker thread
        if self.single_key_listener_worker:
            self.single_key_listener_worker.request_stop_worker_thread() # Yeu cau worker dung
        if self.single_key_listener_thread: # Kiem tra thread ton tai
            self.single_key_listener_thread.quit()
            if not self.single_key_listener_thread.wait(1500): # Doi toi da 1.5s
                # print("SingleKeyListenerThread did not quit, terminating.")
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


        if self.countdown_overlay: # Dong overlay khi thoat
            self.countdown_overlay.close()
            self.countdown_overlay = None

        event.accept()