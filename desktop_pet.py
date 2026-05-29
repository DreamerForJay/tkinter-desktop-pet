"""
桌面小寵物 (Desktop Pet) — 豪華版
====================================

安裝依賴：
    pip install pillow pygame

自動生成存檔：pet_save.json（儲存金幣、心情、統計、背包、設定）

資料夾結構（可選，無圖片時顯示預設文字）：
    assets/
        idle/ coding/ studying/ eating/ drag/ alert/ sleep/
        music/study.mp3
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import threading
import os
import time
import json
import random
from datetime import date

# ── 選用依賴 ──────────────────────────────────────────────────────
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[提示] 未安裝 Pillow，使用預設文字顯示。安裝：pip install pillow")

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except Exception:
    PYGAME_OK = False
    print("[提示] pygame 未安裝，讀書音樂停用。安裝：pip install pygame")


# ── 全域常數 ──────────────────────────────────────────────────────
ASSET_DIR           = "assets"
SAVE_FILE           = "pet_save.json"
FRAME_MS            = 200
EATING_MS           = 3000
BG_COLOR            = "white"
HP_DECAY_INTERVAL   = 90_000   # ms，每 90 秒心情 -1

# ── 商店商品 ──────────────────────────────────────────────────────
SHOP_FOOD = [
    {"id":"apple",  "name":"蘋果",    "icon":"🍎","cost":2, "hp":15,"desc":"補充心情 +15"},
    {"id":"boba",   "name":"珍珠奶茶","icon":"🧋","cost":3, "hp":20,"desc":"療癒系飲品 +20"},
    {"id":"coffee", "name":"咖啡",    "icon":"☕","cost":4, "hp":25,"desc":"提神醒腦 +25"},
    {"id":"burger", "name":"漢堡",    "icon":"🍔","cost":5, "hp":30,"desc":"飽足又滿足 +30"},
    {"id":"sushi",  "name":"壽司",    "icon":"🍣","cost":6, "hp":35,"desc":"精緻日式料理 +35"},
    {"id":"cake",   "name":"生日蛋糕","icon":"🎂","cost":8, "hp":50,"desc":"大幅提振心情 +50"},
]
SHOP_ITEMS = [
    {"id":"potion", "name":"快樂藥水","icon":"💊","cost":10,"desc":"使用後心情立即恢復 100%"},
    {"id":"giftbox","name":"神秘禮盒","icon":"🎁","cost":12,"desc":"開箱獲得 5~30 隨機金幣"},
    {"id":"rune",   "name":"加倍符文","icon":"⚡","cost":15,"desc":"下個番茄鐘金幣 ×2"},
    {"id":"ribbon", "name":"蝴蝶結",  "icon":"🎀","cost":20,"desc":"可愛裝飾品，增加靈氣"},
]

# ── 預設存檔結構 ──────────────────────────────────────────────────
DEFAULT_DATA: dict = {
    "pet_name":     "小白",
    "coins":        0,
    "happiness":    100,
    "bonus_mult":   1,          # 番茄鐘獎勵倍率（加倍符文激活時為 2）
    "last_checkin": "",
    "inventory":    {},
    "stats": {
        "pomodoro_done": 0,
        "coins_earned":  0,
        "coins_spent":   0,
        "items_used":    0,
    },
    "settings": {
        "work_min":      25,
        "rest_min":      5,
        "show_timer":    True,
        "timer_color":   "#444444",
        "always_on_top": True,
    },
}


# ═══════════════════════════════════════════════════════════════════
# SaveManager — JSON 存讀，支援深層合併以相容舊版存檔
# ═══════════════════════════════════════════════════════════════════
class SaveManager:
    def __init__(self):
        self._d: dict = {}
        self.load()

    def load(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    self._d = self._merge(DEFAULT_DATA, json.load(f))
            except Exception as e:
                print(f"[Warning] 存檔讀取失敗：{e}，使用預設值")
                self._d = json.loads(json.dumps(DEFAULT_DATA))
        else:
            self._d = json.loads(json.dumps(DEFAULT_DATA))

    def save(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Warning] 儲存失敗：{e}")

    def _merge(self, base: dict, saved: dict) -> dict:
        result = json.loads(json.dumps(base))
        for k, v in saved.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge(result[k], v)
            elif k in result:
                result[k] = v
        return result

    def __getitem__(self, k):       return self._d[k]
    def __setitem__(self, k, v):    self._d[k] = v
    def get(self, k, default=None): return self._d.get(k, default)


# ═══════════════════════════════════════════════════════════════════
# AnimationManager — 載入並快取各狀態 PNG 序列
# ═══════════════════════════════════════════════════════════════════
class AnimationManager:
    def __init__(self):
        self._cache: dict[str, list] = {}

    def get_frames(self, state: str) -> list:
        if state in self._cache:
            return self._cache[state]
        frames = []
        folder = os.path.join(ASSET_DIR, state)
        if PIL_OK and os.path.isdir(folder):
            try:
                for name in sorted(f for f in os.listdir(folder) if f.lower().endswith(".png")):
                    try:
                        img = Image.open(os.path.join(folder, name)).convert("RGBA")
                        bg  = Image.new("RGBA", img.size, BG_COLOR)
                        bg.paste(img, mask=img.split()[3])
                        frames.append(ImageTk.PhotoImage(bg.convert("RGB")))
                    except Exception as e:
                        print(f"[Warning] {name}: {e}")
            except Exception as e:
                print(f"[Warning] {folder}: {e}")
        self._cache[state] = frames
        return frames


# ═══════════════════════════════════════════════════════════════════
# MusicPlayer — daemon thread + pygame.mixer，不阻塞主執行緒
# ═══════════════════════════════════════════════════════════════════
class MusicPlayer:
    def __init__(self, path: str):
        self._path    = path
        self._stop    = threading.Event()
        self._playing = False

    def play(self):
        if self._playing or not PYGAME_OK:
            return
        if not os.path.exists(self._path):
            print(f"[提示] 找不到音樂：{self._path}")
            return
        self._stop.clear()
        self._playing = True
        threading.Thread(target=self._worker, daemon=True).start()

    def stop(self):
        if not self._playing:
            return
        self._stop.set()
        self._playing = False
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def _worker(self):
        try:
            pygame.mixer.music.load(self._path)
            pygame.mixer.music.play(-1)
            while not self._stop.is_set():
                time.sleep(0.2)
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"[Warning] 音樂錯誤：{e}")
        finally:
            self._playing = False


# ═══════════════════════════════════════════════════════════════════
# PomodoroTimer — root.after() 驅動，支援動態調整時長
# ═══════════════════════════════════════════════════════════════════
class PomodoroTimer:
    def __init__(self, root, work_min, rest_min, on_work_end, on_rest_end, on_tick):
        self._root      = root
        self._work_s    = work_min * 60
        self._rest_s    = rest_min * 60
        self._remaining = self._work_s
        self._is_rest   = False
        self._running   = False
        self._after_id  = None
        self._cb_work   = on_work_end
        self._cb_rest   = on_rest_end
        self._cb_tick   = on_tick

    def update_durations(self, work_min: int, rest_min: int):
        was = self._running
        self.pause()                        # 暫停但不呼叫 _cb_tick
        self._work_s    = work_min * 60
        self._rest_s    = rest_min * 60
        self._remaining = self._work_s
        self._is_rest   = False
        self._cb_tick(self._remaining, self._is_rest)   # 顯示新時長
        if was:
            self.start()

    def start(self):
        if not self._running:
            self._running = True
            self._tick()

    def pause(self):
        self._running = False
        self._cancel()

    def reset(self):
        self.pause()
        self._remaining = self._work_s
        self._is_rest   = False
        self._cb_tick(self._remaining, self._is_rest)

    @property
    def running(self) -> bool:
        return self._running

    def display_text(self) -> str:
        m, s = divmod(self._remaining, 60)
        return f"🍅 {'休息' if self._is_rest else '工作'} {m:02d}:{s:02d}"

    def _cancel(self):
        if self._after_id:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        if not self._running:
            return
        self._cb_tick(self._remaining, self._is_rest)
        if self._remaining <= 0:
            if not self._is_rest:
                self._is_rest, self._remaining = True, self._rest_s
                self._cb_work()
            else:
                self._is_rest, self._remaining = False, self._work_s
                self._cb_rest()
        else:
            self._remaining -= 1
        self._after_id = self._root.after(1000, self._tick)


# ═══════════════════════════════════════════════════════════════════
# ShopWindow — 豪華商店（ttk.Notebook 分頁 + 每日簽到）
# ═══════════════════════════════════════════════════════════════════
class ShopWindow:
    # 色系
    HDR_BG  = "#fff3e0"
    BAR_BG  = "#fbe9e7"
    BTN_FOOD= "#f4511e"
    BTN_ITEM= "#6a1b9a"
    BTN_OK  = "#2e7d32"
    BTN_DIS = "#b0bec5"

    def __init__(self, master, save: SaveManager, on_food_buy, on_item_buy, on_checkin):
        self._master      = master
        self._sv          = save
        self._on_food_buy = on_food_buy   # callback(item_dict)
        self._on_item_buy = on_item_buy   # callback(item_dict)
        self._on_checkin  = on_checkin    # callback()
        self._win         = None
        self._coin_lbl    = self._hp_lbl = self._checkin_btn = None
        self._item_widgets: dict[str, dict] = {}

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._refresh()
            return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("🛍️ 寵物商店")
        w.resizable(False, False)
        w.grab_set()

        # ── 標題列 ────────────────────────────────────────────────
        hdr = tk.Frame(w, bg=self.HDR_BG, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛍️  寵物商店", font=("Arial", 16, "bold"),
                 bg=self.HDR_BG, fg="#bf360c").pack()
        tk.Label(hdr, text="用金幣讓寵物更開心吧！", font=("Arial", 9),
                 bg=self.HDR_BG, fg="#8d6e63").pack()

        # ── 狀態列 ────────────────────────────────────────────────
        bar = tk.Frame(w, bg=self.BAR_BG, pady=6)
        bar.pack(fill="x")
        self._coin_lbl = tk.Label(bar, font=("Arial", 10, "bold"),
                                  bg=self.BAR_BG, fg="#bf360c")
        self._coin_lbl.pack(side="left", padx=14)
        self._hp_lbl = tk.Label(bar, font=("Arial", 10, "bold"),
                                bg=self.BAR_BG, fg="#c62828")
        self._hp_lbl.pack(side="left")

        # ── 每日簽到 ──────────────────────────────────────────────
        ci_frame = tk.Frame(w, pady=8)
        ci_frame.pack()
        self._checkin_btn = tk.Button(
            ci_frame, font=("Arial", 10, "bold"),
            relief="flat", padx=16, pady=5,
            command=self._do_checkin,
        )
        self._checkin_btn.pack()

        # ── Notebook 分頁 ─────────────────────────────────────────
        style = ttk.Style()
        style.configure("Shop.TNotebook.Tab", padding=[12, 5], font=("Arial", 10))
        nb = ttk.Notebook(w, style="Shop.TNotebook")
        nb.pack(fill="both", expand=True, padx=14, pady=4)

        food_tab = tk.Frame(nb, padx=6, pady=6)
        item_tab = tk.Frame(nb, padx=6, pady=6)
        nb.add(food_tab, text="  🍔 食物  ")
        nb.add(item_tab, text="  🎒 道具  ")

        self._item_widgets = {}
        for item in SHOP_FOOD:
            self._item_widgets[item["id"]] = self._food_row(food_tab, item)
        for item in SHOP_ITEMS:
            self._item_widgets[item["id"]] = self._item_row(item_tab, item)

        # ── 底部關閉 ──────────────────────────────────────────────
        tk.Button(w, text="關閉", width=12, relief="flat",
                  bg="#78909c", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=10)

        self._refresh()

    # ── 卡片列 ──────────────────────────────────────────────────

    def _food_row(self, parent, item: dict) -> dict:
        row = tk.Frame(parent, relief="groove", bd=1, padx=8, pady=6)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=item["icon"], font=("Arial", 22)).pack(side="left")
        info = tk.Frame(row)
        info.pack(side="left", fill="both", expand=True, padx=8)
        tk.Label(info, text=item["name"], font=("Arial", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=item["desc"], font=("Arial", 9), fg="#888", anchor="w").pack(fill="x")
        right = tk.Frame(row)
        right.pack(side="right")
        cost_lbl = tk.Label(right, text=f"💰 {item['cost']}",
                            font=("Arial", 10, "bold"), fg="#e65100")
        cost_lbl.pack()
        btn = tk.Button(right, text="購買", font=("Arial", 9, "bold"), width=5,
                        bg=self.BTN_FOOD, fg="white", relief="flat", pady=3,
                        command=lambda i=item: self._buy_food(i))
        btn.pack(pady=2)
        return {"btn": btn}

    def _item_row(self, parent, item: dict) -> dict:
        row = tk.Frame(parent, relief="groove", bd=1, padx=8, pady=6)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=item["icon"], font=("Arial", 22)).pack(side="left")
        info = tk.Frame(row)
        info.pack(side="left", fill="both", expand=True, padx=8)
        tk.Label(info, text=item["name"], font=("Arial", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=item["desc"], font=("Arial", 9), fg="#888", anchor="w").pack(fill="x")
        right = tk.Frame(row)
        right.pack(side="right")
        cost_lbl = tk.Label(right, text=f"💰 {item['cost']}",
                            font=("Arial", 10, "bold"), fg="#4a148c")
        cost_lbl.pack()
        count_lbl = tk.Label(right, text="背包: 0", font=("Arial", 8), fg="#777")
        count_lbl.pack()
        btn = tk.Button(right, text="購買", font=("Arial", 9, "bold"), width=5,
                        bg=self.BTN_ITEM, fg="white", relief="flat", pady=3,
                        command=lambda i=item: self._buy_item(i))
        btn.pack(pady=2)
        return {"btn": btn, "count_lbl": count_lbl}

    # ── 交易邏輯 ────────────────────────────────────────────────

    def _buy_food(self, item: dict):
        if not self._afford(item["cost"]):
            return
        self._sv["coins"] -= item["cost"]
        self._sv["stats"]["coins_spent"] += item["cost"]
        self._sv.save()
        self._refresh()
        self._on_food_buy(item)
        messagebox.showinfo("購買成功！",
            f"{item['icon']} {item['name']} 餵給寵物了！\n❤️ 心情 +{item['hp']}",
            parent=self._win)

    def _buy_item(self, item: dict):
        if not self._afford(item["cost"]):
            return
        self._sv["coins"] -= item["cost"]
        self._sv["stats"]["coins_spent"] += item["cost"]
        inv = self._sv["inventory"]
        inv[item["id"]] = inv.get(item["id"], 0) + 1
        self._sv.save()
        self._refresh()
        self._on_item_buy(item)
        messagebox.showinfo("加入背包！",
            f"{item['icon']} {item['name']} 已加入背包！\n前往「背包」使用它。",
            parent=self._win)

    def _afford(self, cost: int) -> bool:
        if self._sv["coins"] < cost:
            messagebox.showwarning("金幣不足",
                f"需要 {cost} 金幣，目前只有 {self._sv['coins']} 枚。",
                parent=self._win)
            return False
        return True

    def _do_checkin(self):
        self._on_checkin()
        self._refresh()

    # ── 刷新 UI ─────────────────────────────────────────────────

    def _refresh(self):
        if not (self._win and self._win.winfo_exists()):
            return
        coins = self._sv["coins"]
        hp    = self._sv["happiness"]
        inv   = self._sv["inventory"]

        self._coin_lbl.config(text=f"💰 金幣：{coins} 枚")
        self._hp_lbl.config(  text=f"❤️ 心情：{hp}%")

        today     = str(date.today())
        can_ci    = self._sv["last_checkin"] != today
        self._checkin_btn.config(
            text  = "🎁 每日簽到 (+5 金幣)" if can_ci else "✅ 今日已簽到",
            state = "normal" if can_ci else "disabled",
            bg    = self.BTN_OK if can_ci else self.BTN_DIS,
            fg    = "white",
        )

        for item in SHOP_ITEMS:
            wg = self._item_widgets.get(item["id"])
            if wg and "count_lbl" in wg:
                wg["count_lbl"].config(text=f"背包: {inv.get(item['id'], 0)}")


# ═══════════════════════════════════════════════════════════════════
# BackpackWindow — 使用背包內道具
# ═══════════════════════════════════════════════════════════════════
class BackpackWindow:
    ITEM_MAP = {i["id"]: i for i in SHOP_ITEMS}

    def __init__(self, master, save: SaveManager, on_use):
        self._master = master
        self._sv     = save
        self._on_use = on_use   # callback(item_dict)
        self._win    = None
        self._body   = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._rebuild()
            return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("🎒 我的背包")
        w.resizable(False, False)

        hdr = tk.Frame(w, bg="#e8eaf6", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎒 我的背包", font=("Arial", 14, "bold"),
                 bg="#e8eaf6", fg="#283593").pack()
        tk.Label(hdr, text="道具購買後存放於此，點擊使用", font=("Arial", 9),
                 bg="#e8eaf6", fg="#5c6bc0").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)

        self._body = tk.Frame(w, padx=14)
        self._body.pack(fill="both", expand=True)
        self._rebuild()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        tk.Button(w, text="關閉", width=10, relief="flat",
                  bg="#78909c", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=8)

    def _rebuild(self):
        if not self._body:
            return
        for c in self._body.winfo_children():
            c.destroy()

        inv      = self._sv["inventory"]
        has_item = False

        for item_id, count in inv.items():
            if count <= 0:
                continue
            has_item = True
            item = self.ITEM_MAP.get(item_id, {
                "id": item_id, "name": item_id, "icon": "📦", "desc": "未知道具"
            })
            row = tk.Frame(self._body, relief="groove", bd=1, padx=8, pady=6)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=item["icon"], font=("Arial", 22)).pack(side="left")
            info = tk.Frame(row)
            info.pack(side="left", fill="both", expand=True, padx=8)
            tk.Label(info, text=f"{item['name']}  ×{count}",
                     font=("Arial", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=item["desc"], font=("Arial", 9),
                     fg="#888", anchor="w").pack(fill="x")
            tk.Button(row, text="使用", font=("Arial", 9, "bold"), width=5,
                      bg="#1565c0", fg="white", relief="flat",
                      command=lambda i=item: self._use(i)).pack(side="right")

        if not has_item:
            tk.Label(self._body, text="\n背包空空的，去商店採購吧！\n",
                     font=("Arial", 11), fg="#aaa").pack()

    def _use(self, item: dict):
        inv = self._sv["inventory"]
        if inv.get(item["id"], 0) <= 0:
            messagebox.showinfo("道具不足", "沒有這個道具了！", parent=self._win)
            return
        inv[item["id"]] -= 1
        self._sv["stats"]["items_used"] += 1
        self._sv.save()
        self._rebuild()
        self._on_use(item)


# ═══════════════════════════════════════════════════════════════════
# StatsWindow — 統計面板
# ═══════════════════════════════════════════════════════════════════
class StatsWindow:
    def __init__(self, master, save: SaveManager):
        self._master = master
        self._sv     = save
        self._win    = None
        self._frame  = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            self._refresh()
            return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("📊 統計數據")
        w.resizable(False, False)

        hdr = tk.Frame(w, bg="#e0f2f1", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📊 寵物統計", font=("Arial", 14, "bold"),
                 bg="#e0f2f1", fg="#004d40").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        self._frame = tk.Frame(w, padx=24, pady=4)
        self._frame.pack()
        self._refresh()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        tk.Button(w, text="關閉", width=10, relief="flat",
                  bg="#78909c", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=8)

    def _refresh(self):
        if not self._frame:
            return
        for c in self._frame.winfo_children():
            c.destroy()

        s  = self._sv["stats"]
        hp = self._sv["happiness"]
        hp_color = "#c62828" if hp < 30 else ("#f57f17" if hp < 60 else "#2e7d32")

        rows = [
            ("🐾", "寵物名稱",     self._sv["pet_name"],          "#37474f"),
            ("❤️", "目前心情",     f"{hp}%",                       hp_color),
            ("💰", "目前金幣",     f"{self._sv['coins']} 枚",      "#e65100"),
            ("🍅", "完成番茄鐘",   f"{s['pomodoro_done']} 次",     "#37474f"),
            ("💰", "累計獲得金幣", f"{s['coins_earned']} 枚",      "#37474f"),
            ("🛍️","累計消費金幣",  f"{s['coins_spent']} 枚",       "#37474f"),
            ("🎒", "使用道具次數", f"{s.get('items_used', 0)} 次", "#37474f"),
            ("📅", "上次簽到",     self._sv["last_checkin"] or "—","#37474f"),
        ]
        for i, (icon, label, value, vcolor) in enumerate(rows):
            tk.Label(self._frame, text=icon, font=("Arial", 13),
                     width=3, anchor="e").grid(row=i, column=0, pady=4)
            tk.Label(self._frame, text=label, font=("Arial", 10),
                     fg="#555", anchor="w", width=12).grid(row=i, column=1, sticky="w", padx=4)
            tk.Label(self._frame, text=value, font=("Arial", 10, "bold"),
                     fg=vcolor, anchor="w").grid(row=i, column=2, sticky="w", padx=6)


# ═══════════════════════════════════════════════════════════════════
# SettingsWindow — 寵物設定（名稱、番茄鐘時長、計時器顏色等）
# ═══════════════════════════════════════════════════════════════════
class SettingsWindow:
    def __init__(self, master, save: SaveManager, on_apply):
        self._master   = master
        self._sv       = save
        self._on_apply = on_apply   # callback()
        self._win      = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("⚙️ 設定")
        w.resizable(False, False)
        w.grab_set()

        hdr = tk.Frame(w, bg="#f3e5f5", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙️ 設定", font=("Arial", 14, "bold"),
                 bg="#f3e5f5", fg="#4a148c").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=8)

        g = tk.Frame(w, padx=24)
        g.pack()

        s = self._sv["settings"]
        row = 0

        # 寵物名稱
        tk.Label(g, text="🐾 寵物名稱", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._name = tk.StringVar(value=self._sv["pet_name"])
        tk.Entry(g, textvariable=self._name, width=14, font=("Arial", 10)
                 ).grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # 工作時間
        tk.Label(g, text="🍅 工作時間（分）", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._work = tk.IntVar(value=s["work_min"])
        tk.Spinbox(g, from_=1, to=90, textvariable=self._work,
                   width=6, font=("Arial", 10)
                   ).grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # 休息時間
        tk.Label(g, text="☀️ 休息時間（分）", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._rest = tk.IntVar(value=s["rest_min"])
        tk.Spinbox(g, from_=1, to=30, textvariable=self._rest,
                   width=6, font=("Arial", 10)
                   ).grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # 計時器顏色
        tk.Label(g, text="🎨 計時器顏色", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._color = s["timer_color"]
        self._color_btn = tk.Button(g, text="   ▼ 選色   ", bg=self._color,
                                    font=("Arial", 9), relief="flat",
                                    command=self._pick_color)
        self._color_btn.grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # 顯示計時
        tk.Label(g, text="👁 顯示計時器", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._show_t = tk.BooleanVar(value=s["show_timer"])
        tk.Checkbutton(g, variable=self._show_t
                       ).grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # 永遠置頂
        tk.Label(g, text="📌 永遠置頂", font=("Arial", 10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._topmost = tk.BooleanVar(value=s["always_on_top"])
        tk.Checkbutton(g, variable=self._topmost
                       ).grid(row=row, column=1, sticky="w", padx=10)

        ttk.Separator(w).pack(fill="x", padx=12, pady=10)

        bf = tk.Frame(w)
        bf.pack(pady=6)
        tk.Button(bf, text="✔ 套用", font=("Arial", 10, "bold"), width=8,
                  bg="#2e7d32", fg="white", relief="flat",
                  command=self._apply).pack(side="left", padx=6)
        tk.Button(bf, text="✖ 取消", font=("Arial", 10), width=8,
                  relief="flat", command=w.destroy).pack(side="left", padx=6)

    def _pick_color(self):
        result = colorchooser.askcolor(color=self._color, parent=self._win,
                                       title="選擇計時器顏色")
        if result and result[1]:
            self._color = result[1]
            self._color_btn.config(bg=self._color)

    def _apply(self):
        s = self._sv["settings"]
        self._sv["pet_name"]    = self._name.get().strip() or "小白"
        s["work_min"]           = max(1, self._work.get())
        s["rest_min"]           = max(1, self._rest.get())
        s["timer_color"]        = self._color
        s["show_timer"]         = self._show_t.get()
        s["always_on_top"]      = self._topmost.get()
        self._sv.save()
        self._on_apply()
        self._win.destroy()


# ═══════════════════════════════════════════════════════════════════
# DesktopPet — 主體控制器
# ═══════════════════════════════════════════════════════════════════
class DesktopPet:
    FALLBACK = "(ovo)"

    def __init__(self):
        self._root = tk.Tk()
        self._sv   = SaveManager()

        self._status    = "idle"
        self._pre_drag  = "idle"
        self._dragging  = False
        self._frame_idx = 0

        self._anim_id    = None
        self._eating_id  = None
        self._hp_decay_id = None

        self._anim  = AnimationManager()
        self._music = MusicPlayer(os.path.join(ASSET_DIR, "music", "study.mp3"))

        self._setup_window()
        self._build_ui()
        self._bind_events()

        cfg = self._sv["settings"]
        self._pomo = PomodoroTimer(
            self._root,
            work_min    = cfg["work_min"],
            rest_min    = cfg["rest_min"],
            on_work_end = self._on_work_end,
            on_rest_end = self._on_rest_end,
            on_tick     = self._on_tick,
        )

        self._shop = ShopWindow(
            self._root, self._sv,
            on_food_buy = self._on_food_buy,
            on_item_buy = lambda _: None,   # 加入背包不需立即動作
            on_checkin  = self._daily_checkin,
        )
        self._pack    = BackpackWindow(self._root, self._sv, on_use=self._on_use_item)
        self._stats   = StatsWindow(self._root, self._sv)
        self._cfg_win = SettingsWindow(self._root, self._sv, on_apply=self._apply_settings)

        self._animate()
        self._hp_decay()

    # ════════════════════════════════════════════════════════════════
    # 視窗 & UI
    # ════════════════════════════════════════════════════════════════

    def _setup_window(self):
        r = self._root
        r.overrideredirect(True)
        r.wm_attributes("-topmost", self._sv["settings"]["always_on_top"])
        r.attributes("-transparentcolor", BG_COLOR)
        r.config(bg=BG_COLOR)
        r.geometry("+200+200")

    def _build_ui(self):
        cfg = self._sv["settings"]

        # 計時器標籤（最上方）
        self._timer_lbl = tk.Label(
            self._root, text="", bg=BG_COLOR,
            fg=cfg["timer_color"], font=("Consolas", 9, "bold"),
        )
        self._timer_lbl.pack()

        # 心情 / 金幣快速資訊列
        self._info_lbl = tk.Label(
            self._root, text="", bg=BG_COLOR,
            fg="#666", font=("Arial", 8),
        )
        self._info_lbl.pack()

        # 寵物圖片
        self._img_lbl = tk.Label(self._root, bg=BG_COLOR, bd=0)
        self._img_lbl.pack()

        # 備用文字
        self._txt_lbl = tk.Label(
            self._root, text=self.FALLBACK,
            font=("Courier", 32, "bold"), bg=BG_COLOR, fg="#333",
        )

        self._refresh_info()

    def _refresh_info(self):
        hp    = self._sv["happiness"]
        coins = self._sv["coins"]
        # 4 顆愛心圖示
        filled = hp // 25
        hearts = "♥" * filled + "♡" * (4 - filled)
        color  = "#c62828" if hp < 30 else ("#f57f17" if hp < 60 else "#888")
        self._info_lbl.config(
            text  = f"{hearts}  💰{coins}",
            fg    = color,
        )

    def _bind_events(self):
        for w in (self._root, self._img_lbl, self._txt_lbl, self._info_lbl):
            w.bind("<Button-1>",        self._drag_start)
            w.bind("<B1-Motion>",       self._drag_motion)
            w.bind("<ButtonRelease-1>", self._drag_release)
            w.bind("<Button-3>",        self._right_click)

    # ════════════════════════════════════════════════════════════════
    # 動畫循環
    # ════════════════════════════════════════════════════════════════

    def _animate(self):
        frames = self._anim.get_frames(self._status)
        if frames:
            self._txt_lbl.pack_forget()
            self._img_lbl.pack()
            frame = frames[self._frame_idx % len(frames)]
            self._img_lbl.config(image=frame)
            self._img_lbl.image = frame
            self._frame_idx = (self._frame_idx + 1) % len(frames)
        else:
            self._img_lbl.pack_forget()
            self._txt_lbl.pack()
        self._anim_id = self._root.after(FRAME_MS, self._animate)

    # ════════════════════════════════════════════════════════════════
    # 心情衰減（每 90 秒 -1，吃東西 / 提醒中暫停）
    # ════════════════════════════════════════════════════════════════

    def _hp_decay(self):
        if self._status not in ("eating", "alert"):
            hp = max(0, self._sv["happiness"] - 1)
            self._sv["happiness"] = hp
            self._refresh_info()
            if hp == 0:
                self._sv.save()
        self._hp_decay_id = self._root.after(HP_DECAY_INTERVAL, self._hp_decay)

    # ════════════════════════════════════════════════════════════════
    # 拖曳
    # ════════════════════════════════════════════════════════════════

    def _drag_start(self, event):
        self._ox = event.x_root - self._root.winfo_x()
        self._oy = event.y_root - self._root.winfo_y()
        if not self._dragging:
            self._dragging = True
            self._pre_drag = self._status
            self._change_status("drag")

    def _drag_motion(self, event):
        self._root.geometry(f"+{event.x_root - self._ox}+{event.y_root - self._oy}")

    def _drag_release(self, event):
        if self._dragging:
            self._dragging = False
            self._change_status(self._pre_drag)

    # ════════════════════════════════════════════════════════════════
    # 右鍵選單（豪華版）
    # ════════════════════════════════════════════════════════════════

    def _right_click(self, event):
        sv   = self._sv
        name = sv["pet_name"]
        hp   = sv["happiness"]
        coins= sv["coins"]
        inv  = sv["inventory"]
        bag_count = sum(v for v in inv.values() if v > 0)

        menu = tk.Menu(self._root, tearoff=0)

        # ── 寵物資訊（不可點擊） ──────────────────────────────────
        menu.add_command(label=f"🐾 {name}", state="disabled",
                         font=("Arial", 11, "bold"))
        hp_bar = "♥" * (hp // 25) + "♡" * (4 - hp // 25)
        hp_warn = "  ⚠ 心情過低！" if hp < 30 else ""
        menu.add_command(label=f"  {hp_bar} {hp}%{hp_warn}  💰 {coins} 枚",
                         state="disabled")
        if sv["bonus_mult"] > 1:
            menu.add_command(label="  ⚡ 加倍符文生效中！", state="disabled")
        menu.add_separator()

        # ── 活動切換 ──────────────────────────────────────────────
        act = tk.Menu(menu, tearoff=0)
        act.add_command(label="😴 發呆",   command=self._do_idle)
        act.add_command(label="💻 寫程式", command=self._do_coding)
        act.add_command(label="📚 讀書",   command=self._do_studying)
        act.add_command(label="💤 睡覺",   command=self._do_sleep)
        menu.add_cascade(label="🎮 活動切換", menu=act)
        menu.add_separator()

        # ── 商店 & 背包 ───────────────────────────────────────────
        menu.add_command(label="🛍️  商店", command=self._shop.open)
        bag_label = f"🎒 背包（{bag_count} 件）" if bag_count else "🎒 背包（空）"
        menu.add_command(label=bag_label, command=self._pack.open)
        menu.add_separator()

        # ── 番茄鐘 ────────────────────────────────────────────────
        pomo = tk.Menu(menu, tearoff=0)
        pomo.add_command(
            label="⏸ 暫停" if self._pomo.running else "▶ 開始",
            command=self._toggle_pomo,
        )
        pomo.add_command(label="↺ 重設",        command=self._reset_pomo)
        pomo.add_separator()
        pomo.add_command(label="👁 切換計時顯示", command=self._toggle_timer)
        menu.add_cascade(label="🍅 番茄鐘", menu=pomo)
        menu.add_separator()

        # ── 其他功能 ──────────────────────────────────────────────
        menu.add_command(label="📊 統計",    command=self._stats.open)
        menu.add_command(label="⚙️  設定",    command=self._cfg_win.open)
        menu.add_separator()
        menu.add_command(label="❌ 結束程式", command=self._quit)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    # 狀態切換
    # ════════════════════════════════════════════════════════════════

    def _change_status(self, status: str):
        if self._status != status:
            self._status    = status
            self._frame_idx = 0

    def _do_idle(self):
        self._stop_music()
        self._change_status("idle")

    def _do_coding(self):
        self._stop_music()
        self._change_status("coding")

    def _do_studying(self):
        self._change_status("studying")
        self._music.play()

    def _do_sleep(self):
        self._stop_music()
        # 有 sleep 資產時切換，否則用 idle
        self._change_status("sleep" if self._anim.get_frames("sleep") else "idle")

    def _stop_music(self):
        self._music.stop()

    def _do_eating(self):
        if self._eating_id:
            self._root.after_cancel(self._eating_id)
        self._change_status("eating")
        self._eating_id = self._root.after(
            EATING_MS,
            lambda: self._change_status("idle") if self._status == "eating" else None,
        )

    # ════════════════════════════════════════════════════════════════
    # 番茄鐘
    # ════════════════════════════════════════════════════════════════

    def _toggle_pomo(self):
        self._pomo.pause() if self._pomo.running else self._pomo.start()

    def _reset_pomo(self):
        self._pomo.reset()
        self._timer_lbl.config(text="")

    def _toggle_timer(self):
        cfg = self._sv["settings"]
        cfg["show_timer"] = not cfg["show_timer"]
        if not cfg["show_timer"]:
            self._timer_lbl.config(text="")

    def _on_tick(self, remaining: int, is_rest: bool):
        if self._sv["settings"]["show_timer"]:
            self._timer_lbl.config(
                text = self._pomo.display_text(),
                fg   = self._sv["settings"]["timer_color"],
            )

    def _on_work_end(self):
        mult   = self._sv.get("bonus_mult", 1)
        reward = 10 * mult
        self._sv["coins"]               += reward
        self._sv["stats"]["coins_earned"] += reward
        self._sv["stats"]["pomodoro_done"] += 1
        if mult > 1:
            self._sv["bonus_mult"] = 1   # 符文消耗
        self._sv.save()
        self._change_status("alert")
        self._refresh_info()
        bonus_line = f"⚡ 加倍符文生效 ×{mult}！\n" if mult > 1 else ""
        messagebox.showinfo(
            "🍅 番茄鐘結束！",
            f"主人，番茄鐘結束囉！該休息一下了！\n\n"
            f"{bonus_line}🎉 獲得金幣 +{reward}！（目前：{self._sv['coins']} 枚）",
        )
        self._root.after(3000, lambda: self._change_status("idle"))

    def _on_rest_end(self):
        messagebox.showinfo("☀️ 休息結束！", "主人，休息時間結束了！繼續加油吧！💪")
        self._change_status("idle")

    # ════════════════════════════════════════════════════════════════
    # 商店 / 背包回呼
    # ════════════════════════════════════════════════════════════════

    def _on_food_buy(self, item: dict):
        hp = min(100, self._sv["happiness"] + item["hp"])
        self._sv["happiness"] = hp
        self._sv.save()
        self._refresh_info()
        self._do_eating()

    def _on_use_item(self, item: dict):
        iid = item["id"]
        if iid == "potion":
            self._sv["happiness"] = 100
            self._sv.save()
            self._refresh_info()
            messagebox.showinfo("💊 快樂藥水", f"{self._sv['pet_name']} 心情恢復到 100%！開心極了！")
        elif iid == "giftbox":
            reward = random.randint(5, 30)
            self._sv["coins"] += reward
            self._sv["stats"]["coins_earned"] += reward
            self._sv.save()
            self._refresh_info()
            messagebox.showinfo("🎁 神秘禮盒", f"恭喜！開箱獲得 💰 {reward} 金幣！")
        elif iid == "rune":
            self._sv["bonus_mult"] = 2
            self._sv.save()
            messagebox.showinfo("⚡ 加倍符文", "符文已激活！下個番茄鐘金幣 ×2！加油！")
        elif iid == "ribbon":
            messagebox.showinfo("🎀 蝴蝶結", f"{self._sv['pet_name']} 戴上了可愛的蝴蝶結～真漂亮！")

    # ════════════════════════════════════════════════════════════════
    # 每日簽到
    # ════════════════════════════════════════════════════════════════

    def _daily_checkin(self):
        today = str(date.today())
        if self._sv["last_checkin"] == today:
            return
        self._sv["last_checkin"]         = today
        self._sv["coins"]               += 5
        self._sv["stats"]["coins_earned"] += 5
        self._sv.save()
        self._refresh_info()
        messagebox.showinfo(
            "🎁 每日簽到",
            f"簽到成功！獲得 💰 +5 金幣！\n目前金幣：{self._sv['coins']} 枚",
        )

    # ════════════════════════════════════════════════════════════════
    # 設定套用
    # ════════════════════════════════════════════════════════════════

    def _apply_settings(self):
        cfg = self._sv["settings"]
        self._root.wm_attributes("-topmost", cfg["always_on_top"])
        self._pomo.update_durations(cfg["work_min"], cfg["rest_min"])
        self._timer_lbl.config(fg=cfg["timer_color"])
        if not cfg["show_timer"]:
            self._timer_lbl.config(text="")

    # ════════════════════════════════════════════════════════════════
    # 結束（取消所有 after 再 destroy）
    # ════════════════════════════════════════════════════════════════

    def _quit(self):
        self._stop_music()
        self._pomo.pause()
        for attr in ("_anim_id", "_eating_id", "_hp_decay_id"):
            aid = getattr(self, attr, None)
            if aid:
                self._root.after_cancel(aid)
                setattr(self, attr, None)
        self._sv.save()
        self._root.destroy()

    def run(self):
        self._root.mainloop()


# ── 程式入口 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    pet = DesktopPet()
    pet.run()
