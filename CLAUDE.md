# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 執行與開發

```powershell
# 啟動程式
.venv\Scripts\python.exe desktop_pet.py

# 安裝依賴
.venv\Scripts\pip.exe install pillow pygame pyinstaller

# 語法檢查（無測試框架，用 py_compile 快速驗證）
.venv\Scripts\python.exe -m py_compile desktop_pet.py

# 打包成 exe（Windows）
.\build.bat
# 或手動：
.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name DesktopPet --add-data "assets;assets" desktop_pet.py
```

## 素材路徑

`assets/` 已加入 `.gitignore`，不進版本控制。本機實際路徑為 `assets/assets/...`（雙層）。程式內已相容兩種結構，`resource_path()` 優先從 `_MEIPASS`（打包後）或 `__file__` 所在目錄解析。

```
assets/assets/
  idle/ coding/ studying/ eating/ drag/
  music/study.mp3
  icon.ico
```

存檔路徑 `data.json` 在執行檔同層目錄（`data_file_path()` 函式控制），也已加入 `.gitignore`。

## 架構：MVC 分層

唯一主程式 `desktop_pet.py`，約 1900 行，分四層：

```
PetModel          資料層：金幣、心情、背包、設定、統計
                  → _AutoSaver（daemon 執行緒非同步寫 JSON）
                  → sync_save()（_quit 離開前同步寫一次）

PomodoroTimer     Service：root.after() 驅動的計時狀態機
MusicPlayer       Service：pygame 背景執行緒漸入漸出
AnimationCache    Service：PNG 序列快取，支援多角色子目錄
SpeechBubble      Service：overrideredirect Toplevel 浮動對話氣泡

PetView           視圖層：主視窗 + TimerBubble + 子視窗工廠
ShopView / BackpackView / StatsView / SettingsView  子視窗

PetController     控制層：事件 → Model → View
                  → 對話排程：_checkin_id、_idle_chat_id
```

**資料流**：View 事件 → Controller 方法 → Model setter（自動呼叫 `_dirty()` 非同步存檔）→ Controller 再呼叫 View 更新 UI。

**動畫驅動**：`PetView._animate()` 以 `root.after(200)` 迴圈自驅，讀取 `_status`（Controller 設定）決定播哪組幀。Controller 的 `_status` 與 View 的 `_status` 各自獨立——`trigger_eating()` 只改 View，心情衰減 guard 看的是 Controller 的 `_status`。

## 已知待修問題

詳細紀錄在 `PROJECT_NOTES.md`，GitHub Issues 也有追蹤（#1–#5）。

| 問題 | 位置 | 狀態 |
|------|------|------|
| 右鍵選單 `finally: menu.unpost()` 立即關閉選單 | `show_menu()` ~1798 | 未修 |
| 吃東西 Controller `_status` 不同步，心情仍衰減 | `on_hp_tick()` ~1555 | 未修 |
| `SettingsView._apply()` 硬寫 `character="default"` | `_apply()` ~1146 | 未修 |
| `_do_work_checkin` 讀私有屬性 `_pomo._remain` | `~1896` | 未修 |
| `SpeechBubble` 在 root 銷毀後被 after 喚醒 | `_ensure_win()` ~695 | 未修 |

## 對話系統常數

```python
DIALOGUES          # 各情境台詞 dict（work_start / work_early / mid / late,
                   #   rest_start / long_rest_start, eating, idle, mid_hp, low_hp）
_CHECKIN_FIRST_MS    = 120_000  # 開始工作 2 分鐘後第一次提醒
_CHECKIN_INTERVAL_MS = 300_000  # 之後每 5 分鐘提醒
_IDLE_CHAT_MS        = 180_000  # 發呆狀態每 3 分鐘閒聊
```

## GitHub 工作流程

- 分支命名：`fix/<issue號>-<簡短說明>`、`feat/<issue號>-<功能名>`
- commit 格式：`fix/feat/chore/refactor/perf/docs: 說明`，修 bug 加 `fixes #N`
- PR 合併目標：`master`
