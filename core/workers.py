# core/workers.py
import time
from PySide6.QtCore import QObject, Signal, Slot, QThread # Bo QTimer khoi import nay
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
        try:
            if not self.text_to_type: self.error_signal.emit(Translations.get("worker_empty_text_error")); return
            if self.interval_s <= 0: self.error_signal.emit(Translations.get("worker_invalid_interval_error")); return
            if self.repetitions < 0: self.error_signal.emit(Translations.get("worker_invalid_repetitions_error")); return
            count = 0; initial_delay = 0.75; start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request: self.typing_finished_signal.emit(); return # Ket thuc som
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
                    time.sleep(0.05) # Check ngat thuong xuyen hon
                if not self._is_running_request:break
        except Exception as e: self.error_signal.emit(Translations.get("worker_runtime_error", error_message=str(e)))
        finally: self.typing_finished_signal.emit() # Dam bao emit
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

# --- Worker lắng nghe một phím duy nhất (cho cài đặt hotkey) ---
class SingleKeyListenerWorker(QObject):
    key_captured_signal = Signal(object, str) # Pynput key object, key name string
    error_signal = Signal(str) # Bao loi neu co
    
    def __init__(self):
        super().__init__()
        self._listener = None
        self._stop_requested = False

    @Slot()
    def run(self):
        def on_press_once(key):
            if self._stop_requested: return False 
            try:
                key_name = get_pynput_key_display_name(key)
                if key_name == "Unknown" or key_name == "ErrorKey":
                    self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=f"Phím không nhận diện được: {key}"))
                    return False 
                
                self.key_captured_signal.emit(key, key_name)
            except Exception as e:
                self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=str(e)))
            finally:
                return False 

        try:
            self._listener = PynputListener(on_press=on_press_once)
            self._listener.start()
            self._listener.join() 
        except Exception as e:
            self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=f"Không thể khởi tạo bộ lắng nghe: {str(e)}"))

    @Slot()
    def request_stop(self): 
        self._stop_requested = True
        if self._listener and self._listener.is_alive():
            try:
                self._listener.stop()
            except Exception:
                pass 
        self._listener = None

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
        self._is_recording = False # Se duoc set True trong _start_actual_recording
        self._stop_requested = False
        self._last_event_time = None
        self.countdown_duration = 3 # So giay dem nguoc

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
            # Chi ghi neu khong phai la hotkey bat dau ghi (neu can, nhung thuong da qua roi)
            # Va khong phai la hotkey dung ghi (se dc xu ly boi request_stop)
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
            # print("KeyboardRecorderWorker: PynputListener started for actual recording.")
            self._listener.join()
            # print("KeyboardRecorderWorker: PynputListener joined (finished).")
        except Exception as e:
            # print(f"Recorder listener error: {e}")
            pass
        finally:
            # print("KeyboardRecorderWorker: _start_actual_recording finally block. Emitting recording_finished.")
            self._is_recording = False 
            self.recording_finished.emit()

    @Slot()
    def run(self):
        # Thuc hien dem nguoc
        # print(f"KeyboardRecorderWorker: run - starting countdown ({self.countdown_duration}s). Stop requested: {self._stop_requested}")
        for i in range(self.countdown_duration, 0, -1):
            if self._stop_requested:
                # print("KeyboardRecorderWorker: Countdown interrupted by request_stop.")
                self.recording_finished.emit() # Emit finished neu bi huy trong luc dem nguoc
                return
            self.recording_status_update.emit(Translations.get("status_recorder_countdown", seconds=i))
            time.sleep(1)
        
        if self._stop_requested: # Kiem tra lai sau khi sleep cuoi cung
            # print("KeyboardRecorderWorker: Countdown finished but stop was requested. Emitting finished.")
            self.recording_finished.emit()
            return

        # print("KeyboardRecorderWorker: Countdown finished. Starting actual recording.")
        self._start_actual_recording()
        # print("KeyboardRecorderWorker: run - finished _start_actual_recording.")


    @Slot()
    def request_stop(self):
        # print("KeyboardRecorderWorker: request_stop called.")
        self._stop_requested = True
        
        if self._listener and self._listener.is_alive():
            # print("KeyboardRecorderWorker: Calling PynputListener.stop()")
            try:
                self._listener.stop() # Day la cach dung cho pynput
            except Exception as e:
                # print(f"Error stopping listener in request_stop: {e}")
                pass
        # else:
            # print("KeyboardRecorderWorker: Listener not active or None in request_stop.")


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
        try:
            if not self.recorded_events:
                self.error_signal.emit(Translations.get("msgbox_no_recording_text"))
                return

            initial_delay = 0.5 
            start_time = time.perf_counter()
            while time.perf_counter() - start_time < initial_delay:
                if not self._is_running_request: self.playing_finished_signal.emit(); return
                time.sleep(0.05)

            for i, (key_obj, action_str_en, delay_ms) in enumerate(self.recorded_events): # Mong doi action_str_en
                if not self._is_running_request: break
                
                if delay_ms > 0:
                    sleep_start_time = time.perf_counter()
                    while time.perf_counter() - sleep_start_time < (delay_ms / 1000.0):
                        if not self._is_running_request: break
                        time.sleep(0.01) 
                if not self._is_running_request: break

                # Su dung truc tiep action_str_en da duoc chuan hoa
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

            if self._is_running_request: 
                pass 

        except Exception as e:
            self.error_signal.emit(Translations.get("worker_runtime_error", error_message=str(e)))
        finally:
            self.playing_finished_signal.emit()

    @Slot()
    def request_stop(self):
        self._is_running_request = False