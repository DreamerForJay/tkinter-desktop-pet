# 桌面小寵物 Desktop Pet

> 視窗程式設計期末專題　|　彰化師範大學 資訊工程學系

一隻常駐桌面角落的虛擬寵物。結合**番茄鐘工作法**、**多角色 Gacha 系統**、**Todoist 風格待辦清單**與**心情養成機制**，讓讀書和寫程式多一份陪伴與動力。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 功能特色

| 功能 | 說明 |
|------|------|
| 多角色系統 | 預設角色免費使用；Gacha 角色於商店購蛋解鎖，孵蛋動畫含真實 sprite 揭曉 |
| 放生動畫 | 日落場景，角色 sprite 漸遠離去，打字機台詞，可隨時略過 |
| 匯入自訂角色 | 右鍵選單直接匯入含 `idle/` 子目錄的任意資料夾 |
| 番茄鐘計時器 | 工作 / 短休息 / 大休息三階段，彩色 HUD 進度條，完成後播放提示音並自動獎勵金幣 |
| 角色對話氣泡 | 工作中定時關心、心情警示、吃東西反應、發呆閒聊 |
| 待辦清單 | Todoist 風格分組顯示、優先度色條、相對日期、個別到期提醒音效 |
| 音樂管理 | 視窗化曲目管理，支援選播、刪除、匯入（MP3 / OGG / WAV），淡入淡出切換 |
| 統計（Forest 風格） | 累積專注時間、今日番茄、連續天數、emoji 森林成長視覺化 |
| 金幣系統 | 番茄鐘 +10（可加倍）、每日簽到 +5；商店購買食物與道具 |
| 心情養成 | 每 90 秒衰減 −1，低於 60% / 30% 觸發對話提醒 |
| 個人化設定 | 寵物名稱、番茄鐘時長、每輪節數、自動開始、永遠置頂 |
| 自動存檔 | 每次狀態變動立即以背景執行緒寫入 `data.json`，重啟後完整保留 |
| 結束確認 | 點選結束程式後跳出確認視窗，防止誤觸 |

---

## 安裝與執行

### 必要環境

- Python 3.10+
- `tkinter`（Python 標準安裝內建）

### 選用依賴

```bash
pip install pillow pygame
```

| 套件 | 用途 | 未安裝時的行為 |
|------|------|----------------|
| Pillow | 載入角色 PNG 動畫序列 | 顯示文字備用角色 `(ovo)`，其餘功能正常 |
| pygame | 背景音樂播放（淡入淡出） | 靜音執行，其餘功能正常 |

### 執行

```bash
python desktop_pet.py
```

---

## 操作說明

| 操作 | 功能 |
|------|------|
| 左鍵拖曳 | 將寵物移動至螢幕任意位置 |
| 右鍵單擊 | 開啟主選單 |

主選單包含：角色狀態切換、角色切換（含放生 / 匯入）、番茄鐘控制、快速餵食、商店、背包、音樂管理、待辦清單、統計、設定、結束程式。

### 番茄鐘快速預設

| 預設 | 工作 | 短休息 | 大休息 |
|------|------|--------|--------|
| 經典 | 25 分 | 5 分 | 15 分 |
| 雙倍 | 50 分 | 10 分 | 30 分 |
| 迷你 | 15 分 | 3 分 | 10 分 |

### 角色系統

程式以 `assets/` 下的資料夾名稱作為角色 ID，透過 `characters.json` 映射顯示名稱。

**預設角色**（永遠可用）

| 角色 | 資料夾 |
|------|--------|
| 帥潮教授 | `assets/帥潮教授/` |
| 小紫 | `assets/小紫/` |

**Gacha 角色**（商店購買角色蛋 30 金幣解鎖）

| 角色 | 稀有度 | 機率 |
|------|--------|------|
| 橘橘貓咪 | 普通 | 35% |
| 雪白兔兔 | 普通 | 30% |
| 企鵝紳士 | 稀有 | 18% |
| 狡黠狐狸 | 稀有 | 12% |
| 神秘小龍 | 傳說 |  5% |

### 商店道具

**食物**（補充心情值）

| 道具 | 費用 | 心情 |
|------|------|------|
| 蘋果 | 2 | +15 |
| 珍珠奶茶 | 3 | +20 |
| 咖啡 | 4 | +25 |
| 漢堡 | 5 | +30 |
| 壽司 | 6 | +35 |
| 生日蛋糕 | 8 | +50 |

**道具**

| 道具 | 費用 | 效果 |
|------|------|------|
| 快樂藥水 | 10 | 心情立即 100% |
| 神秘禮盒 | 12 | 隨機獲得 5〜30 金幣 |
| 加倍符文 | 15 | 下一顆番茄金幣 ×2 |
| 蝴蝶結 | 20 | 裝飾品 |
| 角色蛋 | 30 | 孵化隨機 Gacha 角色 |

---

## 專案結構

```
Dpet/
├── desktop_pet.py          # 主程式（單檔 MVC，~3,800 行）
├── data.json               # 自動產生的存檔（.gitignore 排除）
└── assets/
    ├── characters.json     # 角色顯示名稱對應表
    ├── icon.ico
    ├── 帥潮教授/            # default 角色素材
    │   ├── idle/           # 待機動畫 PNG 序列（必要）
    │   ├── coding/
    │   ├── studying/
    │   ├── eating/
    │   ├── drag/
    │   ├── alert/
    │   └── sleep/
    ├── 小紫/                # 第二預設角色（同上結構）
    ├── 貓咪/ 兔兔/ 企鵝/ 狐狸/ 小龍/   # Gacha 角色（需解鎖）
    └── music/
        └── *.mp3           # 背景音樂（.gitignore 排除）
```

> 動畫資料夾內的 PNG 以自然數排序（`slice_1.png`、`slice_2.png`…）載入並循環播放；缺少的動畫狀態自動 fallback 至 `idle/`。

---

## 架構說明（MVC）

```mermaid
flowchart TD
    subgraph Controller
        C[PetController\n事件協調 / 業務邏輯\n番茄獎勵 / 對話排程 / 角色切換]
    end
    subgraph Model
        M[PetModel\n金幣 / 心情 / 背包 / 設定\n待辦 / 角色解鎖 / 統計]
        AS[_AutoSaver\ndaemon 執行緒\n非同步寫 JSON]
        M --> AS
    end
    subgraph Services
        PT[PomodoroTimer\nroot.after 狀態機]
        MP[MusicPlayer\npygame 淡入淡出]
        AC[AnimationCache\nPNG 序列快取\n多角色路徑解析]
    end
    subgraph View
        PV[PetView\n主視窗 / 動畫驅動]
        SB[SpeechBubble]
        TB[TimerBubble]
        PM[_PopupMenu]
        EG[EggGachaScreen]
        FS[FarewellScreen]
        TV[TodoView]
        MV[MusicView]
        SW[ShopView / BackpackView\nStatsView / SettingsView]
        PV --> SB & TB & PM & EG & FS & TV & MV & SW
    end

    C -->|讀寫資料| M
    C -->|更新 UI| PV
    C -->|控制| PT & MP
    PV -->|取幀| AC
```

整個專案以單一檔案 `desktop_pet.py` 實作，分為四個明確分層：

| 層級 | 類別 | 職責 |
|------|------|------|
| **Model** | `PetModel`、`_AutoSaver` | 純資料層，不含任何 tkinter。`_AutoSaver` 以 daemon 執行緒非同步寫入 JSON，退出前 `sync_save()` 同步補寫。 |
| **Services** | `AnimationCache`、`MusicPlayer`、`PomodoroTimer` | 業務邏輯，不依賴 tkinter。支援多角色路徑解析、pygame 淡入淡出、`root.after()` 驅動的計時器。 |
| **View** | `PetView` 及所有子視窗 | 純渲染層，不含業務邏輯。透過 `set_controller()` 連結後才啟動事件綁定。 |
| **Controller** | `PetController` | 接收 View 事件 → 操作 Model → 驅動 View 更新。管理對話排程、今日待辦輪播、到期提醒掃描。 |

### 主要元件說明

- **`TimerBubble`** — Canvas 繪製圓角計時 HUD，顯示在寵物頭頂；含進度條與階段文字，三色區分工作（紅）/ 短休息（綠）/ 大休息（藍）。

- **`SpeechBubble`** — 獨立 `Toplevel` 浮動視窗，Canvas 繪製圓角氣泡 + 向下三角尾巴；拖曳寵物時跟隨移動，N 秒後自動隱藏。

- **`_PopupMenu`** — 以 `Toplevel` + `Frame` 手刻右鍵選單，解決 `tk.Menu.tk_popup()` 在 Windows 非阻塞導致立即消失的問題；支援子選單 Hover 觸發與全域點擊關閉。

- **`EggGachaScreen`** — 7 次點擊觸發龜裂動畫（`_cracks` 列表）→ 粒子爆炸（`_particles`）→ 揭曉時以 PIL 預載並縮放角色真實 idle sprite 動畫。

- **`FarewellScreen`** — Canvas 日落天空場景，預載 10 個縮放尺寸的角色 sprite，根據位移進度選取對應尺寸實現漸縮效果；打字機台詞，可略過。

- **`PomodoroTimer`** — 支援工作→短休息→（第 N 節）→大休息的完整週期；`update_config()` 可在執行中熱更新所有參數而不中斷現有計時。

- **`AnimationCache`** — `character == "default"` 時優先讀取 `assets/帥潮教授/{state}/`，PNG 以 `_nat_key()` 自然排序（避免 `slice_10 < slice_2` 的字母順序錯誤），缺失狀態 fallback idle。

---

## 存檔格式

存檔路徑：執行檔或 `.py` 的同層目錄下的 `data.json`。

```json
{
  "pet_name": "小白",
  "coins": 0,
  "happiness": 100,
  "bonus_mult": 1,
  "last_checkin": "",
  "inventory": {},
  "first_launch": false,
  "unlocked_chars": [],
  "todos": [],
  "stats": {
    "pomodoro_done": 0,
    "coins_earned": 0,
    "coins_spent": 0,
    "items_used": 0,
    "focus_minutes": 0,
    "today_count": 0,
    "today_date": "",
    "streak_days": 0,
    "last_focus_date": ""
  },
  "settings": {
    "work_min": 25,
    "rest_min": 5,
    "long_rest_min": 15,
    "sessions_before_long": 4,
    "auto_start": false,
    "always_on_top": true,
    "character": "default"
  }
}
```

載入時使用 `_deep_merge()`：已定義欄位從存檔更新，動態欄位（`inventory`、`todos`）完整保留，未知舊欄位自動捨棄，確保版本向前相容。

---

## 素材規格

在 `assets/` 下建立以角色名稱命名的資料夾，至少需要 `idle/` 子目錄：

```
assets/角色名稱/
├── idle/       # PNG 序列（必要）
├── coding/
├── studying/
├── eating/
├── drag/
├── alert/
└── sleep/      # 可選，缺少時自動 fallback idle
```

- 建議解析度：200×200 px，RGBA 透明背景
- 命名：`0.png`、`1.png`… 或 `slice_1.png`、`slice_2.png`…（程式使用自然數排序）
- 透過右鍵選單 → 匯入角色素材直接加入，無需修改程式碼

---

## 打包為 exe（PyInstaller）

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name DesktopPet `
    --add-data "assets;assets" `
    desktop_pet.py
```

執行檔輸出至 `dist/DesktopPet.exe`，需將 `assets/` 資料夾放在 exe 同層目錄。`data.json` 也會儲存於 exe 同層目錄（非 PyInstaller 的臨時目錄 `_MEIPASS`）。

---

## 開發環境

- Python 3.12 / Windows 11
- Pillow 10、pygame 2.6、PyInstaller 6

---

## 授權

本專案以 [MIT License](LICENSE) 釋出，歡迎自由使用與修改。
