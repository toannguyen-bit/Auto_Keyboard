# gui/custom_title_bar.py
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from core.translations import Translations 

class CustomTitleBar(QWidget):
    language_changed_signal = Signal(str) # Signal de thong bao thay doi NN

    toggle_advanced_mode_signal = Signal(bool)

    def __init__(self, parent=None, current_lang_code=Translations.LANG_VI):
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0); layout.setSpacing(10)
        
        self.title_label = QLabel(Translations.get("custom_title_bar_default_title"))
        self.title_label.setObjectName("titleBarLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.title_label)
        
        # Nut chuyen che do
        self.btn_toggle_mode = QPushButton() # Text se dc set trong retranslate
        self.btn_toggle_mode.setObjectName("toggleModeButton")
        self.btn_toggle_mode.setCheckable(True) # De biet trang thai
        self.btn_toggle_mode.clicked.connect(self._on_toggle_mode_clicked)
        layout.addWidget(self.btn_toggle_mode)
        
        layout.addStretch()

        # ComboBox chon ngon ngu
        self.lang_combo = QComboBox(self)
        self.lang_combo.setObjectName("languageComboBox")
        self.lang_combo.setMinimumWidth(100)
        for code, name in Translations.lang_map.items():
            self.lang_combo.addItem(name, code) # Luu code NN vao UserData
        
        current_index = self.lang_combo.findData(current_lang_code)
        if current_index != -1:
            self.lang_combo.setCurrentIndex(current_index)
        
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)
        layout.addWidget(self.lang_combo)

        self.btn_minimize = QPushButton("–"); self.btn_minimize.setObjectName("minimizeButton"); self.btn_minimize.setFixedSize(30, 30); self.btn_minimize.clicked.connect(self.window().showMinimized)
        layout.addWidget(self.btn_minimize)
        self.btn_maximize_restore = QPushButton("□"); self.btn_maximize_restore.setObjectName("maximizeRestoreButton"); self.btn_maximize_restore.setFixedSize(30, 30); self.btn_maximize_restore.clicked.connect(self._toggle_maximize_restore)
        layout.addWidget(self.btn_maximize_restore)
        self.btn_close = QPushButton("✕"); self.btn_close.setObjectName("closeButton"); self.btn_close.setFixedSize(30, 30); self.btn_close.clicked.connect(self.window().close)
        layout.addWidget(self.btn_close)
        
        self._is_advanced_mode = False # Ban dau la che do AutoTyper
        self.retranslate_ui_texts() # Goi de set text ban dau cho nut toggle

    def _on_lang_combo_changed(self, index): # Khi chon NN moi
        lang_code = self.lang_combo.itemData(index)
        self.language_changed_signal.emit(lang_code)

    def _on_toggle_mode_clicked(self, checked):
        self._is_advanced_mode = checked
        self.toggle_advanced_mode_signal.emit(checked)
        self.retranslate_ui_texts() # Cap nhat lai text nut

    def set_mode_button_state(self, is_advanced): # Goi tu main_window khi chuyen mode bang cach khac (neu co)
        self._is_advanced_mode = is_advanced
        self.btn_toggle_mode.setChecked(is_advanced)
        self.retranslate_ui_texts()

    def _toggle_maximize_restore(self):
        if self.window().isMaximized(): self.window().showNormal(); self.btn_maximize_restore.setText("□")
        else: self.window().showMaximized(); self.btn_maximize_restore.setText("▫")
    
    def setTitle(self, title): self.title_label.setText(title)
    
    def retranslate_ui_texts(self): # Cap nhat text cho combobox va nut toggle
        # Nut chuyen che do
        if self._is_advanced_mode:
            self.btn_toggle_mode.setText(Translations.get("button_autotyper_mode"))
        else:
            self.btn_toggle_mode.setText(Translations.get("button_advanced_mode"))

        current_data = self.lang_combo.currentData() 
        self.lang_combo.blockSignals(True) 
        self.lang_combo.clear()
        for code, name in Translations.lang_map.items():
            self.lang_combo.addItem(name, code) 
        
        current_index = self.lang_combo.findData(current_data) 
        if current_index != -1:
            self.lang_combo.setCurrentIndex(current_index)
        self.lang_combo.blockSignals(False) 