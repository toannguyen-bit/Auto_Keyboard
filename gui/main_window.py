# gui/main_window.py
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox, QFormLayout,
    QSizePolicy, QFrame, QStackedLayout, QGroupBox # Them QGroupBox
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, Slot, QPoint, QSize, QRect
from PySide6.QtGui import QFont, QPixmap, QIcon, QMouseEvent, QKeyEvent
from pynput.keyboard import Key as PynputKey

from core.translations import Translations
from core.workers import AutoTyperWorker, HotkeyListenerWorker, SingleKeyListenerWorker, get_pynput_key_display_name
from .custom_title_bar import CustomTitleBar

class AutoTyperWindow(QMainWindow):
    DEFAULT_HOTKEY = PynputKey.f9
    # DEFAULT_HOTKEY_NAME se dc khoi tao trong __init__

    RESIZE_MARGIN = 10
    NO_EDGE, TOP_EDGE, BOTTOM_EDGE, LEFT_EDGE, RIGHT_EDGE = 0x0, 0x1, 0x2, 0x4, 0x8
    TOP_LEFT_CORNER, TOP_RIGHT_CORNER = TOP_EDGE | LEFT_EDGE, TOP_EDGE | RIGHT_EDGE
    BOTTOM_LEFT_CORNER, BOTTOM_RIGHT_CORNER = BOTTOM_EDGE | LEFT_EDGE, BOTTOM_EDGE | RIGHT_EDGE

    def __init__(self, base_path): # Nhan base_path tu main.py
        super().__init__()
        self.base_path = base_path
        self.background_image_filename = "stellar.jpg" # Ten file anh
        # Duong dan anh nen, thay \ bang / cho os-compatibility
        self.background_image_path = os.path.join(self.base_path, "assets", self.background_image_filename).replace("\\", "/")

        Translations.set_language(Translations.LANG_VI) # Dat NN mac dinh

        self.DEFAULT_HOTKEY_NAME = get_pynput_key_display_name(self.DEFAULT_HOTKEY)

        self.setMinimumSize(640, 520) # Tang min height cho muc set hotkey
        self.resize(800, 650) # Tang chieu cao

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.is_typing_active = False
        self.current_hotkey = self.DEFAULT_HOTKEY
        self.current_hotkey_name = self.DEFAULT_HOTKEY_NAME

        self.autotyper_thread = None
        self.autotyper_worker = None
        
        self.hotkey_listener_thread = None # Thread cho listener chinh
        self.hotkey_listener_worker = None # Worker cho listener chinh

        self.single_key_listener_thread = None # Thread cho set hotkey
        self.single_key_listener_worker = None # Worker cho set hotkey
        self.is_setting_hotkey = False # Flag trang thai set hotkey

        self.original_pixmap = QPixmap(self.background_image_path)

        self._is_dragging = False; self._drag_start_pos = QPoint()
        self._is_resizing = False; self._resize_edge = self.NO_EDGE
        self._resize_start_mouse_pos = QPoint(); self._resize_start_window_geometry = QRect()

        self.init_ui_elements() 
        self.apply_styles()
        self.init_main_hotkey_listener() # Khoi tao listener chinh
        
        self._retranslate_ui() 
        self.setMouseTracking(True) # Cho resize window

    def init_ui_elements(self): # Tao UI
        self.main_container_widget = QWidget(); self.main_container_widget.setObjectName("mainContainerWidget")
        self.setCentralWidget(self.main_container_widget)
        overall_layout = QVBoxLayout(self.main_container_widget); overall_layout.setContentsMargins(0,0,0,0); overall_layout.setSpacing(0)

        self.custom_title_bar = CustomTitleBar(self, current_lang_code=Translations.current_lang)
        self.custom_title_bar.language_changed_signal.connect(self._handle_language_change)
        overall_layout.addWidget(self.custom_title_bar)

        main_area_widget = QWidget(); main_area_layout = QVBoxLayout(main_area_widget); main_area_layout.setContentsMargins(0,0,0,0); main_area_layout.setSpacing(0)
        main_area_stacked_layout = QStackedLayout(); main_area_stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        self.background_label = QLabel(); self.background_label.setObjectName("backgroundLabel")
        if self.original_pixmap.isNull(): self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.background_label.setStyleSheet("background-color: rgb(10, 12, 22); color: white;")
        else: self._update_background_pixmap()
        self.background_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        main_area_stacked_layout.addWidget(self.background_label)

        content_widget = QWidget(); content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout(content_widget); content_layout.setContentsMargins(30, 15, 30, 20); content_layout.setSpacing(15) # Giam margin, spacing

        # --- Input Frame ---
        input_frame = QFrame(); input_frame.setObjectName("inputFrame")
        self.form_layout = QFormLayout(input_frame); self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows); self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft); self.form_layout.setHorizontalSpacing(10); self.form_layout.setVerticalSpacing(12)
        self.label_for_text_entry = QLabel(); self.entry_text = QLineEdit(); self.entry_text.setObjectName("textInput"); self.form_layout.addRow(self.label_for_text_entry, self.entry_text)
        self.label_for_interval = QLabel(); self.spin_interval = QSpinBox(); self.spin_interval.setRange(1,600000); self.spin_interval.setValue(1000); self.spin_interval.setObjectName("intervalInput"); self.form_layout.addRow(self.label_for_interval, self.spin_interval)
        self.label_for_repetitions = QLabel(); self.spin_repetitions = QSpinBox(); self.spin_repetitions.setRange(0,1000000); self.spin_repetitions.setValue(0); self.spin_repetitions.setObjectName("repetitionsInput"); self.form_layout.addRow(self.label_for_repetitions, self.spin_repetitions)
        content_layout.addWidget(input_frame)

        # --- Hotkey Settings Group ---
        hotkey_group = QGroupBox(); hotkey_group.setObjectName("hotkeyGroup") # Style QGroupBox
        hotkey_group_layout = QVBoxLayout(hotkey_group); hotkey_group_layout.setSpacing(8)
        
        current_hotkey_layout = QHBoxLayout()
        self.lbl_current_hotkey_static = QLabel() # "Hotkey hien tai:"
        self.lbl_current_hotkey_value = QLabel(self.current_hotkey_name) # Gia tri F9, Ctrl+V...
        self.lbl_current_hotkey_value.setObjectName("currentHotkeyDisplay") # Style rieng
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_static)
        current_hotkey_layout.addWidget(self.lbl_current_hotkey_value)
        current_hotkey_layout.addStretch()
        hotkey_group_layout.addLayout(current_hotkey_layout)

        self.btn_set_hotkey = QPushButton(); self.btn_set_hotkey.setObjectName("setHotkeyButton"); self.btn_set_hotkey.clicked.connect(self._prompt_for_new_hotkey)
        self.btn_set_hotkey.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed) # Cho nut nho hon
        hotkey_group_layout.addWidget(self.btn_set_hotkey, 0, Qt.AlignmentFlag.AlignLeft) # Canh trai
        content_layout.addWidget(hotkey_group)

        # --- Start/Stop Buttons ---
        button_layout_container = QWidget(); button_layout = QHBoxLayout(button_layout_container); button_layout.setContentsMargins(0,8,0,0)
        self.btn_start = QPushButton(); self.btn_start.setObjectName("startButton"); self.btn_start.clicked.connect(self.toggle_typing_process)
        self.btn_stop = QPushButton(); self.btn_stop.setObjectName("stopButton"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_typing_process)
        button_layout.addStretch(); button_layout.addWidget(self.btn_start); button_layout.addWidget(self.btn_stop); button_layout.addStretch()
        content_layout.addWidget(button_layout_container)

        self.status_label = QLabel(); self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        main_area_stacked_layout.addWidget(content_widget); main_area_stacked_layout.setCurrentWidget(content_widget)
        main_area_layout.addLayout(main_area_stacked_layout); overall_layout.addWidget(main_area_widget)

    def _retranslate_ui(self): # Cap nhat van ban UI
        self.setWindowTitle(Translations.get("window_title"))
        self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name))
        self.custom_title_bar.retranslate_ui_texts() # Cho combobox NN

        if self.original_pixmap.isNull():
            # Chi log 1 lan khi khoi tao hoac khi thay doi NN ma van loi
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

        # Hotkey settings
        if hasattr(self, 'hotkey_group'): # hotkey_group co the chua dc tao khi goi lan dau
             self.hotkey_group.setTitle(Translations.get("label_hotkey_setting_group"))
        self.lbl_current_hotkey_static.setText(Translations.get("label_current_hotkey"))
        self.lbl_current_hotkey_value.setText(self.current_hotkey_name) # Luon cap nhat
        
        if self.is_setting_hotkey:
            self.btn_set_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        else:
            self.btn_set_hotkey.setText(Translations.get("button_set_hotkey"))

        # Start/Stop buttons & Status label
        if self.is_typing_active:
            self.btn_start.setText(Translations.get("button_start_loading"))
            # Status se duoc cap nhat boi worker/stop_process
        else:
            self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name))
            # Tranh ghi de status neu dang o trang thai dac biet
            current_status = self.status_label.text()
            req_stop_text = Translations.get("status_requesting_stop")
            # Kiem tra xem status hien tai co phai la mot trong cac trang thai "da dung" hoac "san sang" khong
            # Can so sanh voi text da dich sang NN hien tai
            is_ready_or_stopped_status = any(
                status_key in current_status for status_key in [
                    Translations.get("status_ready", hotkey_name=self.current_hotkey_name, lang=Translations.LANG_EN), # check voi EN lam chuan
                    Translations.get("status_stopped", hotkey_name=self.current_hotkey_name, lang=Translations.LANG_EN),
                    Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name, lang=Translations.LANG_EN)
                ]
            )

            if current_status == req_stop_text: # Neu dang yeu cau dung, giu nguyen
                pass
            elif self.autotyper_worker is None and self.autotyper_thread is None: # Da dung hoan toan
                 self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))
            elif not self.is_typing_active and is_ready_or_stopped_status : # Neu chi la dung bt hoac san sang
                self.status_label.setText(Translations.get("status_ready", hotkey_name=self.current_hotkey_name))
            # Neu status khac (vd: error message), giu nguyen


        self.btn_stop.setText(Translations.get("button_stop"))


    @Slot(str)
    def _handle_language_change(self, lang_code): # Xu ly khi NN thay doi
        Translations.set_language(lang_code)
        self._retranslate_ui()
        self.apply_styles() 

    def apply_styles(self): # CSS cho app
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
        hotkey_group_border_color = input_frame_border_color; hotkey_value_color = "rgb(180, 210, 255)"; set_hotkey_button_padding = "6px 15px"; set_hotkey_button_min_width = "120px";

        qss = f"""
            QMainWindow {{ background: transparent; }}
            QWidget#mainContainerWidget {{ background-color: {app_main_container_bg}; border-radius: 10px; }}
            QLabel#backgroundLabel {{ border-radius: 10px; /* Goc tron cho bg label */ }}
            QWidget#contentWidget {{ background-color: transparent; }}
            QWidget#customTitleBar {{ background-color: {title_bar_bg}; border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid rgba(224, 218, 230, 0.1); }}
            QLabel#titleBarLabel {{ color: {title_bar_text_color}; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; padding-left: 5px; background-color: transparent; }}
            QPushButton#minimizeButton, QPushButton#maximizeRestoreButton, QPushButton#closeButton {{ background-color: {title_bar_button_bg}; border: none; border-radius: 6px; color: {subtext_color}; font-family: "{font_family}"; font-size: 12pt; font-weight: bold; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0px; }}
            QPushButton#minimizeButton:hover, QPushButton#maximizeRestoreButton:hover {{ background-color: {title_bar_button_hover_bg}; color: {text_color}; }}
            QPushButton#closeButton:hover {{ background-color: {close_button_hover_bg}; color: white; }}
            QPushButton#minimizeButton:pressed, QPushButton#maximizeRestoreButton:pressed {{ background-color: {title_bar_button_pressed_bg}; }}
            QPushButton#closeButton:pressed {{ background-color: {close_button_pressed_bg}; }}
            QComboBox#languageComboBox {{ background-color: {combo_box_bg}; color: {text_color}; border: 1px solid {combo_box_border}; border-radius: 6px; padding: 4px 8px; font-family: "{font_family}"; font-size: 9pt; min-height: 20px; }}
            QComboBox#languageComboBox:hover {{ border-color: {input_focus_border_color}; }}
            QComboBox#languageComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left-width: 1px; border-left-color: {combo_box_border}; border-left-style: solid; border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
            QComboBox QAbstractItemView {{ background-color: {combo_box_dropdown_bg}; color: {text_color}; border: 1px solid {input_focus_border_color}; selection-background-color: {combo_box_dropdown_item_hover_bg}; padding: 3px; border-radius: 4px; font-family: "{font_family}"; font-size: 9pt; }}
            QFrame#inputFrame {{ background-color: {input_frame_bg_color}; border-radius: 14px; padding: 20px; border: 1.5px solid {input_frame_border_color}; }}
            QGroupBox#hotkeyGroup {{ font-family: "{font_family}"; font-size: 10pt; color: {text_color}; border: 1.5px solid {hotkey_group_border_color}; border-radius: 10px; margin-top: 8px; padding: 15px 15px 10px 15px; background-color: transparent; }} /* Style cho groupbox */
            QGroupBox#hotkeyGroup::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px 0 5px; left: 10px; color: {subtext_color}; }}
            QLabel {{ color: {text_color}; font-family: "{font_family}"; font-size: 10pt; padding: 2px; background-color: transparent; }}
            QLabel#currentHotkeyDisplay {{ color: {hotkey_value_color}; font-weight: bold; font-size: 10pt; padding-left: 5px;}}
            QLineEdit, QSpinBox {{ background-color: {input_bg_color}; color: {text_color}; border: 1.5px solid {input_border_color}; border-radius: 9px; padding: 9px 12px; font-family: "{font_family}"; font-size: 10pt; min-height: 24px; }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1.5px solid {input_focus_border_color}; background-color: {input_focus_bg_color}; }}
            QLineEdit::placeholder {{ color: {subtext_color}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: right; width: 18px; border: 1.5px solid {input_border_color}; border-radius: 5px; background-color: {button_bg_color}; margin: 2px 3px 2px 2px; }}
            QSpinBox::up-button {{ top: 1px; height: 11px;}} QSpinBox::down-button {{ bottom: 1px; height: 11px;}}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: rgba(95, 100, 135, 0.95); }}
            QPushButton {{ color: {button_text_color}; background-color: {button_bg_color}; border: 1.5px solid {button_border_color}; padding: 10px 22px; border-radius: 10px; font-family: "{font_family}"; font-size: 10pt; font-weight: bold; min-width: 130px; }}
            QPushButton#startButton {{ background-color: {start_button_bg_color}; border-color: {start_button_border_color}; }}
            QPushButton#startButton:hover {{ background-color: {start_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }}
            QPushButton#startButton:pressed {{ background-color: {start_button_pressed_bg}; }}
            QPushButton#stopButton:hover {{ background-color: {stop_button_hover_bg}; border-color: rgb(210, 190, 250); }}
            QPushButton#stopButton:pressed {{ background-color: {stop_button_pressed_bg}; }}
            QPushButton#setHotkeyButton {{ padding: {set_hotkey_button_padding}; min-width: {set_hotkey_button_min_width}; max-width: 180px; font-size: 9pt; }} /* Style nut set hotkey */
            QPushButton:disabled {{ background-color: {disabled_bg_color}; color: {disabled_text_color}; border-color: {disabled_border_color}; }}
            QLabel#statusLabel {{ color: {subtext_color}; background-color: {status_bg_color}; border: 1px solid {status_border_color}; border-radius: 9px; padding: 12px; font-size: 9pt; margin-top: 10px; font-family: "{font_family}"; }}
            QMessageBox {{ background-color: {msgbox_bg_color}; font-family: "{font_family}"; border-radius: 8px; border: 1px solid {input_frame_border_color}; }}
            QMessageBox QLabel {{ color: {msgbox_text_color}; font-size: 10pt; background-color: transparent; font-family: "{font_family}";}}
            QMessageBox QPushButton {{ background-color: {msgbox_button_bg}; border-color: {msgbox_button_border}; color: {button_text_color}; padding: 8px 18px; border-radius: 8px; min-width: 80px; font-family: "{font_family}";}}
            QMessageBox QPushButton:hover {{ background-color: {msgbox_button_hover_bg}; border-color: {start_button_hover_border_color_val}; }}
        """
        app_font = QFont("Segoe UI", 10)
        if Translations.current_lang == Translations.LANG_JA: app_font = QFont("Meiryo", 9) # Font Nhat nho hon chut
        QApplication.setFont(app_font)
        self.setStyleSheet(qss)
        self.update(); 
        if self.parent(): self.parent().update()
    
    def _update_background_pixmap(self): # Ve lai anh nen khi resize
        if hasattr(self, 'background_label') and not self.original_pixmap.isNull():
            main_area_height = self.main_container_widget.height() - self.custom_title_bar.height()
            main_area_width = self.main_container_widget.width()
            if main_area_width <= 0 or main_area_height <= 0: return
            target_size_for_bg = QSize(main_area_width, main_area_height)
            scaled_pixmap = self.original_pixmap.scaled(target_size_for_bg, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.background_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event): self._update_background_pixmap(); super().resizeEvent(event)

    def _get_current_resize_edge(self, local_pos: QPoint) -> int: # Ktra canh resize
        edge = self.NO_EDGE; rect = self.rect()
        if local_pos.x() < self.RESIZE_MARGIN: edge |= self.LEFT_EDGE
        if local_pos.x() > rect.width() - self.RESIZE_MARGIN: edge |= self.RIGHT_EDGE
        if local_pos.y() < self.RESIZE_MARGIN: edge |= self.TOP_EDGE
        if local_pos.y() > rect.height() - self.RESIZE_MARGIN: edge |= self.BOTTOM_EDGE
        return edge

    def mousePressEvent(self, event: QMouseEvent): # Click chuot
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint(); global_pos = event.globalPosition().toPoint()
            self._resize_edge = self._get_current_resize_edge(local_pos)
            if self._resize_edge != self.NO_EDGE:
                self._is_resizing = True; self._is_dragging = False
                self._resize_start_mouse_pos = global_pos; self._resize_start_window_geometry = self.geometry()
                event.accept(); return
            # Ko drag khi click vao combobox NN hay cac nut tren title bar
            is_on_interactive_title_widget = False
            for child_widget in self.custom_title_bar.findChildren(QPushButton) + [self.custom_title_bar.lang_combo]:
                if child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(global_pos)):
                    is_on_interactive_title_widget = True; break
            if self.custom_title_bar.geometry().contains(local_pos) and not is_on_interactive_title_widget:
                self._is_dragging = True; self._is_resizing = False
                self._drag_start_pos = global_pos - self.frameGeometry().topLeft()
                event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent): # Di chuot
        if event.buttons() & Qt.LeftButton: # Dang giu chuot trai
            if self._is_resizing:
                delta = event.globalPosition().toPoint() - self._resize_start_mouse_pos; start_geom = self._resize_start_window_geometry; new_geom = QRect(start_geom)
                min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
                if self._resize_edge & self.LEFT_EDGE: new_left = start_geom.left() + delta.x(); new_width = max(min_w, start_geom.width() - delta.x()); new_geom.setLeft(start_geom.right() - new_width); new_geom.setWidth(new_width)
                if self._resize_edge & self.RIGHT_EDGE: new_geom.setWidth(max(min_w, start_geom.width() + delta.x()))
                if self._resize_edge & self.TOP_EDGE: new_top = start_geom.top() + delta.y(); new_height = max(min_h, start_geom.height() - delta.y()); new_geom.setTop(start_geom.bottom() - new_height); new_geom.setHeight(new_height)
                if self._resize_edge & self.BOTTOM_EDGE: new_geom.setHeight(max(min_h, start_geom.height() + delta.y()))
                self.setGeometry(new_geom); event.accept(); return
            elif self._is_dragging: self.move(event.globalPosition().toPoint() - self._drag_start_pos); event.accept(); return

        if not (self._is_resizing or self._is_dragging): # Hover de doi cursor
            local_pos = event.position().toPoint(); current_hover_edge = self._get_current_resize_edge(local_pos)
            is_on_interactive_title_widget = False
            for child_widget in self.custom_title_bar.findChildren(QPushButton) + [self.custom_title_bar.lang_combo]:
                if child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(event.globalPosition().toPoint())) : is_on_interactive_title_widget = True; break
            
            if is_on_interactive_title_widget: self.unsetCursor()
            elif current_hover_edge == self.TOP_LEFT_CORNER or current_hover_edge == self.BOTTOM_RIGHT_CORNER: self.setCursor(Qt.SizeFDiagCursor)
            elif current_hover_edge == self.TOP_RIGHT_CORNER or current_hover_edge == self.BOTTOM_LEFT_CORNER: self.setCursor(Qt.SizeBDiagCursor)
            elif current_hover_edge & self.LEFT_EDGE or current_hover_edge & self.RIGHT_EDGE: self.setCursor(Qt.SizeHorCursor)
            elif current_hover_edge & self.TOP_EDGE or current_hover_edge & self.BOTTOM_EDGE: self.setCursor(Qt.SizeVerCursor)
            else: self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent): # Tha chuot
        if event.button() == Qt.LeftButton:
            changed_state = False
            if self._is_resizing: self._is_resizing = False; changed_state = True
            if self._is_dragging: self._is_dragging = False; changed_state = True
            if changed_state: self._resize_edge = self.NO_EDGE; self.unsetCursor(); event.accept(); return
        super().mouseReleaseEvent(event)

    def _cleanup_thread_worker(self, thread_attr, worker_attr): # Don dep thread va worker
        worker = getattr(self, worker_attr, None)
        thread = getattr(self, thread_attr, None)
        
        if worker:
            if hasattr(worker, 'request_stop'): worker.request_stop()
            # worker.deleteLater() # Qt se tu don dep khi thread ket thuc neu worker moveToThread
        
        if thread and thread.isRunning():
            thread.quit()
            if not thread.wait(300): # Cho thread ket thuc
                # print(f"Warning: Thread {thread_attr} did not finish in time.")
                thread.terminate() # Neu can thiet
                thread.wait() # Cho terminate
        
        setattr(self, worker_attr, None)
        setattr(self, thread_attr, None)


    def init_main_hotkey_listener(self): # Khoi tao listener cho hotkey chinh
        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker') # Don dep listener cu neu co

        self.hotkey_listener_thread = QThread(self)
        self.hotkey_listener_worker = HotkeyListenerWorker(self.current_hotkey)
        self.hotkey_listener_worker.moveToThread(self.hotkey_listener_thread)
        
        # Ket noi tin hieu
        self.hotkey_listener_worker.hotkey_pressed_signal.connect(self.toggle_typing_process)
        self.hotkey_listener_thread.started.connect(self.hotkey_listener_worker.run)
        
        # Tu dong don dep khi thread ket thuc
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_worker.deleteLater)
        self.hotkey_listener_thread.finished.connect(self.hotkey_listener_thread.deleteLater) # Xoa thread sau khi worker da dc xoa
        
        self.hotkey_listener_thread.start()
        # print(f"Main hotkey listener started for: {self.current_hotkey_name}")

    @Slot()
    def toggle_typing_process(self): # Bat/Tat go phim
        if self.is_setting_hotkey: return # Neu dang set hotkey thi ko lam gi
        if self.is_typing_active: self.stop_typing_process()
        else: self.start_typing_process()

    def start_typing_process(self): # Bat dau go phim
        if self.is_typing_active or self.is_setting_hotkey: return
        text = self.entry_text.text(); interval = self.spin_interval.value(); repetitions = self.spin_repetitions.value()
        if not text: QMessageBox.warning(self, Translations.get("msgbox_missing_info_title"), Translations.get("worker_empty_text_error")); return
        
        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker') # Don dep worker/thread go phim cu

        self.is_typing_active = True
        self.btn_start.setEnabled(False); self.btn_start.setText(Translations.get("button_start_loading"))
        self.btn_stop.setEnabled(True); self.btn_set_hotkey.setEnabled(False) # Vo hieu hoa nut set hotkey
        self.status_label.setText(Translations.get("status_preparing", hotkey_name=self.current_hotkey_name)); QApplication.processEvents()
        
        self.autotyper_thread = QThread(self)
        self.autotyper_worker = AutoTyperWorker(text, interval, repetitions, self.current_hotkey_name)
        self.autotyper_worker.moveToThread(self.autotyper_thread)
        self.autotyper_worker.update_status_signal.connect(self.update_status_label)
        self.autotyper_worker.error_signal.connect(self.show_error_message_box)
        self.autotyper_worker.typing_finished_signal.connect(self._handle_autotyper_worker_finished)
        # self.autotyper_worker.typing_finished_signal.connect(self.autotyper_worker.deleteLater) # Worker tu xoa khi finished (neu ko co handle_worker_really_finished)
        
        self.autotyper_thread.started.connect(self.autotyper_worker.run)
        self.autotyper_thread.finished.connect(self._handle_autotyper_thread_finished)
        # self.autotyper_thread.finished.connect(self.autotyper_thread.deleteLater) # Thread tu xoa khi finished
        self.autotyper_thread.start()

    @Slot()
    def stop_typing_process(self): # Dung go phim
        if not self.is_typing_active: self._update_ui_stopped_status(); return # Neu ko chay thi cap nhat UI thoi
        if self.autotyper_worker: self.autotyper_worker.request_stop()
        else: self._reset_typing_state_and_ui(); return # Neu ko co worker thi reset luon
        self.btn_stop.setEnabled(False); self.status_label.setText(Translations.get("status_requesting_stop"))

    @Slot(str)
    def update_status_label(self, message): self.status_label.setText(message)
    @Slot(str)
    def show_error_message_box(self, message): 
        QMessageBox.critical(self, Translations.get("msgbox_autotyper_error_title"), message)
        self._reset_typing_state_and_ui() # Reset sau khi bao loi

    def _update_ui_stopped_status(self): # Cap nhat UI khi da dung
        self.btn_start.setEnabled(True); self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name))
        self.btn_stop.setEnabled(False)
        self.btn_set_hotkey.setEnabled(not self.is_setting_hotkey) # Kich hoat lai nut set hotkey neu ko dang set
        # Chi cap nhat status neu khong phai la trang thai loi
        if Translations.get("msgbox_autotyper_error_title") not in self.status_label.text(): # Tam thoi check don gian
             self.status_label.setText(Translations.get("status_stopped", hotkey_name=self.current_hotkey_name))

    def _reset_typing_state_and_ui(self): # Reset trang thai va UI
        self.is_typing_active = False
        self._update_ui_stopped_status() # Cap nhat UI
        # Khong can quit thread o day, de _handle_worker_finished va _handle_thread_finished lam

    @Slot()
    def _handle_autotyper_worker_finished(self): # Khi worker bao xong
        # print("AutoTyperWorker finished signal received.")
        self._reset_typing_state_and_ui()
        if self.autotyper_thread and self.autotyper_thread.isRunning():
            self.autotyper_thread.quit() # Yeu cau thread dung
        if self.autotyper_worker:
            self.autotyper_worker.deleteLater() # Danh dau de xoa worker
            self.autotyper_worker = None


    @Slot()
    def _handle_autotyper_thread_finished(self): # Khi thread thuc su ket thuc
        # print("AutoTyperThread finished signal received.")
        if self.autotyper_thread:
            self.autotyper_thread.deleteLater() # Danh dau de xoa thread
            self.autotyper_thread = None
        
        # Dam bao trang thai la "da dung hoan toan" neu khong co loi xay ra
        # Neu co loi thi message box da hien va status da dc set
        if not self.is_typing_active and Translations.get("msgbox_autotyper_error_title") not in self.status_label.text():
             self.status_label.setText(Translations.get("status_stopped_fully", hotkey_name=self.current_hotkey_name))


    # --- Xu ly cai dat Hotkey ---
    @Slot()
    def _prompt_for_new_hotkey(self): # Bat dau qua trinh set hotkey
        if self.is_typing_active: return # Ko cho set khi dang go
        if self.is_setting_hotkey: # Huy neu dang set roi (nhan lai nut)
            self._cleanup_thread_worker('single_key_listener_thread', 'single_key_listener_worker')
            self.is_setting_hotkey = False
            self.btn_set_hotkey.setText(Translations.get("button_set_hotkey"))
            self.btn_set_hotkey.setEnabled(True)
            self.btn_start.setEnabled(True) # Bat lai nut Start
            return

        self.is_setting_hotkey = True
        self.btn_set_hotkey.setText(Translations.get("button_setting_hotkey_wait"))
        self.btn_set_hotkey.setEnabled(False) # Vo hieu hoa chinh no
        self.btn_start.setEnabled(False) # Vo hieu hoa nut Start
        
        self._cleanup_thread_worker('single_key_listener_thread', 'single_key_listener_worker') # Don dep neu co

        self.single_key_listener_thread = QThread(self)
        self.single_key_listener_worker = SingleKeyListenerWorker()
        self.single_key_listener_worker.moveToThread(self.single_key_listener_thread)

        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error)
        # Tu dong don dep
        self.single_key_listener_thread.started.connect(self.single_key_listener_worker.run)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_worker.deleteLater)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_thread.deleteLater)
        self.single_key_listener_thread.finished.connect(self._on_single_key_listener_thread_finished) # Reset UI

        self.single_key_listener_thread.start()

    @Slot(object, str)
    def _handle_new_hotkey_captured(self, key_obj, key_name): # Xu ly hotkey moi bat duoc
        # print(f"New hotkey captured: {key_name} (obj: {key_obj})")
        self.current_hotkey = key_obj
        self.current_hotkey_name = key_name
        
        self.lbl_current_hotkey_value.setText(self.current_hotkey_name) # Cap nhat label
        self.custom_title_bar.setTitle(Translations.get("title_bar_text", hotkey=self.current_hotkey_name)) # Cap nhat title bar
        self.btn_start.setText(Translations.get("button_start", hotkey_name=self.current_hotkey_name)) # Cap nhat nut Start
        if not self.is_typing_active : # Cap nhat status label neu ko dang chay
            self.status_label.setText(Translations.get("status_ready", hotkey_name=self.current_hotkey_name))
        
        QMessageBox.information(self, Translations.get("msgbox_hotkey_set_title"), Translations.get("msgbox_hotkey_set_text", new_hotkey_name=key_name))
        
        self.init_main_hotkey_listener() # Khoi tao lai listener chinh voi hotkey moi
        self._finish_set_hotkey_process()

    @Slot(str)
    def _handle_set_hotkey_error(self, error_message): # Xu ly loi khi set hotkey
        QMessageBox.critical(self, Translations.get("msgbox_error_set_hotkey_title"), error_message)
        self._finish_set_hotkey_process()

    @Slot()
    def _on_single_key_listener_thread_finished(self): # Khi thread bat phim ket thuc
        # print("SingleKeyListenerThread actually finished.")
        self._finish_set_hotkey_process() # Goi de dam bao UI reset
        self.single_key_listener_worker = None # Clear ref
        self.single_key_listener_thread = None # Clear ref


    def _finish_set_hotkey_process(self): # Ket thuc qua trinh set hotkey, reset UI
        if self.is_setting_hotkey: # Chi reset neu dang trong qua trinh set
            self.is_setting_hotkey = False
            self.btn_set_hotkey.setText(Translations.get("button_set_hotkey"))
            self.btn_set_hotkey.setEnabled(True)
            if not self.is_typing_active: # Chi bat lai nut Start neu ko dang go phim
                self.btn_start.setEnabled(True)
        
        # Dam bao single key listener da dung
        if self.single_key_listener_thread and self.single_key_listener_thread.isRunning():
            self.single_key_listener_thread.quit() # Yeu cau dung
            # Khong can wait o day, finished signal se lo

    def closeEvent(self, event): # Khi dong cua so
        # print("Close event called.")
        self._cleanup_thread_worker('autotyper_thread', 'autotyper_worker')
        self._cleanup_thread_worker('hotkey_listener_thread', 'hotkey_listener_worker')
        self._cleanup_thread_worker('single_key_listener_thread', 'single_key_listener_worker')
        # print("All workers/threads requested to stop.")
        event.accept()