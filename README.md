# Power Scheduler for Linux - Tkinter

[English Version](README_en.md)

一個使用 Python 和 Tkinter 打造的圖形化工具，專為 Linux 桌面環境設計，

讓您輕鬆排程各種系統任務，例如定時關機、重新開機、鬧鐘提醒等。

這個專案是把以前實做的 [Power-Auto-Shutdown](https://github.com/twtrubiks/Power-Auto-Shutdown) 改成用 Python Tkinter 完成,

整個專案幾乎是用 AI 完成的, 自己測試了一下, 應該是沒有什麼問題.

## 應用程式截圖

畫面

![alt tag](Screenshot_2.png)

執行畫面

![alt tag](Screenshot_1.png)

設定一分鐘前通知

![alt tag](https://cdn.imgpile.com/f/ae5OfFE_xl.png)

設定時間到

![alt tag](https://cdn.imgpile.com/f/UVOx7xU_xl.png)

---

## 功能特色

- **多種排程模式**:
  - **指定時間**: 在特定的年、月、日、時、分、秒執行任務。
  - **倒數計時**: 在一段時間後執行任務。
  - **每天**: 在每天的固定時間執行任務。
  - **每隔**: 每隔一段時間重複執行任務。
- **豐富的任務選項**:
  - **系統操作**: 關機、重新開機、休眠 (Suspend)。
  - **桌面環境操作**: 登出 (支援 KDE, GNOME, XFCE)。
  - **螢幕操作**: 立即關閉螢幕。
  - **鬧鐘**: 在指定時間播放音效並顯示提醒視窗。
  - **顯示訊息**: 彈出一個自訂內容的訊息框。
  - **執行程式**: 執行您指定的任何應用程式或腳本。
  - **執行指令**: 執行自訂的 Shell 指令。
- **人性化設計**:
  - **任務前提醒**: 可選擇在任務執行前 1 分鐘彈出提醒。
  - **隨系統啟動**: 可輕鬆設定是否要開機自動執行本程式。
  - **狀態顯示**: 清晰顯示目前任務狀態與剩餘時間。
  - **暫停/繼續**: 隨時暫停或繼續進行中的倒數任務。
  - **自動偵測桌面環境**: 為「登出」功能自動選擇合適的指令。
  - **安全性**: 對於需要管理員權限的系統操作 (如關機)，會透過 `pkexec` 安全地請求授權。

---

## 依賴與安裝

本程式主要依賴 Python 3.12 和其內建的 Tkinter 函式庫。此外，部分功能需要系統已安裝特定的指令行工具。

### 必要依賴

- **Python 3**: 大多數 Linux 發行版已內建。

- **Tkinter**: `pip install tkinter` 或 `sudo apt install python3-tk`

- **pkexec**: Polkit 的一部分，用於請求管理員權限，通常系統已內建。

### 功能性依賴 (根據您使用的功能)

- **ffplay**: 用於「鬧鐘」功能播放音效。`ffplay` 是 `ffmpeg` 套件的一部分。

  ```bash
  # Debian/Ubuntu
  sudo apt-get install ffmpeg

  # Fedora
  sudo dnf install ffmpeg

  # Arch Linux
  sudo pacman -S ffmpeg
  ```

- **xset**: 用於「關閉螢幕」功能。通常由 `xorg-xinit` 或類似套件提供，桌面環境大多已安裝。

---

## 如何使用

- 執行程式

```bash
python3 power_scheduler.py
```

- 設定任務:
  - **1. 選擇任務**: 從左側列表中選擇一個您想執行的任務。對於「鬧鐘」、「顯示訊息」等。
  - **2. 設定時間**: 在右側選擇一個時間模式 (指定時間、倒數等)，並設定好時間。
  - **3. 環境設定**: 通常程式會自動偵測您的桌面環境，如果「登出」功能不正常，您可以在此手動指定。
  - **4. 執行**: 點擊「執行」按鈕啟動排程。

---

## 功能詳解

### 任務類型

- **關機/重新開機/休眠**: 這些是系統級操作，執行時會跳出密碼輸入框以獲取授權。
- **登出**: 會根據您選擇的桌面環境 (KDE, GNOME, XFCE) 執行對應的登出指令。
- **鬧鐘**: 您需要先點擊按鈕選擇一個音效檔 (如 `.mp3`, `.wav`)。時間到時會播放聲音並彈出一個可點擊「停止」的視窗。
- **執行程式/指令**:
  - **執行程式**: 選擇一個您電腦上的執行檔或腳本。
  - **執行指令**: 輸入一段 Shell 指令 (例如 `notify-send "Hello World"` 或 `cp /path/to/source /path/to/destination`)。
    > **警告**: 執行任意指令可能存在安全風險，請謹慎使用。

### 隨系統啟動

勾選「隨系統啟動」選項後，程式會在 `~/.config/autostart/` 目錄下建立一個 `.desktop` 檔案。

這會讓您在登入桌面環境時自動啟動 Power Scheduler, 取消勾選則會刪除該檔案。

`~/.config/autostart/` 是 Linux 桌面環境中用來設定「開機自動啟動」應用程式的標準目錄,

他是屬於使用者層級 (User Level),

不像之前介紹過的 [systemctl 命令是系統服務管理指令](https://github.com/twtrubiks/linux-note/tree/master/systemctl-tutorial)屬於 系統層級 (System Level).

---

## 注意事項

- **權限問題**: 關機、重啟等操作需要管理員權限。本程式使用 `pkexec` 來處理，它會彈出一個對話框讓您輸入密碼。請確保您的系統已安裝並設定好 Polkit。
- **Wayland 環境**: 在 Wayland 顯示伺服器下，「關閉螢幕」功能 (`xset`) 可能無法運作。這是 `xset` 工具本身的限制。
- **指令安全性**: 「執行指令」功能非常強大，但也帶來風險。請勿執行來源不明或您不了解其作用的指令。

---

## 授權條款

本專案採用 [MIT License](LICENSE)。
