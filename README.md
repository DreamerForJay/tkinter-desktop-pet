# Desktop Pet 🐾

> Python Tkinter 期末專題 ｜ 彰化師範大學 資訊工程學系

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

常駐桌面角落的虛擬寵物，整合**番茄鐘計時器**、**多角色 Gacha 系統**與 **Todoist 風格待辦清單**，讓讀書工作多一份陪伴與動力。

---

## 安裝與執行

**必要環境**：Python 3.10+（`tkinter` 內建）

```bash
pip install pillow pygame       # 選用：圖片動畫 + 背景音樂
python desktop_pet.py
```

| 套件 | 用途 | 缺少時 |
|------|------|--------|
| Pillow | 角色 PNG 動畫 | 顯示文字備用角色 |
| pygame | 背景音樂 | 靜音執行 |

---

## 功能

### 🐾 多角色系統

- **帥潮教授**、**小紫**：預設可用，無需解鎖
- **貓咪 / 兔兔 / 企鵝 / 狐狸 / 小龍**：商店購買角色蛋（30 🪙）孵化解鎖
- 孵蛋互動：7 次點擊破殼，揭曉真實角色圖片
- 放生動畫：角色漸遠走向遠方，可略過
- 匯入自訂角色：右鍵 → 切換角色 → ➕ 匯入素材

### 🍅 番茄鐘

- 工作 → 短休息 → 大休息完整週期，頭頂 HUD 顯示倒計時
- 完成提示音（工作結束：四音上行；休息結束：三音下行）
- 快速預設：經典 25/5、雙倍 50/10、迷你 15/3
- 每顆番茄 +10 🪙，加倍符文可達 ×2

### 📋 待辦清單

- 按到期日分組：逾期 → 今天 → 明天 → 本週 → 之後
- 左側優先度色條（紅 / 橙 / 綠）+ 相對日期顯示
- 個別設定到期前 N 分鐘提醒音效
- 底部快速新增列（Enter 送出）
- 今日任務每 5 分鐘在對話氣泡輪流提醒

### 🎵 音樂管理

右鍵 → 🎵 音樂管理：選播、刪除、匯入（MP3 / OGG / WAV）

### 📊 統計（Forest 風格）

累積專注時間、今日番茄、連續天數、emoji 森林（🌱→🌿→🌳→🌲）

### 🪙 商店

| 類別 | 品項 | 費用 |
|------|------|------|
| 食物 | 蘋果 / 珍奶 / 咖啡 / 漢堡 / 壽司 / 蛋糕 | 2–8 🪙 |
| 道具 | 快樂藥水 / 神秘禮盒 / 加倍符文 / 蝴蝶結 | 10–20 🪙 |
| 角色 | 角色蛋（隨機 Gacha） | 30 🪙 |

---

## 操作

| 動作 | 效果 |
|------|------|
| 左鍵拖曳 | 移動寵物 |
| 右鍵單擊 | 開啟主選單（角色 / 番茄鐘 / 商店 / 音樂 / 待辦 / 統計 / 設定） |

---

## 架構

單一主程式 `desktop_pet.py`（~3,800 LOC），MVC 四層分離：

```
Model      PetModel + _AutoSaver        資料 + 非同步 JSON 存檔
Service    PomodoroTimer / MusicPlayer   業務邏輯（無 tkinter）
           AnimationCache
View       PetView / SpeechBubble       純渲染
           EggGachaScreen / FarewellScreen
           TodoView / MusicView / ShopView ...
Controller PetController                事件協調
```

---

## 素材規格

角色資料夾放在 `assets/{角色名}/`，至少需要 `idle/` 子目錄（PNG 序列）：

```
assets/帥潮教授/
├── idle/        ← 必要
├── coding/
├── studying/
├── eating/
├── drag/
├── alert/
└── sleep/       ← 可選
```

---

## 打包 exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name DesktopPet `
    --add-data "assets;assets" desktop_pet.py
```

---

## License

[MIT](LICENSE)
