# core/translations.py

class Translations:
    LANG_VI = "vi"
    LANG_EN = "en"
    LANG_JA = "ja"

    lang_map = { # Map code voi ten hien thi
        LANG_VI: "Tiếng Việt",
        LANG_EN: "English",
        LANG_JA: "日本語"
    }

    translations = {
        "window_title": {
            LANG_VI: "AutoTyper Poetic",
            LANG_EN: "AutoTyper Poetic",
            LANG_JA: "AutoTyper Poetic"
        },
        "title_bar_text": { # hotkey
            LANG_VI: "AutoTyper Poetic - Hotkey: {hotkey}",
            LANG_EN: "AutoTyper Poetic - Hotkey: {hotkey}",
            LANG_JA: "AutoTyper Poetic - ホットキー: {hotkey}"
        },
        "error_loading_background_msg_console": { # path
            LANG_VI: "Loi: Khong the tai anh nen tu '{path}'",
            LANG_EN: "Error: Could not load background image from '{path}'",
            LANG_JA: "エラー: 背景画像を '{path}' から読み込めませんでした"
        },
        "error_loading_background_ui": {
            LANG_VI: "Lỗi tải ảnh nền! Kiểm tra console.",
            LANG_EN: "Background image load error! Check console.",
            LANG_JA: "背景画像の読み込みエラー！コンソールを確認してください。"
        },
        "worker_empty_text_error": {
            LANG_VI: "Vui lòng nhập văn bản/phím cần nhấn.",
            LANG_EN: "Please enter text/keys to press.",
            LANG_JA: "入力するテキスト/キーを入力してください。"
        },
        "worker_invalid_interval_error": {
            LANG_VI: "Khoảng thời gian phải lớn hơn 0.",
            LANG_EN: "Interval must be greater than 0.",
            LANG_JA: "間隔は0より大きくする必要があります。"
        },
        "worker_invalid_repetitions_error": {
            LANG_VI: "Số lần lặp lại phải là số không âm.",
            LANG_EN: "Repetitions must be a non-negative number.",
            LANG_JA: "繰り返し回数は負でない数である必要があります。"
        },
        "worker_status_running": { # count, rep_text, hotkey_display_name
            LANG_VI: "Đang chạy... (Lần {count}/{rep_text}). Nhấn {hotkey_display_name} để dừng.",
            LANG_EN: "Running... (Count {count}/{rep_text}). Press {hotkey_display_name} to stop.",
            LANG_JA: "実行中... (回数 {count}/{rep_text})。{hotkey_display_name} を押して停止。"
        },
        "worker_runtime_error": { # error_message
            LANG_VI: "Lỗi trong quá trình chạy: {error_message}",
            LANG_EN: "Error during execution: {error_message}",
            LANG_JA: "実行中のエラー: {error_message}"
        },
        "text_input_placeholder": {
            LANG_VI: "Nhập văn bản hoặc <key_name>...",
            LANG_EN: "Enter text or <key_name>...",
            LANG_JA: "テキストまたは <key_name> を入力..."
        },
        "label_text_key": {
            LANG_VI: "Văn bản/Phím:",
            LANG_EN: "Text/Key:",
            LANG_JA: "テキスト/キー:"
        },
        "label_interval": {
            LANG_VI: "Khoảng thời gian:",
            LANG_EN: "Interval:",
            LANG_JA: "間隔:"
        },
        "interval_suffix": {
            LANG_VI: " ms",
            LANG_EN: " ms",
            LANG_JA: "ミリ秒"
        },
        "label_repetitions": {
            LANG_VI: "Số lần lặp:",
            LANG_EN: "Repetitions:",
            LANG_JA: "繰り返し回数:"
        },
        "repetitions_infinite": {
            LANG_VI: "Vô hạn (0)",
            LANG_EN: "Infinite (0)",
            LANG_JA: "無限 (0)"
        },
        "button_start": { # hotkey_name
            LANG_VI: "Start ({hotkey_name})",
            LANG_EN: "Start ({hotkey_name})",
            LANG_JA: "開始 ({hotkey_name})"
        },
        "button_stop": {
            LANG_VI: "Stop",
            LANG_EN: "Stop",
            LANG_JA: "停止"
        },
        "status_ready": { # hotkey_name
            LANG_VI: "Sẵn sàng. Nhấn '{hotkey_name}' để bắt đầu.",
            LANG_EN: "Ready. Press '{hotkey_name}' to start.",
            LANG_JA: "準備完了。'{hotkey_name}' を押して開始。"
        },
        "msgbox_missing_info_title": {
            LANG_VI: "Thiếu thông tin",
            LANG_EN: "Missing Information",
            LANG_JA: "情報不足"
        },
        "button_start_loading": {
            LANG_VI: "...",
            LANG_EN: "...",
            LANG_JA: "..."
        },
        "status_preparing": { # hotkey_name
            LANG_VI: "Chuẩn bị... (Nhấn '{hotkey_name}' để dừng)",
            LANG_EN: "Preparing... (Press '{hotkey_name}' to stop)",
            LANG_JA: "準備中... ('{hotkey_name}' を押して停止)"
        },
        "status_requesting_stop": {
            LANG_VI: "Đang yêu cầu dừng...",
            LANG_EN: "Requesting stop...",
            LANG_JA: "停止を要求中..."
        },
        "msgbox_autotyper_error_title": {
            LANG_VI: "Lỗi AutoTyper",
            LANG_EN: "AutoTyper Error",
            LANG_JA: "AutoTyper エラー"
        },
        "status_stopped": { # hotkey_name
            LANG_VI: "Đã dừng. Nhấn '{hotkey_name}' để bắt đầu.",
            LANG_EN: "Stopped. Press '{hotkey_name}' to start.",
            LANG_JA: "停止しました。'{hotkey_name}' を押して開始。"
        },
        "status_stopped_fully": { # hotkey_name
            LANG_VI: "Đã dừng (hoàn toàn). Nhấn '{hotkey_name}' để bắt đầu.",
            LANG_EN: "Stopped (fully). Press '{hotkey_name}' to start.",
            LANG_JA: "停止しました (完全に)。'{hotkey_name}' を押して開始。"
        },
        "custom_title_bar_default_title": {
            LANG_VI: "AutoTyper Poetic",
            LANG_EN: "AutoTyper Poetic",
            LANG_JA: "AutoTyper Poetic"
        },
         "rep_text_infinite": {
            LANG_VI: "∞",
            LANG_EN: "∞",
            LANG_JA: "∞"
        },
        "label_hotkey_setting_group": {
            LANG_VI: "Cài đặt Hotkey",
            LANG_EN: "Hotkey Settings",
            LANG_JA: "ホットキー設定"
        },
        "label_current_hotkey": {
            LANG_VI: "Hotkey hiện tại:",
            LANG_EN: "Current Hotkey:",
            LANG_JA: "現在のホットキー:"
        },
        "button_set_hotkey": {
            LANG_VI: "Thay đổi Hotkey",
            LANG_EN: "Change Hotkey",
            LANG_JA: "ホットキー変更"
        },
        "button_setting_hotkey_wait": {
            LANG_VI: "Nhấn phím mới...",
            LANG_EN: "Press new key...",
            LANG_JA: "新しいキーを押してください..."
        },
        "msgbox_hotkey_set_title": {
            LANG_VI: "Hotkey đã được đặt",
            LANG_EN: "Hotkey Set",
            LANG_JA: "ホットキー設定完了"
        },
        "msgbox_hotkey_set_text": { # new_hotkey_name
            LANG_VI: "Hotkey mới: {new_hotkey_name}",
            LANG_EN: "New hotkey: {new_hotkey_name}",
            LANG_JA: "新しいホットキー: {new_hotkey_name}"
        },
        "msgbox_error_set_hotkey_title": {
            LANG_VI: "Lỗi đặt Hotkey",
            LANG_EN: "Hotkey Set Error",
            LANG_JA: "ホットキー設定エラー"
        },
        "msgbox_error_set_hotkey_text": { # error_message
            LANG_VI: "Không thể đặt hotkey: {error_message}",
            LANG_EN: "Could not set hotkey: {error_message}",
            LANG_JA: "ホットキーを設定できませんでした: {error_message}"
        }
    }
    current_lang = LANG_VI 

    @classmethod
    def set_language(cls, lang_code): # Dat ngon ngu
        if lang_code in [cls.LANG_VI, cls.LANG_EN, cls.LANG_JA]:
            cls.current_lang = lang_code
        else: # Mac dinh tieng Viet neu ko ho tro
            print(f"Unsupported language: {lang_code}. Defaulting to {cls.LANG_VI}")
            cls.current_lang = cls.LANG_VI

    @classmethod
    def get(cls, key, **kwargs): # Lay chuoi dich
        try:
            translation_dict = cls.translations[key]
            # Uu tien ngon ngu hien tai, sau do la tieng Anh, cuoi cung la khoa
            raw_translation = translation_dict.get(cls.current_lang, translation_dict.get(cls.LANG_EN, key))
            return raw_translation.format(**kwargs) if kwargs else raw_translation
        except KeyError:
            # Tra ve key neu ko tim thay, giup de debug
            # print(f"Warning: Translation key '{key}' not found for lang '{cls.current_lang}'.")
            return key