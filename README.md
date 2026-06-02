# Desktop Pet

視窗程式設計期末專題　|　彰化師範大學 資訊工程學系

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)](https://docs.python.org/3/library/tkinter.html)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

常駐桌面的虛擬寵物，結合番茄鐘工作法、多角色養成與 Todoist 風格待辦清單，以 MVC 架構實作於單一 Python 檔案（約 3,800 行）。

---

## 目錄

- [安裝](#安裝)
- [功能](#功能)
- [操作](#操作)
- [架構](#架構)
- [存檔格式](#存檔格式)
- [素材規格](#素材規格)
- [打包 exe](#打包-exe)

---

## 安裝

**必要**：Python 3.10+（`tkinter` 內建）

```bash
pip install pillow pygame
python desktop_pet.py
```

| 套件 | 用途 | 未安裝時 |
|------|------|----------|
| Pillow | 載入角色 PNG 動畫 | 以文字 `(ovo)` 取代，其餘正常 |
| pygame | 背景音樂播放 | 靜音執行，其餘正常 |

---

## 功能

### 角色系統

程式以 `assets/` 下的資料夾名稱作為角色 ID，透過 `characters.json` 映射顯示名稱。

**預設角色**（永遠可用）

| 角色 | 資料夾 |
|------|--------|
| 帥潮教授 | `assets/帥潮教授/` |
| 小紫 | `assets/小紫/` |

**Gacha 角色**（商店購蛋解鎖）

| 角色 | 稀有度 | 機率 |
|------|--------|------|
| 橘橘貓咪 | 普通 | 35% |
| 雪白兔兔 | 普通 | 30% |
| 企鵝紳士 | 稀有 | 18% |
| 狡黠狐狸 | 稀有 | 12% |
| 神秘小龍 | 傳說 |  5% |

- **孵蛋互動**：購買角色蛋後點擊 7 次，蛋殼龜裂動畫 → 粒子爆炸 → 揭曉真實角色動畫
- **放生**：Gacha 角色可放生（日落場景動畫，角色漸遠離去），完成後從解鎖清單移除
- **自訂匯入**：右鍵 → 切換角色 → 匯入角色素材，選取含 `idle/` 子目錄的資料夾即可加入

### 番茄鐘

- 工作 → 短休息 → 大休息三階段循環，寵物頭頂 HUD 顯示倒計時與彩色進度條
- 完成提示音：工作結束四音上行（C5-E5-G5-C6），休息結束三音下行（G5-E5-C5）
- 每完成一顆番茄 +10 金幣；加倍符文效果期間可達 ×2

| 快速預設 | 工作 | 短休息 | 大休息 |
|---------|------|--------|--------|
| 經典 | 25 分 | 5 分 | 15 分 |
| 雙倍 | 50 分 | 10 分 | 30 分 |
| 迷你 | 15 分 | 3 分 | 10 分 |

### 商店與心情

心情值每 90 秒自然衰減 −1，低於 60% / 30% 時角色主動提醒。購買食物後存入背包，使用即補充心情。

**食物**

| 品項 | 費用 | 心情 |
|------|------|------|
| 蘋果 | 2 | +15 |
| 珍珠奶茶 | 3 | +20 |
| 咖啡 | 4 | +25 |
| 漢堡 | 5 | +30 |
| 壽司 | 6 | +35 |
| 生日蛋糕 | 8 | +50 |

**道具**

| 品項 | 費用 | 效果 |
|------|------|------|
| 快樂藥水 | 10 | 心情立即 100% |
| 神秘禮盒 | 12 | 隨機獲得 5〜30 金幣 |
| 加倍符文 | 15 | 下一顆番茄金幣 ×2 |
| 蝴蝶結 | 20 | 裝飾品 |
| 角色蛋 | 30 | 孵化隨機 Gacha 角色 |

**金幣來源**：番茄鐘完成 +10、每日簽到 +5、神秘禮盒 5〜30 隨機。

### 待辦清單

- **分組顯示**：依到期日自動歸類（逾期 / 今天 / 明天 / 本週 / 之後 / 無截止日期）
- **優先度**：高（紅）/ 中（橙）/ 低（綠）以左側色條視覺化
- **相對日期**：「逾期 3 天」「今天 22:00」「明天 07:00」等格式
- **個別提醒**：每筆任務可設定到期前 N 分鐘提示音，程式每分鐘掃描一次到期狀態
- **快速新增**：視窗底部輸入列，Enter 直接建立任務
- **今日輪播**：每 5 分鐘在對話氣泡中依序提醒今日與逾期任務
- **篩選**：全部 / 未完成 / 今天 / 已完成，視窗可自由縮放

### 音樂管理

右鍵 → 音樂管理：顯示完整曲目列表，支援選播、刪除（同步移除磁碟檔案）、匯入（MP3 / OGG / WAV）。切換時 2 秒淡入淡出。

### 統計

| 指標 | 說明 |
|------|------|
| 累積專注 | 所有番茄鐘工作時間總和，格式化為 X 小時 Y 分 |
| 今日番茄 | 當日完成計數，跨日自動重置 |
| 連續天數 | 每日至少完成一顆番茄即計入，中斷歸零 |
| 我的森林 | 番茄數轉換為成長樹木：🌱 → 🌿 → 🌳 → 🌲 |

### 對話系統

工作開始後 2 分鐘第一次關心，之後每 5 分鐘一次；發呆狀態每 3 分鐘閒聊；吃東西、心情低落均有對應台詞。

---

## 操作

| 操作 | 效果 |
|------|------|
| 左鍵拖曳 | 移動寵物至螢幕任意位置 |
| 右鍵單擊 | 開啟主選單 |

主選單包含：角色狀態切換、角色切換（含放生 / 匯入）、番茄鐘控制、快速餵食、商店、背包、音樂管理、待辦清單、統計、設定、結束程式。

---

## 架構

整個專案實作於單一 `desktop_pet.py`，依 MVC 模式分為四層：

```
Model       PetModel          金幣、心情、背包、設定、待辦、角色解鎖、統計
            _AutoSaver        daemon 執行緒非同步寫入 JSON

Services    PomodoroTimer     root.after(1000) 驅動的狀態機
            MusicPlayer       pygame 背景執行緒，淡入淡出 + 曲庫掃描
            AnimationCache    PNG 序列快取，多角色路徑解析，缺失狀態 fallback idle

View        PetView           主視窗（overrideredirect + 透明色鍵）
            TimerBubble       頭頂倒計時 HUD
            SpeechBubble      浮動對話氣泡
            _PopupMenu        Toplevel 手刻右鍵選單
            EggGachaScreen    孵蛋互動動畫
            FarewellScreen    放生告別動畫
            ShopView          商店
            BackpackView      背包
            StatsView         統計
            TodoView          待辦清單
            TodoEditDialog    待辦新增 / 編輯
            MusicView         音樂管理
            SettingsView      設定

Controller  PetController     協調所有事件、排程與狀態更新
```

**資料流**：View 觸發事件 → Controller 呼叫 Model → Model `_dirty()` 非同步存檔 → Controller 更新 View。

---

## 存檔格式

執行時自動建立 `data.json`（與 `desktop_pet.py` 同層目錄）：

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

版本升級時以 `_deep_merge()` 載入：既有欄位更新自存檔，動態欄位（`inventory`、`todos`）完整保留，未知欄位自動丟棄，確保向前相容。

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

## 打包 exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name DesktopPet `
    --add-data "assets;assets" `
    desktop_pet.py
```

輸出 `dist/DesktopPet.exe`，執行時需將 `assets/` 資料夾置於 exe 同層目錄。`data.json` 亦寫入同層目錄（非 PyInstaller 的臨時 `_MEIPASS` 目錄）。

---

## 開發環境

- Python 3.12 / Windows 11
- Pillow 10、pygame 2.6、PyInstaller 6

---

## License

[MIT](LICENSE)
