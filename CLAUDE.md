# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## 執行與開發

```powershell
# 啟動程式
.venv\Scripts\python.exe desktop_pet.py

# 安裝依賴
.venv\Scripts\pip.exe install pillow pygame pyinstaller

# 語法檢查（無測試框架）
.venv\Scripts\python.exe -m py_compile desktop_pet.py

# 打包為 exe（Windows）
.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name DesktopPet --add-data "assets;assets" desktop_pet.py
```

## 素材路徑

`assets/` 已納入版本控制（非 gitignore）。`resource_path()` 優先從 `_MEIPASS`（打包後）或 `__file__` 所在目錄解析，相容打包與開發兩種情境。

```
assets/
  characters.json          # 角色顯示名稱對應表
  icon.ico
  帥潮教授/                  # default 角色（AnimationCache 優先讀此目錄）
    idle/ coding/ studying/ eating/ drag/ alert/ sleep/
  小紫/                      # FREE_CHARS 之一
    idle/ coding/ studying/ eating/ drag/ alert/ sleep/
  貓咪/ 兔兔/ 企鵝/ 狐狸/ 小龍/  # GACHA_POOL 角色，需解鎖
    idle/ coding/ studying/ eating/ drag/ alert/ sleep/
  music/
    *.mp3 / *.ogg / *.wav  # .gitignore 排除
```

`data.json` 存於執行檔同層目錄（`data_file_path()` 控制），已加入 `.gitignore`。

## 架構：MVC 四層（單檔 desktop_pet.py，約 3800 行）

```
Layer 1 — Model
  PetModel            資料層：金幣、心情、背包、設定、統計、待辦、角色解鎖
                      → _AutoSaver（daemon 執行緒非同步寫 JSON）
                      → sync_save()（_quit 前同步寫一次）

Layer 2 — Services（無 tkinter，可單獨測試）
  PomodoroTimer       root.after(1000) 狀態機：work → rest → long_rest
  MusicPlayer         pygame 背景執行緒漸入漸出 + 曲庫掃描
  AnimationCache      PNG 序列快取，多角色路徑，缺失狀態 fallback idle

Layer 3 — View（純渲染）
  PetView             主視窗（overrideredirect + transparentcolor）
  TimerBubble         Canvas 圓角 HUD + 進度條
  SpeechBubble        浮動對話氣泡 Toplevel
  _PopupMenu          自訂右鍵選單（Toplevel 模擬，解決 Windows 立即消失 bug）
  EggGachaScreen      孵蛋互動動畫（7 次點擊 + 粒子爆炸 + 真實 sprite 揭曉）
  FarewellScreen      放生告別動畫（日落場景 + sprite 漸遠 + 打字機台詞）
  ShopView / BackpackView / StatsView / SettingsView
  TodoView + TodoEditDialog   Todoist 風格待辦清單 + 編輯對話框
  MusicView           音樂管理視窗（選播 / 刪除 / 匯入）

Layer 4 — Controller
  PetController       事件 → Model → View 協調
                      → 對話排程：_checkin_id、_idle_chat_id
                      → 今日待辦輪播：_todo_idle_id、_todo_today_idx
                      → 到期提醒檢查：_todo_check_id（每分鐘）
```

**資料流**：View 事件 → Controller → Model `_dirty()` → 非同步存檔 → Controller 更新 View

**角色路徑解析**：
- `character == "default"` → 優先 `assets/帥潮教授/{state}/`，fallback `assets/{state}/`
- 其他角色 → `assets/{character}/{state}/`
- 掃描時排除 `帥潮教授`（= default 的子目錄）避免重複

## 常數速查

```python
FREE_CHARS           = {"default", "小紫"}     # 永遠可用
GACHA_POOL           # 貓咪/兔兔/企鵝/狐狸/小龍（含稀有度、蛋色、描述）
GACHA_WEIGHTS        # 抽蛋機率權重

_CHECKIN_FIRST_MS    = 120_000  # 工作開始後 2 分鐘第一次提醒
_CHECKIN_INTERVAL_MS = 300_000  # 之後每 5 分鐘
_IDLE_CHAT_MS        = 180_000  # 發呆每 3 分鐘閒聊
_TODO_REMIND_MS      = 300_000  # 今日待辦輪播間隔（5 分鐘）
_TODO_CHECK_MS       =  60_000  # 到期提醒掃描間隔（1 分鐘）
```

## 已知待修問題

| 問題 | 位置 | 狀態 |
|------|------|------|
| 休息中套用快速預設後音樂/動畫不同步 | `update_config()` | Issue #5 開著 |

## GitHub 工作流程

- 分支命名：`fix/<issue號>-<簡短說明>`、`feat/<功能名>`
- commit 格式：`fix/feat/chore/refactor/perf/docs: 說明`，修 bug 加 `fixes #N`
- PR 合併目標：`master`

## 文件維護規則

| 修改類型 | 需更新 |
|---------|--------|
| 新增功能 | `README.md` 功能表、`CLAUDE.md` 架構段 |
| 修正 Bug | commit message 加 `fixes #N`；問題修好從本表移除 |
| 新增/刪除類別 | `CLAUDE.md` 架構段 |
| 開新 Issue | `gh issue create` |
| 關閉 Issue | `gh issue close N --comment "說明"` |
