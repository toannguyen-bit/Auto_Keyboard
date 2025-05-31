# gui/main_window.py
import os 
import json 
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Slot

from core.translations import Translations
from .base_main_window import BaseMainWindow
from .autotyper_page import AutoTyperPageWidget
from .recorder_page import RecorderPageWidget
from .constants import SETTING_MAIN_HOTKEY, SETTING_START_RECORD_HOTKEY, SETTING_PLAY_RECORD_HOTKEY

class AutoTyperWindow(BaseMainWindow):
    def __init__(self, base_path):
        super().__init__(base_path) # Goi __init__ cua BaseMainWindow

        self.autotyper_page = AutoTyperPageWidget(self)
        self.recorder_page = RecorderPageWidget(self)

        self.view_stack.addWidget(self.autotyper_page)
        self.view_stack.addWidget(self.recorder_page)

        self._connect_page_signals()

        # Connect SingleKeyListenerWorker (tu BaseMainWindow) den cac handler o day
        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured_generic)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error_generic)
        self.single_key_listener_worker.listener_operation_finished_signal.connect(self._on_single_key_listener_operation_finished_generic)

        self._load_settings_extended() # Load settings cho base va cac page
        self._retranslate_ui_extended() # Retranslate toan bo UI
        self._update_all_controls_state() # Cap nhat trang thai control ban dau

    def _connect_page_signals(self):
        self.autotyper_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.autotyper_page.update_window_title_signal.connect(self._update_main_window_title_from_autotyper_page)
        self.autotyper_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)

        self.recorder_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.recorder_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)
        self.recorder_page.request_countdown_overlay_signal.connect(self._handle_countdown_overlay_request)

    def _load_settings_extended(self):
        # BaseMainWindow._load_settings() da load ngon ngu, geometry
        # Gio load them cho cac page
        settings_data = super()._load_settings() # Goi ham cua base de load va lay data

        self.autotyper_page.load_settings(settings_data)
        self.recorder_page.load_settings(settings_data)

        is_advanced_mode = settings_data.get("advanced_mode_active", False)
        # Goi toggle_view_mode cua AutoTyperWindow (da override)
        self.toggle_view_mode(is_advanced_mode, from_load=True)

    def _save_settings(self): # Override ham cua BaseMainWindow
        settings_dict = { # Settings co ban
            "language": Translations.current_lang,
            "window_geometry": self.geometry().getRect() if not self.isMaximized() else self.normalGeometry().getRect(),
            "window_maximized": self.isMaximized(),
            "advanced_mode_active": self.view_stack.currentWidget() == self.recorder_page,
        }
        self.autotyper_page.save_settings(settings_dict)
        self.recorder_page.save_settings(settings_dict)
        super()._save_settings(settings_dict) # Goi ham cua base de luu vao file

    @Slot(str) # Override tu BaseMainWindow
    def _handle_language_change(self, lang_code):
        super()._handle_language_change(lang_code) # Goi base de set ngon ngu, style
        self._retranslate_ui_extended() # Goi retranslate cua lop nay

    def toggle_view_mode(self, to_advanced_mode, from_load=False): # Override BaseMainWindow
        super().toggle_view_mode(to_advanced_mode, from_load) # Goi base de set button state

        current_target_widget = self.recorder_page if to_advanced_mode else self.autotyper_page
        if self.view_stack.currentWidget() != current_target_widget or from_load:
            self.view_stack.setCurrentWidget(current_target_widget)

        if not from_load: # Chi retranslate/update control neu ko phai tu luc load
            self._retranslate_ui_extended()
            self._update_all_controls_state()

    def _retranslate_ui_extended(self): # Override
        super()._retranslate_base_ui() # Retranslate base UI
        current_widget = self.view_stack.currentWidget()
        if current_widget == self.autotyper_page:
            self.setWindowTitle(Translations.get("window_title")) # Title chinh cho app
            self.autotyper_page.retranslate_ui() # Page se emit signal de cap nhat title bar text
        elif current_widget == self.recorder_page:
            self.setWindowTitle(Translations.get("label_record_play_group")) # Title chinh
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group")) # Title bar text
            self.recorder_page.retranslate_ui()
        if hasattr(self.custom_title_bar, 'retranslate_ui_texts'): # Dam bao title bar cap nhat
            self.custom_title_bar.retranslate_ui_texts()

    @Slot(str)
    def _update_main_window_title_from_autotyper_page(self, title_text):
        # Chi cap nhat title bar neu autotyper page dang hien thi
        if self.view_stack.currentWidget() == self.autotyper_page:
             self.custom_title_bar.setTitle(title_text)

    @Slot(bool, int) # is_setting, hotkey_type
    def _on_page_setting_hotkey_status_changed(self, is_setting, hotkey_type):
        # Khi mot page bat dau/ket thuc set hotkey, vo hieu hoa nut chuyen mode
        self.custom_title_bar.btn_toggle_mode.setEnabled(not is_setting)
        self._update_all_controls_state() # Cap nhat lai trang thai cua cac page

    @Slot(bool, str)
    def _handle_countdown_overlay_request(self, show, text):
        if show: self.show_countdown_overlay(text)
        else: self.hide_countdown_overlay()

    @Slot(int)
    def _activate_single_key_listener(self, hotkey_type_to_set):
        if self.single_key_listener_worker:
            self.single_key_listener_worker.activate_listener_for_hotkey_type(hotkey_type_to_set)

    @Slot(int, object, str)
    def _handle_new_hotkey_captured_generic(self, hotkey_type_captured, key_obj, key_name):
        # Kiem tra xung dot
        conflict = False; conflict_desc = ""
        # Check voi Autotyper
        if hotkey_type_captured != SETTING_MAIN_HOTKEY and self.autotyper_page.current_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_autotyper")
        # Check voi Record
        if not conflict and hotkey_type_captured != SETTING_START_RECORD_HOTKEY and self.recorder_page.current_start_record_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_record")
        # Check voi Play
        if not conflict and hotkey_type_captured != SETTING_PLAY_RECORD_HOTKEY and self.recorder_page.current_play_record_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_play")

        if conflict:
            QMessageBox.warning(self, Translations.get("msgbox_hotkey_conflict_title"), Translations.get("msgbox_hotkey_conflict_text", new_hotkey_name=key_name, action_description=conflict_desc))
            # Listener se tu ket thuc, _on_single_key_listener_operation_finished_generic se duoc goi
            return

        QMessageBox.information(self, Translations.get("msgbox_hotkey_set_title"), Translations.get("msgbox_hotkey_set_text", new_hotkey_name=key_name))
        # Phan phoi hotkey moi cho page tuong ung
        if hotkey_type_captured == SETTING_MAIN_HOTKEY: self.autotyper_page.on_new_hotkey_captured(key_obj, key_name)
        elif hotkey_type_captured == SETTING_START_RECORD_HOTKEY: self.recorder_page.on_new_hotkey_captured(SETTING_START_RECORD_HOTKEY, key_obj, key_name)
        elif hotkey_type_captured == SETTING_PLAY_RECORD_HOTKEY: self.recorder_page.on_new_hotkey_captured(SETTING_PLAY_RECORD_HOTKEY, key_obj, key_name)
        # Listener se tu ket thuc, _on_single_key_listener_operation_finished_generic se duoc goi de reset UI

    @Slot(int, str)
    def _handle_set_hotkey_error_generic(self, hotkey_type_errored, error_message):
        if self.is_setting_hotkey_type != hotkey_type_errored: return # Bo qua neu ko phai loi cua hotkey dang set
        QMessageBox.critical(self, Translations.get("msgbox_error_set_hotkey_title"), error_message)
        # Listener se tu ket thuc, _on_single_key_listener_operation_finished_generic se duoc goi

    @Slot(int)
    def _on_single_key_listener_operation_finished_generic(self, hotkey_type_finished):
        if self.is_setting_hotkey_type != hotkey_type_finished: return # Neu da bi huy/thay doi
        
        original_setting_type = self.is_setting_hotkey_type
        self.is_setting_hotkey_type = 0 # Reset o day, quan trong!

        if original_setting_type == SETTING_MAIN_HOTKEY: self.autotyper_page.on_set_hotkey_finished_or_cancelled(SETTING_MAIN_HOTKEY)
        elif original_setting_type == SETTING_START_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_START_RECORD_HOTKEY)
        elif original_setting_type == SETTING_PLAY_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_PLAY_RECORD_HOTKEY)
        
        self._update_all_controls_state() # Cap nhat lai UI cua cac page va nut toggle mode

    def _update_all_controls_state(self):
        self.autotyper_page._update_controls_state()
        self.recorder_page._update_controls_state()
        self.custom_title_bar.btn_toggle_mode.setEnabled(self.is_setting_hotkey_type == 0)

    def closeEvent(self, event): # Override
        self._save_settings() # Goi ham save cua AutoTyperWindow (da override)
        self.autotyper_page.cleanup_resources()
        self.recorder_page.cleanup_resources()
        super().closeEvent(event) # Goi ham cua BaseMainWindow de cleanup SingleKeyListener, overlay
        event.accept() # Dam bao event duoc accept