# core/workers.py
import time
from PySide6.QtCore import QObject, Signal, Slot, QThread
from pynput.keyboard import Controller as PynputController, Listener as PynputListener, Key as PynputKey
from .translations import Translations # Import tuong doi

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
        # print(f"HotkeyListenerWorker: Starting to listen for {self.hotkey_to_listen}")
        def on_press(key):
            if not self._keep_listening:return False
            try:
                # print(f"Hotkey pressed: {key}, Target: {self.hotkey_to_listen}")
                if key==self.hotkey_to_listen:
                    # print(f"MATCH! Emitting hotkey_pressed_signal for {self.hotkey_to_listen}")
                    self.hotkey_pressed_signal.emit()
            except AttributeError:pass # Tranh loi khi so sanh
            except Exception as e: 
                # print(f"Error in on_press: {e}")
                pass
            return self._keep_listening
        
        try:
            self._pynput_listener=PynputListener(on_press=on_press, suppress=False) # suppress=False de debug
            self._pynput_listener.start()
            self._pynput_listener.join() # Block thread nay cho den khi listener stop
        except Exception as e:
            # print(f"Error starting/joining PynputListener: {e}")
            pass # Co the emit error signal
        # print("HotkeyListenerWorker: Listener stopped/finished.")

    @Slot()
    def request_stop(self):
        # print("HotkeyListenerWorker: Requesting stop...")
        self._keep_listening=False
        if self._pynput_listener and self._pynput_listener.is_alive():
            # print("HotkeyListenerWorker: Calling PynputListener.stop()")
            # Day la cach dung cho pynput < 1.7.0. Tu 1.7.0, listener.stop() la instance method
            try:
                self._pynput_listener.stop()
            except Exception as e:
                # print(f"Error calling self._pynput_listener.stop(): {e}")
                # Thu cach cu hon neu version pynput khac
                try:
                    PynputListener.stop(self._pynput_listener)
                except Exception as e_fallback:
                    # print(f"Error calling PynputListener.stop (fallback): {e_fallback}")
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
        # print("SingleKeyListenerWorker: run - waiting for key press")
        def on_press_once(key):
            if self._stop_requested: return False # Neu da yeu cau dung
            try:
                # print(f"SingleKeyListenerWorker: Key pressed: {key}")
                key_name = get_pynput_key_display_name(key)
                if key_name == "Unknown" or key_name == "ErrorKey":
                    self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=f"Phím không nhận diện được: {key}"))
                    return False 
                
                self.key_captured_signal.emit(key, key_name)
            except Exception as e:
                # print(f"SingleKeyListenerWorker: Error in on_press_once: {e}")
                self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=str(e)))
            finally:
                return False # Luon dung listener sau khi bat duoc 1 phim (hoac loi)

        try:
            self._listener = PynputListener(on_press=on_press_once)
            self._listener.start()
            self._listener.join() # Cho listener ket thuc
        except Exception as e:
            # print(f"SingleKeyListenerWorker: Error starting listener: {e}")
            self.error_signal.emit(Translations.get("msgbox_error_set_hotkey_text", error_message=f"Không thể khởi tạo bộ lắng nghe: {str(e)}"))
        # print("SingleKeyListenerWorker: Listener finished.")

    @Slot()
    def request_stop(self): # Dung worker neu can
        # print("SingleKeyListenerWorker: Requesting stop.")
        self._stop_requested = True
        if self._listener and self._listener.is_alive():
            try:
                self._listener.stop()
            except Exception:
                pass 
        self._listener = None