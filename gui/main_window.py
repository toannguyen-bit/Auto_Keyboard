# gui/main_window.py
import os
import json
from PySide6.QtWidgets import QMessageBox, QGraphicsOpacityEffect, QFileDialog
from PySide6.QtCore import Slot, QPropertyAnimation, QEasingCurve, QAbstractAnimation, QRect

from core.translations import Translations
from .base_main_window import BaseMainWindow
from .autotyper_page import AutoTyperPageWidget
from .recorder_page import RecorderPageWidget
from .constants import SETTING_MAIN_HOTKEY, SETTING_START_RECORD_HOTKEY, SETTING_PLAY_RECORD_HOTKEY

class AutoTyperWindow(BaseMainWindow):
    def __init__(self, base_path):
        super().__init__(base_path) # Goi __init__ cua BaseMainWindow

        # Tao cac page sau khi BaseMainWindow da khoi tao xong (de custom_title_bar co san)
        self.autotyper_page = AutoTyperPageWidget(self)
        self.recorder_page = RecorderPageWidget(self)

        self.view_stack.addWidget(self.autotyper_page)
        self.view_stack.addWidget(self.recorder_page)

        self._connect_page_signals()

        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured_generic)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error_generic)
        self.single_key_listener_worker.listener_operation_finished_signal.connect(self._on_single_key_listener_operation_finished_generic)

        self.page_transition_animation_out = None
        self.page_transition_animation_in = None
        self._current_widget_for_transition = None 

        self._load_settings_extended() # Load config (bao gom ngon ngu)


    def _connect_page_signals(self):
        self.autotyper_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.autotyper_page.update_window_title_signal.connect(self._update_main_window_title_from_autotyper_page)
        self.autotyper_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)

        self.recorder_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.recorder_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)
        self.recorder_page.request_countdown_overlay_signal.connect(self._handle_countdown_overlay_request)

    def _gather_all_current_settings(self):
        # Thu thap tat ca setting tu app va cac page
        settings_dict = {
            "language": Translations.current_lang,
            "window_geometry": self.geometry().getRect() if not self.isMaximized() else self.normalGeometry().getRect(),
            "window_maximized": self.isMaximized(),
            "advanced_mode_active": self.view_stack.currentWidget() == self.recorder_page,
        }
        self.autotyper_page.save_settings(settings_dict)
        self.recorder_page.save_settings(settings_dict)
        return settings_dict

    def _apply_app_specific_settings(self, settings_data):
        # Ap dung cac setting lien quan den page va view mode
        if not settings_data: # Neu settings_data la None hoac rong
            settings_data = {} # Su dung dict rong de cac page load gia tri mac dinh

        self.autotyper_page.load_settings(settings_data)
        self.recorder_page.load_settings(settings_data)

        is_advanced_mode = settings_data.get("advanced_mode_active", False)
        # Quan trong: Goi toggle_view_mode voi from_load=True de tranh anim khong can thiet khi moi load
        self.toggle_view_mode(is_advanced_mode, from_load=True)


    def _full_ui_refresh(self):
        # Goi sau khi da ap dung tat ca settings (bao gom ngon ngu)
        self._retranslate_ui_extended()
        self._update_all_controls_state()
        self.apply_styles() # Ap lai style (neu font thay doi theo ngon ngu)


    def _load_settings_extended(self):
        # Load config ban dau (tu self.config_path cua BaseMainWindow)
        settings_data = super()._load_initial_config() # Method nay da handle ngon ngu, geom
        self._apply_app_specific_settings(settings_data)
        self._full_ui_refresh()


    def _save_settings(self): # Duoc goi khi dong app
        settings_dict = self._gather_all_current_settings()
        super()._save_config_to_default_path(settings_dict) # Luu vao self.config_path


    @Slot() # Override tu BaseMainWindow
    def _handle_load_config_requested(self):
        if self.is_setting_hotkey_type != 0: # Neu dang set hotkey, ko cho load
             QMessageBox.warning(self, Translations.get("msgbox_error_set_hotkey_title"), "Hoàn tất hoặc hủy cài đặt hotkey trước khi tải cấu hình mới.")
             if self.single_key_listener_worker: self.single_key_listener_worker.cancel_current_listening_operation()
             return

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            Translations.get("msgbox_load_config_title"),
            os.path.dirname(self.config_path), # Mo tai thu muc config hien tai
            Translations.get("file_dialog_json_filter")
        )
        if filepath:
            new_settings_data = self._read_settings_from_file(filepath) # Goi method cua BaseMainWindow
            if new_settings_data:
                self.config_path = filepath # Cap nhat duong dan config hien tai
                self._apply_base_window_settings(new_settings_data) # Ap dung lang, geom
                self._apply_app_specific_settings(new_settings_data) # Ap dung cho pages
                self._full_ui_refresh() # Cap nhat toan bo UI

                QMessageBox.information(self, Translations.get("msgbox_load_success_title"),
                                        Translations.get("msgbox_load_success_text", filename=os.path.basename(filepath)))
            # Neu _read_settings_from_file tra ve None, no da show error roi

    @Slot() # Override tu BaseMainWindow
    def _handle_save_config_as_requested(self):
        if self.is_setting_hotkey_type != 0: # Neu dang set hotkey, ko cho save
             QMessageBox.warning(self, Translations.get("msgbox_error_set_hotkey_title"), "Hoàn tất hoặc hủy cài đặt hotkey trước khi lưu cấu hình.")
             if self.single_key_listener_worker: self.single_key_listener_worker.cancel_current_listening_operation()
             return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            Translations.get("msgbox_save_config_as_title"),
            os.path.join(os.path.dirname(self.config_path), os.path.basename(self.config_path) or "autokeyboard_config.json"),
            Translations.get("file_dialog_json_filter")
        )
        if filepath:
            if not filepath.lower().endswith(".json"): filepath += ".json" # Dam bao duoi .json
            
            current_settings = self._gather_all_current_settings()
            if self._write_settings_to_file(filepath, current_settings): # Goi method cua BaseMainWindow
                self.config_path = filepath # Cap nhat duong dan config hien tai
                QMessageBox.information(self, Translations.get("msgbox_save_success_title"),
                                        Translations.get("msgbox_save_success_text", filename=os.path.basename(filepath)))

    @Slot() # Override tu BaseMainWindow
    def _handle_save_current_config_requested(self):
        if self.is_setting_hotkey_type != 0: # Neu dang set hotkey, ko cho save
             QMessageBox.warning(self, Translations.get("msgbox_error_set_hotkey_title"), "Hoàn tất hoặc hủy cài đặt hotkey trước khi lưu cấu hình.")
             if self.single_key_listener_worker: self.single_key_listener_worker.cancel_current_listening_operation()
             return

        current_settings = self._gather_all_current_settings()
        if self._write_settings_to_file(self.config_path, current_settings): # Luu vao self.config_path
            QMessageBox.information(self, Translations.get("msgbox_save_success_title"),
                                    Translations.get("msgbox_save_success_text", filename=os.path.basename(self.config_path)))


    # Slot _handle_language_change_from_combobox da duoc BaseMainWindow xu ly Translations.set_language
    @Slot(str) 
    def _handle_language_change_from_combobox(self, lang_code): 
        super()._handle_language_change_from_combobox(lang_code) 
        self._full_ui_refresh()


    def _get_or_create_opacity_effect(self, widget):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

    def toggle_view_mode(self, to_advanced_mode, from_load=False): # Override + Anim
        current_widget_on_stack = self.view_stack.currentWidget()
        target_widget = self.recorder_page if to_advanced_mode else self.autotyper_page

        # Cap nhat trang thai nut toggle tren title bar
        self.custom_title_bar.set_mode_button_state(to_advanced_mode)


        if current_widget_on_stack == target_widget:
            # Goi _retranslate_ui_extended chi khi khong phai from_load, vi from_load se co _full_ui_refresh sau
            if not from_load:
                self._retranslate_ui_extended() # Can de cap nhat title window, etc.
                self._update_all_controls_state()
            return

        if from_load: # Khi load tu config, chi chuyen trang, ko anim
            self.view_stack.setCurrentWidget(target_widget)
            # Cac buoc retranslate va update controls se duoc goi boi _full_ui_refresh
            return

        # Dung anim cu neu co
        if self.page_transition_animation_out and self.page_transition_animation_out.state() == QAbstractAnimation.State.Running:
            self.page_transition_animation_out.stop()
        if self.page_transition_animation_in and self.page_transition_animation_in.state() == QAbstractAnimation.State.Running:
            self.page_transition_animation_in.stop()

        # Reset opacity cua widget (neu co effect tu lan truoc)
        if current_widget_on_stack.graphicsEffect():
            current_widget_on_stack.graphicsEffect().setOpacity(1.0)
            current_widget_on_stack.graphicsEffect().setEnabled(False)
        if target_widget.graphicsEffect():
            target_widget.graphicsEffect().setOpacity(1.0) 
            target_widget.graphicsEffect().setEnabled(False)

        self._current_widget_for_transition = current_widget_on_stack
        effect_out = self._get_or_create_opacity_effect(self._current_widget_for_transition)
        effect_out.setEnabled(True)

        self.page_transition_animation_out = QPropertyAnimation(effect_out, b"opacity", self)
        self.page_transition_animation_out.setDuration(180) 
        self.page_transition_animation_out.setStartValue(1.0)
        self.page_transition_animation_out.setEndValue(0.0)
        self.page_transition_animation_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.page_transition_animation_out.finished.connect(
            lambda: self._start_fade_in_transition(target_widget) # Khong can to_advanced_mode nua
        )
        
        self.custom_title_bar.btn_toggle_mode.setEnabled(False) 
        self.page_transition_animation_out.start()


    def _start_fade_in_transition(self, target_widget):
        if self._current_widget_for_transition and self._current_widget_for_transition.graphicsEffect():
            self._current_widget_for_transition.graphicsEffect().setEnabled(False) 

        self._current_widget_for_transition = target_widget 
        effect_in = self._get_or_create_opacity_effect(self._current_widget_for_transition)
        effect_in.setOpacity(0.0) 
        effect_in.setEnabled(True)

        self.view_stack.setCurrentWidget(target_widget)

        self._retranslate_ui_extended() # Dich lai UI cho trang moi
        self._update_all_controls_state() # Cap nhat trang thai control cho trang moi

        self.page_transition_animation_in = QPropertyAnimation(effect_in, b"opacity", self)
        self.page_transition_animation_in.setDuration(220) 
        self.page_transition_animation_in.setStartValue(0.0)
        self.page_transition_animation_in.setEndValue(1.0)
        self.page_transition_animation_in.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.page_transition_animation_in.finished.connect(self._finish_page_transition)
        self.page_transition_animation_in.start()

    def _finish_page_transition(self):
        if self._current_widget_for_transition and self._current_widget_for_transition.graphicsEffect():
            self._current_widget_for_transition.graphicsEffect().setEnabled(False) 
        
        self._current_widget_for_transition = None 
        self.custom_title_bar.btn_toggle_mode.setEnabled(self.is_setting_hotkey_type == 0)


    def _retranslate_ui_extended(self): # Goi de dich lai toan bo UI cua app
        super()._retranslate_base_ui() # Dich cac thanh phan cua BaseMainWindow (vd: title bar buttons)
        current_widget = self.view_stack.currentWidget()
        
        if current_widget == self.autotyper_page:
            self.setWindowTitle(Translations.get("window_title")) # Set window title chung
            self.autotyper_page.retranslate_ui()
        elif current_widget == self.recorder_page:
            self.setWindowTitle(Translations.get("label_record_play_group")) # Set window title chung
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group")) # Cap nhat label tren title bar
            self.recorder_page.retranslate_ui()
        
        # Dam bao title bar luon duoc cap nhat text (cho cac nut config, mode, ngon ngu)
        if hasattr(self.custom_title_bar, 'retranslate_ui_texts'):
            self.custom_title_bar.retranslate_ui_texts()

    @Slot(str)
    def _update_main_window_title_from_autotyper_page(self, title_text):
        if self.view_stack.currentWidget() == self.autotyper_page:
             self.custom_title_bar.setTitle(title_text)

    @Slot(bool, int)
    def _on_page_setting_hotkey_status_changed(self, is_setting, hotkey_type):
        is_transitioning = (self.page_transition_animation_out and self.page_transition_animation_out.state() == QAbstractAnimation.State.Running) or \
                           (self.page_transition_animation_in and self.page_transition_animation_in.state() == QAbstractAnimation.State.Running)
        if not is_transitioning:
            self.custom_title_bar.btn_toggle_mode.setEnabled(not is_setting)
            self.custom_title_bar.btn_load_config.setEnabled(not is_setting)
            self.custom_title_bar.btn_save_config_as.setEnabled(not is_setting)
            self.custom_title_bar.btn_save_current_config.setEnabled(not is_setting)
        self._update_all_controls_state()

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
        conflict = False; conflict_desc = ""
        if hotkey_type_captured != SETTING_MAIN_HOTKEY and self.autotyper_page.current_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_autotyper")
        if not conflict and hotkey_type_captured != SETTING_START_RECORD_HOTKEY and self.recorder_page.current_start_record_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_record")
        if not conflict and hotkey_type_captured != SETTING_PLAY_RECORD_HOTKEY and self.recorder_page.current_play_record_hotkey == key_obj:
            conflict=True; conflict_desc=Translations.get("action_description_play")

        if conflict:
            QMessageBox.warning(self, Translations.get("msgbox_hotkey_conflict_title"), Translations.get("msgbox_hotkey_conflict_text", new_hotkey_name=key_name, action_description=conflict_desc))
            # Van goi _on_single_key_listener_operation_finished_generic de reset trang thai
            # Nhung khong cap nhat hotkey
            if self.single_key_listener_worker: 
                self.single_key_listener_worker.cancel_current_listening_operation()
            return 


        QMessageBox.information(self, Translations.get("msgbox_hotkey_set_title"), Translations.get("msgbox_hotkey_set_text", new_hotkey_name=key_name))
        if hotkey_type_captured == SETTING_MAIN_HOTKEY: self.autotyper_page.on_new_hotkey_captured(key_obj, key_name)
        elif hotkey_type_captured == SETTING_START_RECORD_HOTKEY: self.recorder_page.on_new_hotkey_captured(SETTING_START_RECORD_HOTKEY, key_obj, key_name)
        elif hotkey_type_captured == SETTING_PLAY_RECORD_HOTKEY: self.recorder_page.on_new_hotkey_captured(SETTING_PLAY_RECORD_HOTKEY, key_obj, key_name)


    @Slot(int, str)
    def _handle_set_hotkey_error_generic(self, hotkey_type_errored, error_message):
        if self.is_setting_hotkey_type != hotkey_type_errored: return
        QMessageBox.critical(self, Translations.get("msgbox_error_set_hotkey_title"), error_message)

    @Slot(int)
    def _on_single_key_listener_operation_finished_generic(self, hotkey_type_finished):
        # Slot nay duoc goi khi listener ket thuc (bat phim, loi, hoac huy)
        if self.is_setting_hotkey_type != hotkey_type_finished: 
            return

        original_setting_type = self.is_setting_hotkey_type
        self.is_setting_hotkey_type = 0

        if original_setting_type == SETTING_MAIN_HOTKEY: self.autotyper_page.on_set_hotkey_finished_or_cancelled(SETTING_MAIN_HOTKEY)
        elif original_setting_type == SETTING_START_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_START_RECORD_HOTKEY)
        elif original_setting_type == SETTING_PLAY_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_PLAY_RECORD_HOTKEY)

        self._update_all_controls_state()

    def _update_all_controls_state(self):
        self.autotyper_page._update_controls_state()
        self.recorder_page._update_controls_state()
        
        is_any_page_busy = self.autotyper_page.is_typing_active or \
                           self.recorder_page.is_recording or \
                           self.recorder_page.is_playing_recording
                           
        is_setting_any_hotkey = self.is_setting_hotkey_type != 0

        can_interact_with_config = not is_any_page_busy and not is_setting_any_hotkey
        
        is_transitioning = (self.page_transition_animation_out and self.page_transition_animation_out.state() == QAbstractAnimation.State.Running) or \
                           (self.page_transition_animation_in and self.page_transition_animation_in.state() == QAbstractAnimation.State.Running)
        
        enable_title_bar_buttons = not is_setting_any_hotkey and not is_transitioning

        self.custom_title_bar.btn_toggle_mode.setEnabled(enable_title_bar_buttons and not is_any_page_busy)
        self.custom_title_bar.btn_load_config.setEnabled(enable_title_bar_buttons and not is_any_page_busy)
        self.custom_title_bar.btn_save_config_as.setEnabled(enable_title_bar_buttons and not is_any_page_busy)
        self.custom_title_bar.btn_save_current_config.setEnabled(enable_title_bar_buttons and not is_any_page_busy)
        self.custom_title_bar.lang_combo.setEnabled(enable_title_bar_buttons and not is_any_page_busy)


    def closeEvent(self, event): # Override
        self._save_settings() # Luu cau hinh hien tai vao self.config_path
        self.autotyper_page.cleanup_resources()
        self.recorder_page.cleanup_resources()
        super().closeEvent(event) 