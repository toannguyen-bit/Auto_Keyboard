# gui/main_window.py
import os
import json
from PySide6.QtWidgets import QMessageBox, QGraphicsOpacityEffect
from PySide6.QtCore import Slot, QPropertyAnimation, QEasingCurve, QAbstractAnimation

from core.translations import Translations
from .base_main_window import BaseMainWindow
from .autotyper_page import AutoTyperPageWidget
from .recorder_page import RecorderPageWidget
from .constants import SETTING_MAIN_HOTKEY, SETTING_START_RECORD_HOTKEY, SETTING_PLAY_RECORD_HOTKEY

class AutoTyperWindow(BaseMainWindow):
    def __init__(self, base_path):
        super().__init__(base_path)

        self.autotyper_page = AutoTyperPageWidget(self)
        self.recorder_page = RecorderPageWidget(self)

        self.view_stack.addWidget(self.autotyper_page)
        self.view_stack.addWidget(self.recorder_page)

        self._connect_page_signals()

        self.single_key_listener_worker.key_captured_signal.connect(self._handle_new_hotkey_captured_generic)
        self.single_key_listener_worker.error_signal.connect(self._handle_set_hotkey_error_generic)
        self.single_key_listener_worker.listener_operation_finished_signal.connect(self._on_single_key_listener_operation_finished_generic)

        # Animations chuyen page
        self.page_transition_animation_out = None
        self.page_transition_animation_in = None
        self._current_widget_for_transition = None # Luu widget dang fade out/in

        self._load_settings_extended()
        self._retranslate_ui_extended()
        self._update_all_controls_state()

    def _connect_page_signals(self):
        self.autotyper_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.autotyper_page.update_window_title_signal.connect(self._update_main_window_title_from_autotyper_page)
        self.autotyper_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)

        self.recorder_page.request_single_key_listener_signal.connect(self._activate_single_key_listener)
        self.recorder_page.setting_hotkey_status_changed_signal.connect(self._on_page_setting_hotkey_status_changed)
        self.recorder_page.request_countdown_overlay_signal.connect(self._handle_countdown_overlay_request)

    def _load_settings_extended(self):
        settings_data = super()._load_settings()

        self.autotyper_page.load_settings(settings_data)
        self.recorder_page.load_settings(settings_data)

        is_advanced_mode = settings_data.get("advanced_mode_active", False)
        self.toggle_view_mode(is_advanced_mode, from_load=True)

    def _save_settings(self):
        settings_dict = {
            "language": Translations.current_lang,
            "window_geometry": self.geometry().getRect() if not self.isMaximized() else self.normalGeometry().getRect(),
            "window_maximized": self.isMaximized(),
            "advanced_mode_active": self.view_stack.currentWidget() == self.recorder_page,
        }
        self.autotyper_page.save_settings(settings_dict)
        self.recorder_page.save_settings(settings_dict)
        super()._save_settings(settings_dict)

    @Slot(str)
    def _handle_language_change(self, lang_code):
        super()._handle_language_change(lang_code)
        self._retranslate_ui_extended()

    def _get_or_create_opacity_effect(self, widget):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

    def toggle_view_mode(self, to_advanced_mode, from_load=False): # Override + Anim
        current_widget_on_stack = self.view_stack.currentWidget()
        target_widget = self.recorder_page if to_advanced_mode else self.autotyper_page

        if current_widget_on_stack == target_widget:
            super().toggle_view_mode(to_advanced_mode, from_load) # Goi base de cap nhat nut toggle
            if not from_load:
                self._retranslate_ui_extended()
                self._update_all_controls_state()
            return

        if from_load:
            super().toggle_view_mode(to_advanced_mode, from_load)
            self.view_stack.setCurrentWidget(target_widget)
            self._retranslate_ui_extended()
            self._update_all_controls_state()
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
            target_widget.graphicsEffect().setOpacity(1.0) # Hoac 0.0 tuy logic reset
            target_widget.graphicsEffect().setEnabled(False)

        # --- Anim chuyen trang ---
        self._current_widget_for_transition = current_widget_on_stack
        effect_out = self._get_or_create_opacity_effect(self._current_widget_for_transition)
        effect_out.setEnabled(True)

        self.page_transition_animation_out = QPropertyAnimation(effect_out, b"opacity", self)
        self.page_transition_animation_out.setDuration(180) # ms
        self.page_transition_animation_out.setStartValue(1.0)
        self.page_transition_animation_out.setEndValue(0.0)
        self.page_transition_animation_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Ket noi finished signal de bat dau fade in
        self.page_transition_animation_out.finished.connect(
            lambda: self._start_fade_in_transition(target_widget, to_advanced_mode, from_load)
        )
        
        self.custom_title_bar.btn_toggle_mode.setEnabled(False) # Vo hieu hoa nut khi dang chuyen
        self.page_transition_animation_out.start()


    def _start_fade_in_transition(self, target_widget, to_advanced_mode, from_load_param_not_used_here):
        if self._current_widget_for_transition and self._current_widget_for_transition.graphicsEffect():
            self._current_widget_for_transition.graphicsEffect().setEnabled(False) # Tat effect trang cu
            # Opacity da la 0.0 tu anim out, khong can set lai 1.0 o day

        # Chuan bi trang moi
        self._current_widget_for_transition = target_widget # Gio la trang moi
        effect_in = self._get_or_create_opacity_effect(self._current_widget_for_transition)
        effect_in.setOpacity(0.0) # Bat dau tu mo
        effect_in.setEnabled(True)

        super(AutoTyperWindow, self).toggle_view_mode(to_advanced_mode, False) # Goi base de cap nhat nut toggle
        self.view_stack.setCurrentWidget(target_widget)

        self._retranslate_ui_extended()
        self._update_all_controls_state()

        self.page_transition_animation_in = QPropertyAnimation(effect_in, b"opacity", self)
        self.page_transition_animation_in.setDuration(220) # ms
        self.page_transition_animation_in.setStartValue(0.0)
        self.page_transition_animation_in.setEndValue(1.0)
        self.page_transition_animation_in.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.page_transition_animation_in.finished.connect(self._finish_page_transition)
        self.page_transition_animation_in.start()

    def _finish_page_transition(self):
        if self._current_widget_for_transition and self._current_widget_for_transition.graphicsEffect():
            self._current_widget_for_transition.graphicsEffect().setEnabled(False) # Tat effect trang hien tai
            # Opacity da la 1.0 tu anim in
        
        self._current_widget_for_transition = None # Xoa ref
        # Kich hoat lai nut toggle mode (neu khong co hotkey nao dang duoc set)
        self.custom_title_bar.btn_toggle_mode.setEnabled(self.is_setting_hotkey_type == 0)


    def _retranslate_ui_extended(self):
        super()._retranslate_base_ui()
        current_widget = self.view_stack.currentWidget()
        if current_widget == self.autotyper_page:
            self.setWindowTitle(Translations.get("window_title"))
            self.autotyper_page.retranslate_ui()
        elif current_widget == self.recorder_page:
            self.setWindowTitle(Translations.get("label_record_play_group"))
            self.custom_title_bar.setTitle(Translations.get("label_record_play_group"))
            self.recorder_page.retranslate_ui()
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
        if self.is_setting_hotkey_type != hotkey_type_finished: return

        original_setting_type = self.is_setting_hotkey_type
        self.is_setting_hotkey_type = 0

        if original_setting_type == SETTING_MAIN_HOTKEY: self.autotyper_page.on_set_hotkey_finished_or_cancelled(SETTING_MAIN_HOTKEY)
        elif original_setting_type == SETTING_START_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_START_RECORD_HOTKEY)
        elif original_setting_type == SETTING_PLAY_RECORD_HOTKEY: self.recorder_page.on_set_hotkey_finished_or_cancelled(SETTING_PLAY_RECORD_HOTKEY)

        self._update_all_controls_state()

    def _update_all_controls_state(self):
        self.autotyper_page._update_controls_state()
        self.recorder_page._update_controls_state()
        # Ktra xem co dang chuyen trang ko
        is_transitioning = (self.page_transition_animation_out and self.page_transition_animation_out.state() == QAbstractAnimation.State.Running) or \
                           (self.page_transition_animation_in and self.page_transition_animation_in.state() == QAbstractAnimation.State.Running)
        if not is_transitioning: # Chi cap nhat neu ko chuyen trang
             self.custom_title_bar.btn_toggle_mode.setEnabled(self.is_setting_hotkey_type == 0)


    def closeEvent(self, event): # Override
        self._save_settings()
        self.autotyper_page.cleanup_resources()
        self.recorder_page.cleanup_resources()
        super().closeEvent(event) # Goi BaseMainWindow.closeEvent de xu ly anim dong