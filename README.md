# AutoTyper Poetic - Advanced Keyboard Automation ᓚᘏᗢ



<!-- Vietnamese -->
<details>
<summary>🇻🇳 Tiếng Việt</summary>

## Giới thiệu

**AutoTyper Poetic** là một ứng dụng máy tính để bàn được thiết kế để tự động hóa các tác vụ nhập liệu bàn phím. Ứng dụng cung cấp hai chế độ chính: chế độ **AutoTyper** cơ bản để gõ văn bản hoặc phím lặp đi lặp lại, và chế độ **Ghi & Phát** nâng cao để ghi lại và phát lại các chuỗi hành động bàn phím phức tạp. Với giao diện trực quan, hỗ trợ đa ngôn ngữ, khả năng tùy chỉnh hotkey và quản lý cấu hình linh hoạt, AutoTyper Poetic là công cụ hữu ích cho việc tự động hóa các công việc lặp đi lặp lại hoặc thực hiện các macro bàn phím.

Ứng dụng được xây dựng bằng Python và PySide6 cho giao diện người dùng, cùng với `pynput` để xử lý tương tác bàn phím.

**LƯU Ý QUAN TRỌNG:**

*   📜 **Tập tin cấu hình:** Cài đặt của người dùng (ngôn ngữ, kích thước cửa sổ, hotkey, macro đã ghi, v.v.) được lưu trong `autokeyboard_config.json` tại thư mục gốc của ứng dụng.
*   🚀 **Script chạy nhanh:** Các tệp `run.bat` (Windows) và `run.sh` (Linux/macOS) được cung cấp để tự động hóa việc tạo môi trường ảo (nếu chưa có) và cài đặt các thư viện cần thiết.

## Tính năng

*   **Hoạt động Hai Chế độ:**
    *   **Chế độ AutoTyper:**
        *   Tự động gõ văn bản do người dùng xác định hoặc các tổ hợp phím đặc biệt (ví dụ: `<enter>`, `<f1>`).
        *   Khoảng thời gian giữa các lần gõ có thể điều chỉnh (tính bằng mili giây).
        *   Số lần lặp lại có thể cấu hình (0 cho vô hạn).
        *   Hotkey chuyên dụng (mặc định F9, có thể thay đổi) để bắt đầu/dừng việc gõ tự động.
    *   **Chế độ Ghi & Phát (Giao diện Nâng cao):**
        *   Ghi lại các chuỗi hành động bàn phím (nhấn phím, thả phím và thời gian chính xác giữa chúng).
        *   Lớp phủ đếm ngược trực quan trước khi bắt đầu ghi.
        *   Các hotkey chuyên dụng (mặc định F10 để ghi, F11 để phát, có thể thay đổi) để bắt đầu/dừng ghi và phát lại.
        *   Các hành động đã ghi được hiển thị trong bảng (Phím, Hành động, Độ trễ).
        *   Phát lại các chuỗi đã ghi với số lần lặp có thể điều chỉnh (0 cho vô hạn).
        *   Tùy chọn xóa các hành động đã ghi.
*   **Giao diện Thân thiện với Người dùng:**
    *   Giao diện đồ họa trực quan được xây dựng bằng PySide6.
    *   Thanh tiêu đề tùy chỉnh với các nút điều khiển cửa sổ tiêu chuẩn (thu nhỏ, phóng to, đóng) và phong cách tùy chỉnh.
    *   Hỗ trợ kéo và thay đổi kích thước cửa sổ.
    *   Hiệu ứng chuyển động mượt mà khi mở/đóng cửa sổ và chuyển đổi giữa các trang.
*   **Hỗ trợ Đa ngôn ngữ:**
    *   Giao diện có sẵn bằng Tiếng Anh (English), Tiếng Việt (Vietnamese), và Tiếng Nhật (日本語).
    *   Dễ dàng chuyển đổi ngôn ngữ thông qua menu thả xuống trên thanh tiêu đề.
*   **Quản lý Cấu hình:**
    *   Cài đặt được lưu trữ bền vững trong `autokeyboard_config.json`.
    *   Lưu tùy chọn ngôn ngữ, kích thước/vị trí cửa sổ, chế độ hoạt động, tất cả hotkey, cài đặt AutoTyper, và các macro đã ghi.
    *   Các chức năng "Tải Cấu hình", "Lưu dạng..." và "Lưu Hiện tại".
*   **Quản lý Hotkey:**
    *   Giao diện dễ sử dụng để thay đổi hotkey cho AutoTyper, Bắt đầu/Dừng Ghi, và Bắt đầu/Dừng Phát lại.
    *   Phát hiện xung đột hotkey để tránh gán cùng một hotkey cho nhiều hành động.
*   **Tương thích Đa nền tảng:**
    *   Bao gồm `run.bat` cho Windows và `run.sh` cho Linux/macOS để đơn giản hóa việc thiết lập và thực thi.
    *   Các script này sẽ xử lý việc tạo môi trường ảo và cài đặt các thư viện phụ thuộc.
*   **Trạng thái & Phản hồi:**
    *   Cập nhật trạng thái theo thời gian thực trong ứng dụng.
    *   Lớp phủ đếm ngược trực quan khi ghi.
    *   Các hộp thoại thông báo lỗi và xác nhận.

## Điều kiện tiên quyết (Để chạy từ mã nguồn)

1.  **Python:** Nên sử dụng Python 3.x. Các script `run.bat`/`run.sh` sẽ cố gắng sử dụng `python` (Windows) hoặc `python3`/`python` (Linux/macOS) có sẵn trong PATH.
2.  **Pip:** Trình quản lý gói Python (thường đi kèm với Python).

## Cài đặt & Chạy ứng dụng (Từ mã nguồn)

Cách dễ nhất để chạy ứng dụng là sử dụng các script được cung cấp:

1.  **Tải mã nguồn:**
    *   Sao chép (clone) repository này hoặc tải về dưới dạng ZIP và giải nén.

2.  **Chạy script cài đặt và khởi động:**
    *   **Trên Windows:**
        *   Điều hướng đến thư mục `windows` trong dự án.
        *   Chạy file `run.bat`.
    *   **Trên Linux/macOS:**
        *   Mở terminal, điều hướng đến thư mục `linux-mac` trong dự án.
        *   Cấp quyền thực thi cho script: `chmod +x run.sh`
        *   Chạy script: `./run.sh`

    Các script này sẽ:
    *   Kiểm tra và tạo một môi trường ảo Python tên là `venv` trong thư mục gốc của dự án (nếu chưa có).
    *   Kích hoạt môi trường ảo.
    *   Cài đặt các thư viện cần thiết từ `requirements.txt`.
    *   Khởi chạy ứng dụng.

**Cài đặt Thủ công (Nếu không muốn dùng script):**

1.  **Tải mã nguồn.**
2.  Mở terminal hoặc command prompt, điều hướng đến thư mục gốc của dự án.
3.  **(Khuyến nghị)** Tạo và kích hoạt một môi trường ảo Python:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```
4.  Cài đặt các thư viện cần thiết:
    ```bash
    pip install -r requirements.txt
    ```
5.  Chạy ứng dụng:
    ```bash
    python main.py
    ```

## Hướng dẫn sử dụng

Sau khi ứng dụng khởi chạy:

*   **Chuyển đổi Chế độ:** Sử dụng nút "Nâng cao" / "AutoTyper" trên thanh tiêu đề để chuyển đổi giữa chế độ AutoTyper và chế độ Ghi & Phát.
*   **Chọn Ngôn ngữ:** Sử dụng menu thả xuống ngôn ngữ trên thanh tiêu đề.
*   **Chế độ AutoTyper:**
    *   **Văn bản/Phím:** Nhập văn bản bạn muốn gõ tự động. Đối với các phím đặc biệt, sử dụng định dạng `<key_name>` (ví dụ: `<enter>`, `<f12>`, `<space>`).
    *   **Khoảng thời gian:** Đặt khoảng thời gian (ms) giữa mỗi lần gõ/nhấn phím.
    *   **Số lần lặp:** Đặt số lần lặp lại (0 cho vô hạn).
    *   **Hotkey:** Mặc định là F9. Nhấn nút "Thay đổi Hotkey" để đặt hotkey mới. Nhấn hotkey này để Bắt đầu/Dừng.
    *   **Nút Start/Stop:** Cũng có thể dùng để bắt đầu/dừng.
*   **Chế độ Ghi & Phát (Nâng cao):**
    *   **Hotkey Ghi/Dừng:** Mặc định F10. Dùng để bắt đầu (sau khi đếm ngược) và dừng ghi. Có thể thay đổi bằng nút "Đổi Hotkey Ghi".
    *   **Hotkey Phát/Dừng:** Mặc định F11. Dùng để bắt đầu/dừng phát lại các hành động đã ghi. Có thể thay đổi bằng nút "Đổi Hotkey Phát".
    *   **Số lần lặp (Phát):** Đặt số lần phát lại chuỗi hành động (0 cho vô hạn).
    *   **Nút Bắt đầu Ghi / Dừng Ghi:** Bắt đầu/dừng quá trình ghi.
    *   **Nút Phát Bản Ghi / Dừng Phát:** Phát/dừng phát lại.
    *   **Nút Xóa Bản Ghi:** Xóa tất cả các hành động đã ghi trong bảng.
    *   **Bảng sự kiện:** Hiển thị các phím đã ghi, hành động (nhấn/thả) và độ trễ.
*   **Quản lý Cấu hình:**
    *   **Tải Cấu hình:** Tải cài đặt từ một tệp `.json`.
    *   **Lưu dạng...:** Lưu cấu hình hiện tại vào một tệp `.json` mới.
    *   **Lưu Hiện tại:** Lưu cấu hình hiện tại vào tệp `autokeyboard_config.json` đang được sử dụng.
    Cấu hình bao gồm ngôn ngữ, trạng thái cửa sổ, cài đặt AutoTyper, cài đặt Ghi/Phát và các hotkey.

## Cấu trúc thư mục (Đơn giản hóa)

```
autokeyboard/
├── assets/               # Tài sản như icon
│   └── icon.ico
├── core/                 # Logic cốt lõi (dịch thuật, workers)
│   ├── translations.py
│   └── workers.py
├── gui/                  # Mã nguồn giao diện người dùng (các trang, cửa sổ, widget tùy chỉnh)
│   ├── autotyper_page.py
│   ├── base_main_window.py
│   ├── constants.py
│   ├── countdown_overlay.py
│   ├── custom_title_bar.py
│   ├── main_window.py
│   └── recorder_page.py
├── linux-mac/            # Script chạy cho Linux/macOS
│   └── run.sh
├── windows/              # Script chạy cho Windows
│   └── run.bat
├── venv/                 # (Thư mục môi trường ảo, được tạo bởi script)
├── .gitignore
├── autokeyboard_config.json # Tệp cấu hình mặc định/được lưu
├── main.py               # Điểm vào chính của ứng dụng
└── requirements.txt      # Danh sách các thư viện Python cần thiết
```

## Công nghệ sử dụng

*   **Python**
*   **PySide6:** Bộ công cụ Qt cho Python (GUI).
*   **pynput:** Thư viện để điều khiển và giám sát thiết bị nhập liệu (bàn phím).

</details>

<!-- English -->
<details>
<summary>🇬🇧 English</summary>

## Introduction

**AutoTyper Poetic** is a desktop application designed to automate keyboard input tasks. It offers two main modes: a basic **AutoTyper** mode for repeatedly typing text or keys, and an advanced **Recorder & Player** mode for recording and replaying complex keyboard action sequences. With an intuitive interface, multilingual support, customizable hotkeys, and flexible configuration management, AutoTyper Poetic is a useful tool for automating repetitive tasks or executing keyboard macros.

The application is built using Python and PySide6 for the user interface, along with `pynput` for handling keyboard interactions.

**IMPORTANT NOTES:**

*   📜 **Configuration File:** User settings (language, window size, hotkeys, recorded macros, etc.) are stored in `autokeyboard_config.json` in the application's root directory.
*   🚀 **Quick Run Scripts:** `run.bat` (Windows) and `run.sh` (Linux/macOS) files are provided to automate virtual environment creation (if not present) and dependency installation.

## Features

*   **Dual Mode Operation:**
    *   **AutoTyper Mode:**
        *   Automated typing of user-defined text or special key combinations (e.g., `<enter>`, `<f1>`).
        *   Adjustable typing interval (in milliseconds).
        *   Configurable repetition count (0 for infinite).
        *   Dedicated hotkey (default F9, changeable) to start/stop auto-typing.
    *   **Recorder & Player Mode (Advanced View):**
        *   Record sequences of keyboard actions (key presses, releases, and precise timings between them).
        *   Visual countdown overlay before recording starts.
        *   Dedicated hotkeys (defaults F10 for record, F11 for play, changeable) for starting/stopping recording and playback.
        *   Recorded actions displayed in a table (Key, Action, Delay).
        *   Playback of recorded sequences with adjustable repetition count (0 for infinite).
        *   Option to clear recorded actions.
*   **User-Friendly Interface:**
    *   Intuitive GUI built with PySide6.
    *   Custom title bar with standard window controls (minimize, maximize, close) and custom styling.
    *   Support for window dragging and resizing.
    *   Smooth animations for window open/close and page transitions.
*   **Multilingual Support:**
    *   Interface available in English, Vietnamese (Tiếng Việt), and Japanese (日本語).
    *   Easy language switching via a dropdown menu in the title bar.
*   **Configuration Management:**
    *   Persistent settings stored in `autokeyboard_config.json`.
    *   Saves language preference, window size/position, active mode, all hotkeys, AutoTyper settings, and recorded macros.
    *   Functions to "Load Config", "Save As...", and "Save Current" configuration.
*   **Hotkey Management:**
    *   Easy-to-use interface for changing hotkeys for AutoTyper, Record Start/Stop, and Playback Start/Stop.
    *   Hotkey conflict detection to prevent assigning the same hotkey to multiple actions.
*   **Cross-Platform Compatibility:**
    *   Includes `run.bat` for Windows and `run.sh` for Linux/macOS to simplify setup and execution.
    *   These scripts handle virtual environment creation and dependency installation.
*   **Status & Feedback:**
    *   Real-time status updates within the application.
    *   Visual countdown overlay for recording.
    *   Informative dialog boxes for errors and confirmations.

## Prerequisites (To run from source)

1.  **Python:** Python 3.x is recommended. The `run.bat`/`run.sh` scripts will attempt to use `python` (Windows) or `python3`/`python` (Linux/macOS) available in PATH.
2.  **Pip:** Python package installer (usually comes with Python).

## Installation & Running the Application (From source)

The easiest way to run the application is by using the provided scripts:

1.  **Download Source Code:**
    *   Clone this repository or download it as a ZIP and extract it.

2.  **Run the setup and launch script:**
    *   **On Windows:**
        *   Navigate to the `windows` directory within the project.
        *   Execute `run.bat`.
    *   **On Linux/macOS:**
        *   Open a terminal, navigate to the `linux-mac` directory within the project.
        *   Make the script executable: `chmod +x run.sh`
        *   Run the script: `./run.sh`

    These scripts will:
    *   Check for and create a Python virtual environment named `venv` in the project root (if it doesn't exist).
    *   Activate the virtual environment.
    *   Install necessary dependencies from `requirements.txt`.
    *   Launch the application.

**Manual Setup (If you prefer not to use scripts):**

1.  **Download source code.**
2.  Open a terminal or command prompt, navigate to the project's root directory.
3.  **(Recommended)** Create and activate a Python virtual environment:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Run the application:
    ```bash
    python main.py
    ```

## Usage Guide

Once the application is running:

*   **Switching Modes:** Use the "Advanced" / "AutoTyper" button on the title bar to toggle between AutoTyper mode and Recorder/Player mode.
*   **Language Selection:** Use the language dropdown menu on the title bar.
*   **AutoTyper Mode:**
    *   **Text/Key:** Enter the text you want to auto-type. For special keys, use the `<key_name>` format (e.g., `<enter>`, `<f12>`, `<space>`).
    *   **Interval:** Set the time (in ms) between each type/key press.
    *   **Repetitions:** Set the number of repetitions (0 for infinite).
    *   **Hotkey:** Default is F9. Click "Change Hotkey" to set a new one. Press this hotkey to Start/Stop.
    *   **Start/Stop Buttons:** Can also be used to initiate/halt typing.
*   **Recorder & Player Mode (Advanced):**
    *   **Record/Stop Hotkey:** Default F10. Used to start (after a countdown) and stop recording. Changeable via "Change Rec. Hotkey" button.
    *   **Play/Stop Hotkey:** Default F11. Used to start/stop playback of recorded actions. Changeable via "Change Play Hotkey" button.
    *   **Repetitions (Playback):** Set the number of times the action sequence will be played (0 for infinite).
    *   **Start Recording / Stop Recording Button:** Initiates/stops the recording process.
    *   **Play Recording / Stop Playing Button:** Starts/stops playback.
    *   **Clear Recording Button:** Clears all recorded actions from the table.
    *   **Events Table:** Displays recorded keys, actions (press/release), and delays.
*   **Configuration Management:**
    *   **Load Config:** Load settings from a `.json` file.
    *   **Save As...:** Save the current configuration to a new `.json` file.
    *   **Save Current:** Save the current configuration to the `autokeyboard_config.json` file being used.
    Configuration includes language, window state, AutoTyper settings, Recorder/Player settings, and hotkeys.

## Folder Structure (Simplified)

```
autokeyboard/
├── assets/               # Assets like icons
│   └── icon.ico
├── core/                 # Core logic (translations, workers)
│   ├── translations.py
│   └── workers.py
├── gui/                  # User interface code (pages, windows, custom widgets)
│   ├── autotyper_page.py
│   ├── base_main_window.py
│   ├── constants.py
│   ├── countdown_overlay.py
│   ├── custom_title_bar.py
│   ├── main_window.py
│   └── recorder_page.py
├── linux-mac/            # Run script for Linux/macOS
│   └── run.sh
├── windows/              # Run script for Windows
│   └── run.bat
├── venv/                 # (Virtual environment directory, created by scripts)
├── .gitignore
├── autokeyboard_config.json # Default/saved configuration file
├── main.py               # Main application entry point
└── requirements.txt      # List of Python dependencies
```

## Technologies Used

*   **Python**
*   **PySide6:** Qt for Python (GUI).
*   **pynput:** Library to control and monitor input devices (keyboard).

</details>

<!-- Japanese -->
<details>
<summary>🇯🇵 日本語</summary>

## AutoTyper Poetic - 高度なキーボード自動化 ᓚᘏᗢ

## 概要

**AutoTyper Poetic**は、キーボード入力タスクを自動化するために設計されたデスクトップアプリケーションです。テキストやキーを繰り返し入力するための基本的な**オートタイパー**モードと、複雑なキーボードアクションシーケンスを記録・再生するための高度な**レコーダー＆プレーヤー**モードの2つの主要なモードを提供します。直感的なインターフェース、多言語サポート、カスタマイズ可能なホットキー、柔軟な設定管理機能を備えたAutoTyper Poeticは、反復的な作業を自動化したり、キーボードマクロを実行したりするのに役立つツールです。

このアプリケーションは、PythonとPySide6（ユーザーインターフェース用）、および`pynput`（キーボードインタラクション処理用）を使用して構築されています。

**重要な注意点:**

*   📜 **設定ファイル:** ユーザー設定（言語、ウィンドウサイズ、ホットキー、記録されたマクロなど）は、アプリケーションのルートディレクトリにある`autokeyboard_config.json`に保存されます。
*   🚀 **クイック実行スクリプト:** `run.bat`（Windows）および`run.sh`（Linux/macOS）ファイルが提供されており、仮想環境の作成（存在しない場合）と依存関係のインストールを自動化します。

## 機能

*   **デュアルモード操作:**
    *   **オートタイパーモード:**
        *   ユーザー定義のテキストまたは特殊キーの組み合わせ（例：`<enter>`、`<f1>`）の自動入力。
        *   調整可能な入力間隔（ミリ秒単位）。
        *   設定可能な繰り返し回数（0で無限）。
        *   自動入力を開始/停止するための専用ホットキー（デフォルトF9、変更可能）。
    *   **レコーダー＆プレーヤーモード（詳細表示）:**
        *   キーボードアクションのシーケンス（キー押下、解放、それらの間の正確なタイミング）を記録。
        *   記録開始前の視覚的なカウントダウンオーバーレイ。
        *   記録と再生を開始/停止するための専用ホットキー（記録はデフォルトF10、再生はデフォルトF11、変更可能）。
        *   記録されたアクションをテーブルに表示（キー、アクション、遅延）。
        *   調整可能な繰り返し回数（0で無限）で記録されたシーケンスを再生。
        *   記録されたアクションをクリアするオプション。
*   **ユーザーフレンドリーなインターフェース:**
    *   PySide6で構築された直感的なGUI。
    *   標準のウィンドウコントロール（最小化、最大化、閉じる）とカスタムスタイリングを備えたカスタムタイトルバー。
    *   ウィンドウのドラッグとサイズ変更のサポート。
    *   ウィンドウの開閉およびページ遷移時のスムーズなアニメーション。
*   **多言語サポート:**
    *   英語、ベトナム語（Tiếng Việt）、日本語（日本語）で利用可能なインターフェース。
    *   タイトルバーのドロップダウンメニューによる簡単な言語切り替え。
*   **設定管理:**
    *   `autokeyboard_config.json`に永続的に保存される設定。
    *   言語設定、ウィンドウのサイズ/位置、アクティブモード、すべてのホットキー、オートタイパー設定、記録されたマクロを保存。
    *   「設定読込」、「名前を付けて保存...」、「現設定保存」機能。
*   **ホットキー管理:**
    *   オートタイパー、記録開始/停止、再生開始/停止のホットキーを変更するための使いやすいインターフェース。
    *   複数のアクションに同じホットキーが割り当てられるのを防ぐためのホットキー競合検出。
*   **クロスプラットフォーム互換性:**
    *   セットアップと実行を簡素化するためのWindows用`run.bat`とLinux/macOS用`run.sh`が付属。
    *   これらのスクリプトは、仮想環境の作成と依存関係のインストールを処理します。
*   **ステータスとフィードバック:**
    *   アプリケーション内でのリアルタイムのステータス更新。
    *   記録時の視覚的なカウントダウンオーバーレイ。
    *   エラーや確認のための情報ダイアログボックス。

## 前提条件（ソースから実行する場合）

1.  **Python:** Python 3.xを推奨します。`run.bat`/`run.sh`スクリプトは、PATHで利用可能な`python`（Windows）または`python3`/`python`（Linux/macOS）を使用しようとします。
2.  **Pip:** Pythonパッケージインストーラー（通常Pythonに付属）。

## インストールとアプリケーションの実行（ソースから）

アプリケーションを実行する最も簡単な方法は、提供されているスクリプトを使用することです。

1.  **ソースコードのダウンロード:**
    *   このリポジトリをクローンするか、ZIPとしてダウンロードして展開します。

2.  **セットアップおよび起動スクリプトの実行:**
    *   **Windowsの場合:**
        *   プロジェクト内の`windows`ディレクトリに移動します。
        *   `run.bat`を実行します。
    *   **Linux/macOSの場合:**
        *   ターミナルを開き、プロジェクト内の`linux-mac`ディレクトリに移動します。
        *   スクリプトに実行権限を付与します: `chmod +x run.sh`
        *   スクリプトを実行します: `./run.sh`

    これらのスクリプトは次の処理を行います:
    *   プロジェクトルートに`venv`という名前のPython仮想環境を確認し、存在しない場合は作成します。
    *   仮想環境をアクティブ化します。
    *   `requirements.txt`から必要な依存関係をインストールします。
    *   アプリケーションを起動します。

**手動セットアップ（スクリプトを使用したくない場合）:**

1.  **ソースコードをダウンロードします。**
2.  ターミナルまたはコマンドプロンプトを開き、プロジェクトのルートディレクトリに移動します。
3.  **(推奨)** Python仮想環境を作成してアクティブ化します:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```
4.  依存関係をインストールします:
    ```bash
    pip install -r requirements.txt
    ```
5.  アプリケーションを実行します:
    ```bash
    python main.py
    ```

## 使用方法

アプリケーションの起動後:

*   **モードの切り替え:** タイトルバーの「高度な設定」/「オートタイパー」ボタンを使用して、オートタイパーモードとレコーダー/プレーヤーモードを切り替えます。
*   **言語選択:** タイトルバーの言語ドロップダウンメニューを使用します。
*   **オートタイパーモード:**
    *   **テキスト/キー:** 自動入力したいテキストを入力します。特殊キーの場合は、`<key_name>`形式を使用します（例：`<enter>`、`<f12>`、`<space>`）。
    *   **間隔:** 各入力/キー押下の間の時間（ミリ秒）を設定します。
    *   **繰り返し回数:** 繰り返しの回数を設定します（0で無限）。
    *   **ホットキー:** デフォルトはF9です。「ホットキー変更」をクリックして新しいホットキーを設定します。このホットキーを押して開始/停止します。
    *   **開始/停止ボタン:** 入力を開始/停止するためにも使用できます。
*   **レコーダー＆プレーヤーモード（高度な設定）:**
    *   **録画/停止ホットキー:** デフォルトF10。記録を開始（カウントダウン後）および停止するために使用します。「録画ホットキー変更」ボタンで変更可能です。
    *   **再生/停止ホットキー:** デフォルトF11。記録されたアクションの再生を開始/停止するために使用します。「再生ホットキー変更」ボタンで変更可能です。
    *   **繰り返し回数（再生）:** アクションシーケンスを再生する回数を設定します（0で無限）。
    *   **録画開始 / 録画停止ボタン:** 記録プロセスを開始/停止します。
    *   **再生 / 再生停止ボタン:** 再生を開始/停止します。
    *   **録画を消去ボタン:** テーブル内のすべての記録されたアクションをクリアします。
    *   **イベントテーブル:** 記録されたキー、アクション（押す/離す）、遅延を表示します。
*   **設定管理:**
    *   **設定読込:** `.json`ファイルから設定を読み込みます。
    *   **名前を付けて保存...:** 現在の設定を新しい`.json`ファイルに保存します。
    *   **現設定保存:** 現在の設定を使用中の`autokeyboard_config.json`ファイルに保存します。
    設定には、言語、ウィンドウの状態、オートタイパー設定、レコーダー/プレーヤー設定、およびホットキーが含まれます。

## フォルダ構成（簡易版）

```
autokeyboard/
├── assets/               # アイコンなどのアセット
│   └── icon.ico
├── core/                 # コアロジック（翻訳、ワーカー）
│   ├── translations.py
│   └── workers.py
├── gui/                  # ユーザーインターフェースコード（ページ、ウィンドウ、カスタムウィジェット）
│   ├── autotyper_page.py
│   ├── base_main_window.py
│   ├── constants.py
│   ├── countdown_overlay.py
│   ├── custom_title_bar.py
│   ├── main_window.py
│   └── recorder_page.py
├── linux-mac/            # Linux/macOS用実行スクリプト
│   └── run.sh
├── windows/              # Windows用実行スクリプト
│   └── run.bat
├── venv/                 # （仮想環境ディレクトリ、スクリプトによって作成）
├── .gitignore
├── autokeyboard_config.json # デフォルト/保存された設定ファイル
├── main.py               # メインアプリケーションエントリポイント
└── requirements.txt      # Python依存関係リスト
```

## 使用技術

*   **Python**
*   **PySide6:** Python用Qt（GUI）。
*   **pynput:** 入力デバイス（キーボード）を制御および監視するためのライブラリ。


</details>
