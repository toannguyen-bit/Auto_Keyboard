# core/workers.py
import time
from PySide6.QtCore import QObject, Signal, Slot, QThread 
from pynput.keyboard import Controller as PynputController, Listener as PynputListener, Key as PynputKey
from .translations import Translations 

# --- Ham tien ich lay ten hien thi cho Pynput Key ---
def get_pynput_key_display_name(key_obj):
    try:
        if isinstance(key_obj, PynputKey): # Phim dac biet
            name = key_obj.name
            name_map = {
                'alt_l': 'Alt', 'alt_r': 'Alt', 'alt_gr': 'AltGr',
                'ctrl_l': 'Ctrl', 'ctrl_r': 'Ctrl',
                'shift_l': 'Shift', 'shift_r': 'Shift',
                'cmd': 'Cmd', 'cmd_r': 'Cmd', 
                'enter': 'Enter', 'space': 'Space', 'tab': 'Tab',
                'esc': 'Esc', 'delete': 'Del', 'backspace': 'Backspace',
                'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right',
                'page_up': 'PgUp', 'page_down': 'PgDn',
                'home': 'Home', 'end': 'End', 'insert': 'Ins',
                'caps_lock': 'CapsLock', 'num_lock': 'NumLock',
                'print_screen': 'PrtSc', 'scroll_lock': 'ScrollLock', 'pause': 'Pause',
                **{f'f{i}': f'F{i}' for i in range(1, 25)}
            }
            return name_map.get(name, name.capitalize())
        elif hasattr(key_obj, 'char') and key_obj.char is not None: # Phim ky tu
            return str(key_obj.char).upper()
        else: # Ko xac dinh
            return "Unknown"
    except Exception: # Neu co loi
        return "ErrorKey"

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
        error_emitted = False # Flag theo doi loi
        try:
            if not self.text_to_type: 
                self.error_signal.emit(Translations.get("worker_empty_text_error"))
                error_emitted = True; return
            if self.interval_s <= 0: 
                self.error_signal.emit(Translations.get("worker_invalid_interval_error"))
                error_emitted = True; return
            if self.repetitions < 0: 
                self.error_signal.emit(Translations.get("worker_invalid_repetitions_error"))
                error_emitted = True; return
            
            count = 0; initial_delay = 0.75; start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request: 
                    return # Finally se emit typing_finished_signal
                time.sleep(0.05)
            
            while self._is_running_request:
                if self.repetitions != 0 and count >= self.repetitions: break
                special_keys_map = {"<enter>":PynputKey.enter,"<tab>":PynputKey.tab,"<esc>":PynputKey.esc,"<space>":PynputKey.space,"<up>":PynputKey.up,"<down>":PynputKey.down,"<left>":PynputKey.left,"<right>":PynputKey.right,**{f"<f{i}>":getattr(PynputKey,f"f{i}")for i in range(1,13)},}
                if self.text_to_type.lower() in special_keys_map:
                    key_to_press=special_keys_map[self.text_to_type.lower()]; self.keyboard_controller.press(key_to_press); self.keyboard_controller.release(key_to_press)
                else: self.keyboard_controller.type(self.text_to_type)
                count+=1; rep_text=f"{self.repetitions}"if self.repetitions!=0 else Translations.get("rep_text_infinite")
                self.update_status_signal.emit(Translations.get("worker_status_running",
                    count=count, rep_text=rep_text, hotkey_display_name=self.hotkey_display_name
                ))
                sleep_start_time=time.perf_counter()
                while time.perf_counter()-sleep_start_time < self.interval_s:
                    if not self._is_running_request:break
                    time.sleep(0.05) 
                if not self._is_running_request:break
        except Exception as e: 
            self.error_signal.emit(Translations.get("worker_runtime_error", error_message=str(e)))
            error_emitted = True 
        finally: 
            if not error_emitted: 
                self.typing_finished_signal.emit()
    @Slot()
    def request_stop(self): self._is_running_request=False

# --- Worker lắng nghe Hotkey ---
class HotkeyListenerWorker(QObject):
    hotkey_pressed_signal=Signal()
    def __init__(self,hotkey_to_listen):
        super().__init__()
        self.hotkey_to_listen=hotkey_to_listen
        self._pynput_listener=None
        self._keep_listening=True
    @Slot()
    def run(self):
        def on_press(key):
            if not self._keep_listening:return False
            try:
                if key==self.hotkey_to_listen:
                    self.hotkey_pressed_signal.emit()
            except AttributeError:pass 
            except Exception: pass
            return self._keep_listening
        
        try:
            self._pynput_listener=PynputListener(on_press=on_press, suppress=False) 
            self._pynput_listener.start()
            self._pynput_listener.join() 
        except Exception:
            pass

    @Slot()
    def request_stop(self):
        self._keep_listening=False
        if self._pynput_listener and self._pynput_listener.is_alive():
            try:
                self._pynput_listener.stop()
            except Exception:
                try:
                    PynputListener.stop(self._pynput_listener)
                except Exception:
                    pass
        self._pynput_listener = None 

# --- Worker lắng nghe một phím duy nhất (cho cài đặt hotkey) - DA DUOC UPDATE ---
class SingleKeyListenerWorker(QObject):
    key_captured_signal = Signal(int, object, str) # hotkey_type, Pynput key object, key name string
    error_signal = Signal(int, str) # hotkey_type, error_message
    # Bao hieu listener da ket thuc (bat duoc phim, loi hoac huy) cho hotkey_type tuong ung
    listener_operation_finished_signal = Signal(int) 

    def __init__(self):
        super().__init__()
        self._pynput_listener_instance = None 
        self._current_hotkey_type_being_set = 0 # Loai hotkey dang duoc set
        self._is_actively_listening_for_key = False # Flag dieu khien pynput listener con
        self._keep_worker_thread_running = True # Flag dieu khien vong lap chinh cua worker (run())

    @Slot(int)
    def activate_listener_for_hotkey_type(self, hotkey_type_to_set):
        # Kich hoat worker de bat dau lang nghe cho mot loai hotkey cu the
        if self._is_actively_listening_for_key: 
            return 
        self._current_hotkey_type_being_set = hotkey_type_to_set
        self._is_actively_listening_for_key = True
        
    @Slot()
    def cancel_current_listening_operation(self):
        if self._is_actively_listening_for_key: 
            self._is_actively_listening_for_key = False 
            if self._pynput_listener_instance and self._pynput_listener_instance.is_alive():
                try:
                    self._pynput_listener_instance.stop() 
                except Exception: 
                    pass
    
    def _on_press_capture_key(self, key_pressed):
        if not self._is_actively_listening_for_key: 
            return False 

        try:
            key_name_str = get_pynput_key_display_name(key_pressed)
            if key_name_str == "Unknown" or key_name_str == "ErrorKey":
                self.error_signal.emit(self._current_hotkey_type_being_set, Translations.get("msgbox_error_set_hotkey_text", error_message=f"Phím không nhận diện: {key_pressed}"))
            else:
                self.key_captured_signal.emit(self._current_hotkey_type_being_set, key_pressed, key_name_str)
        except Exception as e:
            self.error_signal.emit(self._current_hotkey_type_being_set, Translations.get("msgbox_error_set_hotkey_text", error_message=str(e)))
        finally:
            self._is_actively_listening_for_key = False 
            return False 

    @Slot()
    def run(self):
        while self._keep_worker_thread_running:
            if self._is_actively_listening_for_key:
                active_hotkey_type_at_start = self._current_hotkey_type_being_set 
                try:
                    self._pynput_listener_instance = PynputListener(on_press=self._on_press_capture_key, suppress=False)
                    self._pynput_listener_instance.start()
                    self._pynput_listener_instance.join() 
                except Exception as e:
                    if self._is_actively_listening_for_key : 
                        self.error_signal.emit(active_hotkey_type_at_start, Translations.get("msgbox_error_set_hotkey_text", error_message=f"Lỗi bộ lắng nghe: {str(e)}"))
                        self._is_actively_listening_for_key = False 
                finally:
                    self._is_actively_listening_for_key = False 
                    self._pynput_listener_instance = None 
                    self.listener_operation_finished_signal.emit(active_hotkey_type_at_start) 
            else:
                QThread.msleep(50) 

    @Slot()
    def request_stop_worker_thread(self): 
        self._keep_worker_thread_running = False 
        self._is_actively_listening_for_key = False 
        if self._pynput_listener_instance and self._pynput_listener_instance.is_alive():
            try:
                self._pynput_listener_instance.stop()
            except Exception: 
                pass
        self._pynput_listener_instance = None


# --- Worker ghi thao tác bàn phím ---
class KeyboardRecorderWorker(QObject):
    key_event_recorded = Signal(object, str, str, float) # key_obj, key_name, action ("press"/"release"), delay_ms
    recording_status_update = Signal(str)
    recording_finished = Signal()
    
    def __init__(self, start_record_hotkey, stop_record_hotkey_name):
        super().__init__()
        self.start_record_hotkey = start_record_hotkey 
        self.stop_record_hotkey_name = stop_record_hotkey_name 
        self._listener = None
        self._is_recording = False 
        self._stop_requested = False
        self._last_event_time = None
        self.countdown_duration = 3 

    def _start_actual_recording(self):
        self._is_recording = True
        self._last_event_time = time.perf_counter() 
        self.recording_status_update.emit(Translations.get("status_recorder_recording", hotkey_name=self.stop_record_hotkey_name))
        
        def on_press(key):
            if not self._is_recording or self._stop_requested: return False
            current_time = time.perf_counter()
            delay_ms = (current_time - self._last_event_time) * 1000 if self._last_event_time else 0
            self._last_event_time = current_time
            key_name = get_pynput_key_display_name(key)
            self.key_event_recorded.emit(key, key_name, Translations.get("action_press"), delay_ms)
            return not self._stop_requested

        def on_release(key):
            if not self._is_recording or self._stop_requested: return False
            current_time = time.perf_counter()
            delay_ms = (current_time - self._last_event_time) * 1000
            self._last_event_time = current_time
            key_name = get_pynput_key_display_name(key)
            self.key_event_recorded.emit(key, key_name, Translations.get("action_release"), delay_ms)
            if self._stop_requested : return False 
            return not self._stop_requested

        try:
            self._listener = PynputListener(on_press=on_press, on_release=on_release, suppress=False) 
            self._listener.start()
            self._listener.join()
        except Exception:
            pass
        finally:
            self._is_recording = False 
            self.recording_finished.emit() # Dam bao emit ngay ca khi co loi listener

    @Slot()
    def run(self):
        for i in range(self.countdown_duration, 0, -1):
            if self._stop_requested:
                self.recording_finished.emit() 
                return
            self.recording_status_update.emit(Translations.get("status_recorder_countdown", seconds=i))
            time.sleep(1)
        
        if self._stop_requested: 
            self.recording_finished.emit()
            return
        self._start_actual_recording()

    @Slot()
    def request_stop(self):
        self._stop_requested = True
        if self._listener and self._listener.is_alive():
            try:
                self._listener.stop() 
            except Exception:
                pass


# --- Worker phát lại thao tác bàn phím ---
class RecordedPlayerWorker(QObject):
    update_status_signal = Signal(str)
    playing_finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, recorded_events, play_stop_hotkey_name):
        super().__init__()
        self.recorded_events = recorded_events 
        self.play_stop_hotkey_name = play_stop_hotkey_name
        self.keyboard_controller = PynputController()
        self._is_running_request = True
        self.total_actions = len(recorded_events)

    @Slot()
    def run(self):
        error_emitted = False # Flag theo doi loi
        try:
            if not self.recorded_events:
                self.error_signal.emit(Translations.get("msgbox_no_recording_text"))
                error_emitted = True
                return 

            initial_delay = 0.5 
            start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request: 
                    return # Finally se emit finished
                time.sleep(0.05)

            for i, (key_obj, action_str_en, delay_ms) in enumerate(self.recorded_events): 
                if not self._is_running_request: break
                
                if delay_ms > 0:
                    sleep_start_time = time.perf_counter()
                    while time.perf_counter() - sleep_start_time < (delay_ms / 1000.0):
                        if not self._is_running_request: break
                        time.sleep(0.01) 
                if not self._is_running_request: break

                if action_str_en == Translations.get("action_press", lang=Translations.LANG_EN): 
                    self.keyboard_controller.press(key_obj)
                elif action_str_en == Translations.get("action_release", lang=Translations.LANG_EN):
                    self.keyboard_controller.release(key_obj)
                
                self.update_status_signal.emit(
                    Translations.get("status_player_playing", 
                                     current_action=i + 1, 
                                     total_actions=self.total_actions,
                                     hotkey_name=self.play_stop_hotkey_name)
                )
        except Exception as e:
            self.error_signal.emit(Translations.get("worker_runtime_error", error_message=str(e)))
            error_emitted = True
        finally:
            if not error_emitted: 
                self.playing_finished_signal.emit()

    @Slot()
    def request_stop(self):
        self._is_running_request = False