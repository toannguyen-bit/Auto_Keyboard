# gui/base_main_window.py
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QMessageBox,
    QSizePolicy, QStackedWidget, QStackedLayout
)
from PySide6.QtCore import Qt, QThread, Slot, QPoint, QSize, QRect
from PySide6.QtGui import QFont, QPixmap, QIcon, QMouseEvent

from pynput.keyboard import Key as PynputKey, KeyCode 

from core.translations import Translations
from core.workers import SingleKeyListenerWorker, get_pynput_key_display_name
from .custom_title_bar import CustomTitleBar
from .countdown_overlay import CountdownOverlay 
from .constants import (
    RESIZE_MARGIN, NO_EDGE, TOP_EDGE, BOTTOM_EDGE, LEFT_EDGE, RIGHT_EDGE,
    TOP_LEFT_CORNER, TOP_RIGHT_CORNER, BOTTOM_LEFT_CORNER, BOTTOM_RIGHT_CORNER,
    CONFIG_FILE_NAME
)


class BaseMainWindow(QMainWindow):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.config_path = os.path.join(self.base_path, CONFIG_FILE_NAME)
        self.background_image_filename = "stellar.jpg"
        self.background_image_path = os.path.join(self.base_path, "assets", self.background_image_filename).replace("\\", "/")

        app_icon_path = os.path.join(self.base_path, "assets", "icon.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        Translations.set_language(Translations.LANG_VI) # Mac dinh, se bi ghi de boi config

        self.setMinimumSize(700, 600) # Kich thuoc toi thieu
        self.resize(850, 700) # Kich thuoc mac dinh

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.is_setting_hotkey_type = 0 # Loai hotkey dang duoc set (0 la ko set)

        self.single_key_listener_thread = QThread(self)
        self.single_key_listener_worker = SingleKeyListenerWorker()
        self.single_key_listener_worker.moveToThread(self.single_key_listener_thread)
        # Cac signal cua worker nay se duoc connect o lop con (AutoTyperWindow)
        self.single_key_listener_thread.started.connect(self.single_key_listener_worker.run)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_worker.deleteLater)
        self.single_key_listener_thread.finished.connect(self.single_key_listener_thread.deleteLater)
        self.single_key_listener_thread.start()

        self.original_pixmap = QPixmap(self.background_image_path)
        self._is_dragging = False; self._drag_start_pos = QPoint()
        self._is_resizing = False; self._resize_edge = NO_EDGE
        self._resize_start_mouse_pos = QPoint(); self._resize_start_window_geometry = QRect()

        self.countdown_overlay = None # Khoi tao overlay

        self.init_base_ui_elements()
        self.apply_styles()

        self._retranslate_base_ui()
        self.setMouseTracking(True) # Cho resize/drag

    def init_base_ui_elements(self):
        self.main_container_widget = QWidget(); self.main_container_widget.setObjectName("mainContainerWidget")
        self.setCentralWidget(self.main_container_widget)
        overall_layout = QVBoxLayout(self.main_container_widget); overall_layout.setContentsMargins(0,0,0,0); overall_layout.setSpacing(0)

        self.custom_title_bar = CustomTitleBar(self, current_lang_code=Translations.current_lang)
        self.custom_title_bar.language_changed_signal.connect(self._handle_language_change)
        self.custom_title_bar.toggle_advanced_mode_signal.connect(self._toggle_view_mode_slot)
        overall_layout.addWidget(self.custom_title_bar)

        main_area_widget = QWidget(); main_area_layout = QVBoxLayout(main_area_widget); main_area_layout.setContentsMargins(0,0,0,0); main_area_layout.setSpacing(0)

        self.view_stack = QStackedWidget() # Cac page se duoc them vao day

        main_area_stacked_layout = QStackedLayout(); main_area_stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.background_label = QLabel(); self.background_label.setObjectName("backgroundLabel")
        if self.original_pixmap.isNull(): self.background_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.background_label.setStyleSheet("background-color: rgb(10, 12, 22); color: white;")
        else: self._update_background_pixmap()
        self.background_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        main_area_stacked_layout.addWidget(self.background_label)
        main_area_stacked_layout.addWidget(self.view_stack)

        main_area_layout.addLayout(main_area_stacked_layout)
        overall_layout.addWidget(main_area_widget)

    @Slot(bool)
    def _toggle_view_mode_slot(self, to_advanced_mode): 
        self.toggle_view_mode(to_advanced_mode, from_load=False)

    def toggle_view_mode(self, to_advanced_mode, from_load=False):
        # Ham nay se duoc override o lop con de chuyen view_stack.currentWidget()
        self.custom_title_bar.set_mode_button_state(to_advanced_mode)
        if not from_load:
            self._retranslate_base_ui() 

    def _retranslate_base_ui(self):
        self.custom_title_bar.retranslate_ui_texts()
        if self.original_pixmap.isNull():
            if not hasattr(self, "_bg_error_logged") or self._bg_error_logged != Translations.current_lang:
                print(Translations.get("error_loading_background_msg_console", path=self.background_image_path))
                self._bg_error_logged = Translations.current_lang
            self.background_label.setText(Translations.get("error_loading_background_ui"))
        # Cac page se tu retranslate UI cua chung

    @Slot(str)
    def _handle_language_change(self, lang_code):
        Translations.set_language(lang_code)
        # Lop con (AutoTyperWindow) se override ham nay de goi retranslate cho cac page
        self._retranslate_base_ui()
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

    def _update_background_pixmap(self):
        if hasattr(self, 'background_label') and not self.original_pixmap.isNull():
            main_area_height = self.main_container_widget.height() - self.custom_title_bar.height()
            main_area_width = self.main_container_widget.width()
            if main_area_width <= 0 or main_area_height <= 0: return
            target_size_for_bg = QSize(main_area_width, main_area_height)
            scaled_pixmap = self.original_pixmap.scaled(
                target_size_for_bg, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event): self._update_background_pixmap(); super().resizeEvent(event)

    def _get_current_resize_edge(self, local_pos: QPoint) -> int: 
        edge = NO_EDGE; rect = self.rect()
        if local_pos.x() < RESIZE_MARGIN: edge |= LEFT_EDGE
        if local_pos.x() > rect.width() - RESIZE_MARGIN: edge |= RIGHT_EDGE
        if local_pos.y() < RESIZE_MARGIN: edge |= TOP_EDGE
        if local_pos.y() > rect.height() - RESIZE_MARGIN: edge |= BOTTOM_EDGE
        return edge

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            local_pos = event.position().toPoint(); global_pos = event.globalPosition().toPoint()
            self._resize_edge = self._get_current_resize_edge(local_pos)
            is_on_title_bar_geom = self.custom_title_bar.geometry().contains(local_pos)
            if self._resize_edge != NO_EDGE and not (is_on_title_bar_geom and self._resize_edge != TOP_EDGE) :
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
                if self._resize_edge & LEFT_EDGE: new_left = start_geom.left() + delta.x(); new_width = max(min_w, start_geom.width() - delta.x()); new_geom.setLeft(start_geom.right() - new_width); new_geom.setWidth(new_width)
                if self._resize_edge & RIGHT_EDGE: new_geom.setWidth(max(min_w, start_geom.width() + delta.x()))
                if self._resize_edge & TOP_EDGE: new_top = start_geom.top() + delta.y(); new_height = max(min_h, start_geom.height() - delta.y()); new_geom.setTop(start_geom.bottom() - new_height); new_geom.setHeight(new_height)
                if self._resize_edge & BOTTOM_EDGE: new_geom.setHeight(max(min_h, start_geom.height() + delta.y()))
                self.setGeometry(new_geom); event.accept(); return
            elif self._is_dragging: self.move(event.globalPosition().toPoint() - self._drag_start_pos); event.accept(); return
        if not (self._is_resizing or self._is_dragging):
            local_pos = event.position().toPoint(); current_hover_edge = self._get_current_resize_edge(local_pos)
            is_on_interactive_title_widget = False
            interactive_widgets_on_title = self.custom_title_bar.findChildren(QPushButton) + \
                                           [self.custom_title_bar.lang_combo, self.custom_title_bar.btn_toggle_mode]
            for child_widget in interactive_widgets_on_title:
                if child_widget.isVisible() and child_widget.geometry().contains(self.custom_title_bar.mapFromGlobal(event.globalPosition().toPoint())) : is_on_interactive_title_widget = True; break
            if is_on_interactive_title_widget: self.unsetCursor()
            elif current_hover_edge == TOP_LEFT_CORNER or current_hover_edge == BOTTOM_RIGHT_CORNER: self.setCursor(Qt.SizeFDiagCursor)
            elif current_hover_edge == TOP_RIGHT_CORNER or current_hover_edge == BOTTOM_LEFT_CORNER: self.setCursor(Qt.SizeBDiagCursor)
            elif current_hover_edge & LEFT_EDGE or current_hover_edge & RIGHT_EDGE: self.setCursor(Qt.SizeHorCursor)
            elif current_hover_edge & TOP_EDGE or current_hover_edge & BOTTOM_EDGE: self.setCursor(Qt.SizeVerCursor)
            else: self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent): 
        if event.button() == Qt.LeftButton:
            changed_state = False
            if self._is_resizing: self._is_resizing = False; changed_state = True
            if self._is_dragging: self._is_dragging = False; changed_state = True
            if changed_state: self._resize_edge = NO_EDGE; self.unsetCursor(); event.accept(); return
        super().mouseReleaseEvent(event)

    def _cleanup_thread_worker(self, thread_attr_name, worker_attr_name, target_obj=None):
        obj_to_cleanup = target_obj if target_obj else self
        worker = getattr(obj_to_cleanup, worker_attr_name, None)
        thread = getattr(obj_to_cleanup, thread_attr_name, None)
        if worker and hasattr(worker, 'request_stop'): worker.request_stop()
        if thread and thread.isRunning():
            thread.quit()
            if not thread.wait(1000): thread.terminate(); thread.wait()
        if hasattr(obj_to_cleanup, worker_attr_name): setattr(obj_to_cleanup, worker_attr_name, None)
        if hasattr(obj_to_cleanup, thread_attr_name): setattr(obj_to_cleanup, thread_attr_name, None)

    def _serialize_key(self, key_obj): 
        if isinstance(key_obj, PynputKey): return {"type": "special", "value": key_obj.name}
        elif isinstance(key_obj, KeyCode):
            if key_obj.char is not None: return {"type": "keycode_char", "value": key_obj.char}
            elif hasattr(key_obj, 'vk'): return {"type": "keycode_vk", "value": key_obj.vk}
        elif isinstance(key_obj, str): return {"type": "char_str", "value": key_obj}
        return None

    def _deserialize_key(self, key_data): 
        if not key_data or "type" not in key_data or "value" not in key_data: return None
        key_type, key_value = key_data["type"], key_data["value"]
        try:
            if key_type == "special": return getattr(PynputKey, key_value)
            elif key_type == "keycode_char": return KeyCode.from_char(key_value)
            elif key_type == "keycode_vk": return KeyCode.from_vk(key_value)
            elif key_type == "char_str": return KeyCode.from_char(key_value)
        except (AttributeError, Exception): return None
        return None

    def _load_settings(self): # Ham nay se duoc goi boi lop con
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
           
                return settings 
            else:
                print(Translations.get("config_file_not_found", filepath=self.config_path))
        except Exception as e:
            print(Translations.get("config_loaded_error", filepath=self.config_path, error=str(e)))
        return {} # Tra ve dict rong neu co loi hoac file ko ton tai

    def _save_settings(self, settings_dict):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(Translations.get("config_saved_error", filepath=self.config_path, error=str(e)))

    def show_countdown_overlay(self, text):
        if not self.countdown_overlay: self.countdown_overlay = CountdownOverlay(None)
        self.countdown_overlay.setText(text)
        if not self.countdown_overlay.isVisible():
            self.countdown_overlay.show(); self.countdown_overlay.activateWindow(); self.countdown_overlay.raise_()

    def hide_countdown_overlay(self):
        if self.countdown_overlay and self.countdown_overlay.isVisible(): self.countdown_overlay.hide()

    def closeEvent(self, event):

        if self.single_key_listener_worker: self.single_key_listener_worker.request_stop_worker_thread()
        if self.single_key_listener_thread:
            self.single_key_listener_thread.quit()
            if not self.single_key_listener_thread.wait(1500): self.single_key_listener_thread.terminate(); self.single_key_listener_thread.wait()
        self.single_key_listener_worker = None; self.single_key_listener_thread = None
        if self.countdown_overlay: self.countdown_overlay.close(); self.countdown_overlay = None
