# 🐾 Tkinter Desktop Pet

> 視窗程式設計期末專題 ｜ 彰化師範大學 資訊工程學系

一隻住在你桌面上的小寵物。結合**番茄鐘工作法**、**虛擬貨幣商店**與**心情養成系統**，讓讀書和寫程式多一點陪伴。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## ✨ 功能特色

| 功能 | 說明 |
|------|------|
| 🎨 動畫精靈 | 支援多狀態 PNG 序列動畫（待機、寫程式、讀書、吃東西、拖曳、睡覺） |
| 🍅 番茄鐘計時器 | 可調整工作／休息時長，完成後自動獎勵金幣 |
| 💰 金幣系統 | 透過番茄鐘、每日簽到累積金幣 |
| 🛍️ 寵物商店 | 食物補充心情，道具（藥水、禮盒、加倍符文、蝴蝶結）各有效果 |
| 🎒 背包系統 | 道具加入背包後可隨時使用 |
| ❤️ 心情養成 | 心情每 90 秒自動衰減，需定期照顧 |
| 📅 每日簽到 | 每天簽到領 +5 金幣 |
| ⚙️ 個人化設定 | 寵物名稱、番茄鐘時長、計時器顏色、永遠置頂 |
| 💾 自動存檔 | 所有資料儲存至 `pet_save.json`，重啟後完整保留 |

---

## 📦 安裝與執行

### 必要環境

- Python 3.10 以上
- tkinter（Python 內建）

### 選用依賴

```bash
pip install pillow pygame
```

- **Pillow** — 載入 PNG 動畫精靈；未安裝時顯示預設文字寵物 `(ovo)`
- **pygame** — 讀書模式背景音樂；未安裝時靜音執行

### 執行

```bash
python desktop_pet.py
```

---

## 🗂️ 專案結構

```
tkinter-desktop-pet/
├── desktop_pet.py          # 主程式
├── assets/
│   ├── idle/               # 待機動畫 (0.png, 1.png, ...)
│   ├── coding/             # 寫程式動畫
│   ├── studying/           # 讀書動畫
│   ├── eating/             # 吃東西動畫
│   ├── drag/               # 拖曳動畫
│   ├── sleep/              # 睡覺動畫（可選）
│   └── music/
│       └── study.mp3       # 讀書背景音樂（可選）
└── pet_save.json           # 自動產生的存檔（不含於版本控制）
```

> 動畫資料夾內的 PNG 檔案請以 `0.png`, `1.png`, ... 依序命名，程式會自動載入並循環播放。

---

## 🎮 操作說明

| 操作 | 功能 |
|------|------|
| **左鍵拖曳** | 移動寵物至螢幕任意位置 |
| **右鍵單擊** | 開啟主選單（活動切換、商店、背包、番茄鐘、統計、設定） |

### 商店道具效果

| 道具 | 費用 | 效果 |
|------|------|------|
| 💊 快樂藥水 | 10 金幣 | 心情立即恢復 100% |
| 🎁 神秘禮盒 | 12 金幣 | 開箱獲得 5～30 隨機金幣 |
| ⚡ 加倍符文 | 15 金幣 | 下個番茄鐘金幣獎勵 ×2 |
| 🎀 蝴蝶結 | 20 金幣 | 可愛裝飾品 |

---

## 🏗️ 架構概覽

```
DesktopPet          # 主控制器，負責視窗與事件整合
├── SaveManager     # JSON 存讀，支援深層合併相容舊版存檔
├── AnimationManager# PNG 序列載入與快取
├── MusicPlayer     # pygame daemon 執行緒播放背景音樂
├── PomodoroTimer   # root.after() 驅動的番茄鐘，支援動態調整時長
├── ShopWindow      # 商店介面（ttk.Notebook 分頁 + 每日簽到）
├── BackpackWindow  # 背包介面，顯示與使用已購道具
├── StatsWindow     # 統計面板
└── SettingsWindow  # 設定視窗（名稱、時長、顏色、置頂）
```

---

## 🛠️ 開發環境

- **語言：** Python 3.12
- **GUI 框架：** tkinter / ttk
- **圖像處理：** Pillow 10
- **音效：** pygame 2.6
- **平台：** Windows 11

---

## 📄 授權

本專案以 [MIT License](LICENSE) 釋出，歡迎自由使用與修改。
