"""
桌面小寵物 (Desktop Pet) — 豪華版 v2.0  |  MVC 架構
======================================================

【打包為 exe — PyInstaller 指令】
  Windows PowerShell:
      pyinstaller --onefile --windowed --name DesktopPet `
          --add-data "assets;assets" `
          desktop_pet.py

  macOS / Linux:
      pyinstaller --onefile --windowed --name DesktopPet \
          --add-data "assets:assets" \
          desktop_pet.py

  執行檔位於 dist/DesktopPet.exe
  data.json 儲存在 exe 同層目錄（不放在 _MEIPASS 臨時目錄）

【安裝依賴】
  pip install pillow pygame pyinstaller

【資料夾結構（圖片皆可選，缺少時顯示備用文字）】
  assets/
    idle/ coding/ studying/ eating/ drag/ alert/ sleep/
    music/study.mp3
"""

# ── 標準庫 ────────────────────────────────────────────────────
import sys, os, json, threading, queue, random, time
from datetime import date

# ── GUI ───────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk

# ── 選用依賴：Pillow ──────────────────────────────────────────
try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[提示] pip install pillow  （圖片功能停用）")

# ── 選用依賴：pygame ──────────────────────────────────────────
try:
    import pygame; pygame.mixer.init(); PYGAME_OK = True
except Exception:
    PYGAME_OK = False
    print("[提示] pip install pygame  （音樂功能停用）")


# ════════════════════════════════════════════════════════════════
# 路徑工具（PyInstaller 相容）
# ════════════════════════════════════════════════════════════════

def resource_path(rel: str) -> str:
    """資源路徑：開發用 __file__ 目錄；打包後用 sys._MEIPASS。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def data_file_path() -> str:
    """data.json 永遠放在 exe / .py 同層目錄，不放在 _MEIPASS。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "data.json")


# ════════════════════════════════════════════════════════════════
# 常數 & 商品定義
# ════════════════════════════════════════════════════════════════

FRAME_MS    = 200
EATING_MS   = 3_000
BG          = "white"
HP_DECAY_MS = 90_000     # 每 90 秒心情 -1

_CHECKIN_FIRST_MS    = 120_000   # 工作開始後 2 分鐘第一次關心
_CHECKIN_INTERVAL_MS = 300_000   # 之後每 5 分鐘關心一次
_IDLE_CHAT_MS        = 180_000   # 發呆狀態每 3 分鐘閒聊

DIALOGUES: dict = {
    "work_start": [
        "工作時間開始！\n一起加油！💪",
        "專注模式啟動！✨\n我陪著你喔～",
        "讓我們一起努力！🎯",
        "放鬆心情，專注工作！💡",
    ],
    "work_early": [
        "加油！繼續保持～✨",
        "做得很好！💪",
        "狀態不錯喔，繼續！",
        "感覺你很有效率！",
    ],
    "work_mid": [
        "喝點水，保持水分💧",
        "記得動動手腕喔～",
        "辛苦了！快一半了！",
        "保持專注，你做得到！🌟",
        "需要我唱首歌嗎？🎵",
    ],
    "work_late": [
        "快完成了！再堅持！🎯",
        "最後衝刺！加油💨",
        "快到終點了！棒棒！🎉",
        "勝利就在眼前！⚡",
    ],
    "rest_start": [
        "休息一下！\n伸展一下吧～🙆",
        "辛苦啦！\n喝個水休息💧",
        "好好放鬆，待會出發！☀️",
        "站起來走走吧～👟",
    ],
    "long_rest_start": [
        "一輪結束！\n好好休息一下🌙",
        "太棒了！\n充分放鬆再出發💤",
        "辛苦了！\n享受大休息時光～🌸",
        "這輪你很厲害！zzz💤",
    ],
    "mid_hp": [
        "主人記得關心我喔～",
        "我需要一些點心了…🍪",
        "摸摸我好嗎？🐾",
    ],
    "low_hp": [
        "主人…\n我有點不開心了…😢",
        "可以給我食物嗎？🥺",
        "心情不太好…\n吃點東西吧🍎",
        "需要你的關心～😿",
    ],
    "eating": [
        "好好吃！\n謝謝主人！😋",
        "最愛主人了！❤️",
        "吃飽飽了！\n心情大好！🎵",
        "Yummy！感謝款待！",
    ],
    "idle": [
        "今天也要加油喔！✨",
        "我在這裡陪著你喔～",
        "有什麼需要我幫忙嗎？",
        "一起加油吧！💪",
        "我是你的小夥伴！🐾",
        "需要開始工作了嗎？\n我準備好了！🍅",
        "發呆的時候就找我聊聊～",
        "今天有什麼計畫呀？📝",
    ],
}

SHOP_FOOD = [
    {"id":"apple",  "name":"蘋果",    "icon":"🍎","cost":2, "hp":15,"desc":"心情 +15"},
    {"id":"boba",   "name":"珍珠奶茶","icon":"🧋","cost":3, "hp":20,"desc":"心情 +20"},
    {"id":"coffee", "name":"咖啡",    "icon":"☕","cost":4, "hp":25,"desc":"心情 +25"},
    {"id":"burger", "name":"漢堡",    "icon":"🍔","cost":5, "hp":30,"desc":"心情 +30"},
    {"id":"sushi",  "name":"壽司",    "icon":"🍣","cost":6, "hp":35,"desc":"心情 +35"},
    {"id":"cake",   "name":"生日蛋糕","icon":"🎂","cost":8, "hp":50,"desc":"心情 +50"},
]
SHOP_ITEMS = [
    {"id":"potion", "name":"快樂藥水","icon":"💊","cost":10,"desc":"心情立即 100%"},
    {"id":"giftbox","name":"神秘禮盒","icon":"🎁","cost":12,"desc":"隨機 5~30 金幣"},
    {"id":"rune",   "name":"加倍符文","icon":"⚡","cost":15,"desc":"下個番茄鐘 ×2"},
    {"id":"ribbon", "name":"蝴蝶結",  "icon":"🎀","cost":20,"desc":"可愛裝飾品"},
]
FOOD_IDS  = frozenset(i["id"] for i in SHOP_FOOD)
FOOD_MAP  = {i["id"]: i for i in SHOP_FOOD}
ITEM_MAP  = {i["id"]: i for i in SHOP_ITEMS}
ALL_ITEMS = {**FOOD_MAP, **ITEM_MAP}

DEFAULT_DATA: dict = {
    "pet_name":     "小白",
    "coins":        0,
    "happiness":    100,
    "bonus_mult":   1,
    "last_checkin": "",
    "inventory":    {},
    "stats": {"pomodoro_done":0,"coins_earned":0,"coins_spent":0,"items_used":0},
    "settings": {
        "work_min":25,"rest_min":5,"long_rest_min":15,
        "sessions_before_long":4,"auto_start":False,
        "always_on_top":True,
        "character":"default",
    },
}


# ════════════════════════════════════════════════════════════════
# 工具函式
# ════════════════════════════════════════════════════════════════

def _deep_merge(base: dict, saved: dict) -> dict:
    result = json.loads(json.dumps(base))
    for k, v in saved.items():
        if k not in result:
            continue
        if isinstance(result[k], dict) and isinstance(v, dict):
            # Empty base dict = dynamic map (e.g. inventory); preserve all saved entries.
            # Non-empty base dict = fixed schema; only keep keys defined in base.
            result[k] = _deep_merge(result[k], v) if result[k] else json.loads(json.dumps(v))
        else:
            result[k] = v
    return result


# ════════════════════════════════════════════════════════════════
# LAYER 1 — MODEL（純資料，無任何 tkinter）
# ════════════════════════════════════════════════════════════════

class _AutoSaver:
    """背景 daemon 執行緒，非同步寫入 JSON，防止 GUI 卡頓。"""

    def __init__(self, path: str):
        self._path = path
        self._q    = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def schedule(self, payload: str):
        # 只保留最新一筆，丟掉積壓
        while not self._q.empty():
            try: self._q.get_nowait()
            except queue.Empty: break
        self._q.put(payload)

    def _run(self):
        while True:
            data = self._q.get()
            try:
                with open(self._path, "w", encoding="utf-8") as f:
                    f.write(data)
            except Exception as e:
                print(f"[AutoSave Error] {e}")


class PetModel:
    """
    資料層（Model）。
    每次屬性變動後立即觸發非同步自動儲存，不需手動呼叫 save()。
    完全不含 tkinter 程式碼。
    """

    def __init__(self):
        self._saver = _AutoSaver(data_file_path())
        self._d: dict = {}
        self._load()

    def _load(self):
        p = data_file_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self._d = _deep_merge(DEFAULT_DATA, json.load(f))
                return
            except Exception as e:
                print(f"[Model] 載入失敗：{e}")
        self._d = json.loads(json.dumps(DEFAULT_DATA))

    def _dirty(self):
        self._saver.schedule(json.dumps(self._d, ensure_ascii=False, indent=2))

    # ── 屬性存取器 ───────────────────────────────────────────

    @property
    def pet_name(self)     -> str:  return self._d["pet_name"]
    @property
    def coins(self)        -> int:  return self._d["coins"]
    @property
    def happiness(self)    -> int:  return self._d["happiness"]
    @property
    def bonus_mult(self)   -> int:  return self._d.get("bonus_mult", 1)
    @property
    def last_checkin(self) -> str:  return self._d["last_checkin"]
    @property
    def inventory(self)    -> dict: return self._d["inventory"]
    @property
    def stats(self)        -> dict: return self._d["stats"]
    @property
    def settings(self)     -> dict: return self._d["settings"]

    @pet_name.setter
    def pet_name(self, v: str):
        self._d["pet_name"] = v or "小白"; self._dirty()

    @coins.setter
    def coins(self, v: int):
        self._d["coins"] = max(0, int(v)); self._dirty()

    @happiness.setter
    def happiness(self, v: int):
        self._d["happiness"] = max(0, min(100, int(v))); self._dirty()

    @bonus_mult.setter
    def bonus_mult(self, v: int):
        self._d["bonus_mult"] = max(1, int(v)); self._dirty()

    @last_checkin.setter
    def last_checkin(self, v: str):
        self._d["last_checkin"] = v; self._dirty()

    def add_inv(self, item_id: str, qty: int = 1):
        inv = self._d["inventory"]
        inv[item_id] = inv.get(item_id, 0) + qty
        self._dirty()

    def remove_inv(self, item_id: str, qty: int = 1) -> bool:
        inv = self._d["inventory"]
        if inv.get(item_id, 0) < qty:
            return False
        inv[item_id] -= qty
        if inv[item_id] == 0:
            del inv[item_id]
        self._dirty()
        return True

    def inc_stat(self, key: str, val: int = 1):
        self._d["stats"][key] = self._d["stats"].get(key, 0) + val
        self._dirty()

    def patch_settings(self, **kw):
        self._d["settings"].update(kw)
        self._dirty()

    def sync_save(self):
        try:
            with open(data_file_path(), "w", encoding="utf-8") as f:
                json.dump(self._d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Model] 同步儲存失敗：{e}")


# ════════════════════════════════════════════════════════════════
# LAYER 2 — SERVICES（不含 tkinter，可單獨測試）
# ════════════════════════════════════════════════════════════════

class AnimationCache:
    """載入並快取各狀態 PNG 序列，支援多角色子目錄。"""

    def __init__(self):
        self._cache: dict[str, list] = {}

    def get(self, state: str, character: str = "default") -> list:
        key = f"{character}/{state}"
        if key in self._cache:
            return self._cache[key]
        if character == "default":
            folder = resource_path(os.path.join("assets", state))
        else:
            folder = resource_path(os.path.join("assets", character, state))
        frames = []
        if PIL_OK and os.path.isdir(folder):
            try:
                for name in sorted(f for f in os.listdir(folder) if f.lower().endswith(".png")):
                    try:
                        img = Image.open(os.path.join(folder, name)).convert("RGBA")
                        bg  = Image.new("RGBA", img.size, BG)
                        bg.paste(img, mask=img.split()[3])
                        frames.append(ImageTk.PhotoImage(bg.convert("RGB")))
                    except Exception as e:
                        print(f"[Anim] {name}: {e}")
            except Exception as e:
                print(f"[Anim] {folder}: {e}")
        self._cache[key] = frames
        return frames


class MusicPlayer:
    """pygame 音樂播放器，支援淡入（啟動）／淡出（停止）。"""

    FADE = 2.0   # 淡入 / 淡出秒數

    def __init__(self):
        self._path    = resource_path(os.path.join("assets", "music", "study.mp3"))
        self._playing = False
        self._cancel  = threading.Event()

    def play(self):
        if not PYGAME_OK: return
        if not os.path.exists(self._path):
            print(f"[Music] 找不到：{self._path}"); return
        if not self._playing:
            try:
                pygame.mixer.music.load(self._path)
                pygame.mixer.music.set_volume(0.0)
                pygame.mixer.music.play(-1)
                self._playing = True
            except Exception as e:
                print(f"[Music] {e}"); return
        self._fade(1.0)

    def stop(self):
        if not self._playing: return
        self._fade(0.0, on_done=self._hard_stop)

    # ── 私有 ────────────────────────────────────────────────────

    def _hard_stop(self):
        self._playing = False
        try: pygame.mixer.music.stop()
        except Exception: pass

    def _fade(self, target: float, on_done=None):
        """在背景執行緒平滑調整音量至 target（0.0–1.0）。"""
        self._cancel.set()
        ev = self._cancel = threading.Event()

        def _run():
            try:
                start = pygame.mixer.music.get_volume()
            except Exception:
                return
            steps = max(1, int(self.FADE * 30))
            for i in range(1, steps + 1):
                if ev.is_set(): return
                vol = start + (target - start) * i / steps
                try:
                    pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
                except Exception:
                    return
                time.sleep(self.FADE / steps)
            if not ev.is_set() and on_done:
                on_done()

        threading.Thread(target=_run, daemon=True).start()


class PomodoroTimer:
    """root.after() 驅動的番茄鐘，支援長休息、節次追蹤、自動開始。"""

    def __init__(self, root, work_min, rest_min, long_rest_min,
                 sessions_before_long, auto_start,
                 on_tick, on_work_end, on_short_rest_end, on_long_rest_end):
        self._root             = root
        self._work_s           = work_min * 60
        self._rest_s           = rest_min * 60
        self._long_rest_s      = long_rest_min * 60
        self._sessions_n       = sessions_before_long
        self._auto_start       = auto_start
        self._running          = False
        self._after_id         = None

        self._phase            = "work"      # "work" | "rest" | "long_rest"
        self._remain           = self._work_s
        self._total            = self._work_s
        self._session_done     = 0           # 本輪已完成工作節數

        self.on_tick           = on_tick     # (m, s, phase, session_done, sessions_n, total_s)
        self.on_work_end       = on_work_end
        self.on_short_rest_end = on_short_rest_end
        self.on_long_rest_end  = on_long_rest_end

    @property
    def running(self)      -> bool: return self._running
    @property
    def phase(self)        -> str:  return self._phase
    @property
    def session_done(self) -> int:  return self._session_done
    @property
    def sessions_n(self)   -> int:  return self._sessions_n
    @property
    def auto_start(self)   -> bool: return self._auto_start

    def start(self):
        if not self._running:
            self._running = True; self._tick()

    def pause(self):
        self._running = False
        if self._after_id:
            self._root.after_cancel(self._after_id); self._after_id = None

    def reset(self):
        self.pause()
        self._phase        = "work"
        self._remain       = self._work_s
        self._total        = self._work_s
        self._session_done = 0
        self._fire_tick()

    def update_config(self, work_min: int, rest_min: int, long_rest_min: int,
                      sessions_before_long: int, auto_start: bool):
        was = self._running
        self.pause()
        self._work_s      = work_min * 60
        self._rest_s      = rest_min * 60
        self._long_rest_s = long_rest_min * 60
        self._sessions_n  = sessions_before_long
        self._auto_start  = auto_start
        self._phase       = "work"
        self._remain      = self._total = self._work_s
        self._session_done = 0
        self._fire_tick()
        if was: self.start()

    def _fire_tick(self):
        m, s = divmod(self._remain, 60)
        self.on_tick(m, s, self._phase,
                     self._session_done, self._sessions_n, self._total)

    def _tick(self):
        if not self._running: return
        try:
            if not self._root.winfo_exists():
                self._running = False; return
        except Exception:
            self._running = False; return

        self._fire_tick()

        if self._remain <= 0:
            self._advance(); return

        self._remain -= 1
        self._after_id = self._root.after(1000, self._tick)

    def _advance(self):
        if self._phase == "work":
            self._session_done += 1
            if self._session_done >= self._sessions_n:
                self._phase        = "long_rest"
                self._remain       = self._long_rest_s
                self._total        = self._long_rest_s
                self._session_done = 0
            else:
                self._phase  = "rest"
                self._remain = self._rest_s
                self._total  = self._rest_s
            self.on_work_end()
        elif self._phase == "rest":
            self._phase  = "work"
            self._remain = self._work_s
            self._total  = self._work_s
            self.on_short_rest_end()
        else:
            self._phase  = "work"
            self._remain = self._work_s
            self._total  = self._work_s
            self.on_long_rest_end()

        if self._auto_start:
            self._after_id = self._root.after(1000, self._tick)
        else:
            self._running = False
            self._fire_tick()


# ════════════════════════════════════════════════════════════════
# LAYER 3 — VIEW（純渲染，透過 Controller 回呼處理邏輯）
# ════════════════════════════════════════════════════════════════

# ── 頭頂計時框 ───────────────────────────────────────────────

class TimerBubble:
    """
    番茄鐘計時框（緊湊圓角）。
    Canvas bg=BG（透明角落）+ 彩色圓角多邊形，
    文字用 #FEFEFE（視覺白色，不觸發 -transparentcolor）。
    工作：深紅  休息：深綠  長休息：深藍
    """
    _CLR = {"work": "#B03A2E", "rest": "#1E8449", "long_rest": "#1A5276"}
    _TRK = {"work": "#7B241C", "rest": "#145A32", "long_rest": "#0E3460"}
    _SUB = {"work": "#F1948A", "rest": "#82E0AA", "long_rest": "#85C1E9"}
    _W, _H, _R = 112, 74, 11

    def __init__(self, parent: tk.Tk):
        w, h, r = self._W, self._H, self._R
        self._pb_x1, self._pb_x2 = 8, w - 8

        self._canvas = tk.Canvas(
            parent, width=w, height=h,
            bg=BG, bd=0, highlightthickness=0,
        )
        self._canvas.grid(row=0, column=0, pady=(0, 4))
        self._canvas.grid_remove()

        self._rect = self._canvas.create_polygon(
            *self._rrect(2, 2, w - 2, h - 2, r),
            smooth=True, fill=self._CLR["work"], outline="",
        )
        self._sess_item = self._canvas.create_text(
            w // 2, 13, text="第 1 / 4 節",
            font=("Arial", 8), fill=self._SUB["work"],
        )
        self._mode_item = self._canvas.create_text(
            w // 2, 27, text="工作",
            font=("Arial", 9, "bold"), fill="#FEFEFE",
        )
        self._time_item = self._canvas.create_text(
            w // 2, 48, text="25:00",
            font=("Consolas", 17, "bold"), fill="#FEFEFE",
        )
        self._pb_bg = self._canvas.create_rectangle(
            self._pb_x1, 62, self._pb_x2, 68,
            fill=self._TRK["work"], outline="",
        )
        self._pb_fg = self._canvas.create_rectangle(
            self._pb_x1, 62, self._pb_x1, 68,
            fill="#FEFEFE", outline="",
        )

    @staticmethod
    def _rrect(x1, y1, x2, y2, r):
        return (
            x1+r, y1,   x2-r, y1,
            x2,   y1,   x2,   y1+r,
            x2,   y2-r, x2,   y2,
            x2-r, y2,   x1+r, y2,
            x1,   y2,   x1,   y2-r,
            x1,   y1+r, x1,   y1,
        )

    def update(self, minutes: int, seconds: int, phase: str,
               session_done: int, sessions_n: int, total_s: int):
        clr   = self._CLR.get(phase, self._CLR["work"])
        track = self._TRK.get(phase, self._TRK["work"])
        sub_c = self._SUB.get(phase, self._SUB["work"])

        if phase == "work":
            mode = "工作"
            sess = f"第 {session_done + 1} / {sessions_n} 節"
        elif phase == "rest":
            mode = "短暫休息"
            sess = "喝口水、動一動"
        else:
            mode = "大休息"
            sess = "充分放鬆再出發"

        remain_s = minutes * 60 + seconds
        progress = max(0.0, min(1.0, 1.0 - remain_s / max(1, total_s)))
        pb_w = int((self._pb_x2 - self._pb_x1) * progress)

        self._canvas.itemconfig(self._rect,      fill=clr)
        self._canvas.itemconfig(self._pb_bg,     fill=track)
        self._canvas.itemconfig(self._sess_item, text=sess, fill=sub_c)
        self._canvas.itemconfig(self._mode_item, text=mode)
        self._canvas.itemconfig(self._time_item, text=f"{minutes:02d}:{seconds:02d}")
        self._canvas.coords(self._pb_fg,
            self._pb_x1, 62, self._pb_x1 + pb_w, 68)

    def set_visible(self, v: bool):
        if v: self._canvas.grid()
        else: self._canvas.grid_remove()


# ── 角色對話氣泡 ──────────────────────────────────────────

class SpeechBubble:
    """角色對話氣泡，以獨立 Toplevel 浮動顯示在寵物上方。"""
    _W    = 158
    _BH   = 68
    _TH   = 10
    _H    = 78
    _R    = 12
    _BODY = "#FFFDE7"
    _BORD = "#F9A825"
    _FG   = "#4A3728"

    def __init__(self, parent: tk.Tk):
        self._parent    = parent
        self._after_id  = None
        self._win       = None
        self._canvas    = None
        self._text_item = None

    def show(self, text: str, duration_ms: int = 4000):
        if self._after_id:
            try: self._parent.after_cancel(self._after_id)
            except Exception: pass
        self._ensure_win()
        self._canvas.itemconfig(self._text_item, text=text)
        self._reposition()
        try:
            self._win.deiconify()
            self._win.lift()
        except Exception:
            pass
        self._after_id = self._parent.after(duration_ms, self._hide)

    def reposition(self):
        """跟隨主視窗重新定位（拖曳時呼叫）。"""
        if self._after_id and self._win and self._win.winfo_exists():
            self._reposition()

    def cancel(self):
        if self._after_id:
            try: self._parent.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None
        self._hide()

    def _hide(self):
        self._after_id = None
        if self._win:
            try: self._win.withdraw()
            except Exception: pass

    def _ensure_win(self):
        if self._win and self._win.winfo_exists():
            return
        w, h, bh, r = self._W, self._H, self._BH, self._R
        cx = w // 2

        win = self._win = tk.Toplevel(self._parent)
        win.overrideredirect(True)
        win.wm_attributes("-topmost", True)
        win.attributes("-transparentcolor", BG)
        win.config(bg=BG)
        win.withdraw()

        cvs = self._canvas = tk.Canvas(
            win, width=w, height=h,
            bg=BG, bd=0, highlightthickness=0,
        )
        cvs.pack()

        # 三角尾巴（先畫，讓氣泡本體蓋住頂端邊界）
        cvs.create_polygon(
            cx - 8, bh, cx + 8, bh, cx, h - 1,
            fill=self._BODY, outline="",
        )
        # 圓角氣泡本體（後畫，蓋住尾巴頂端）
        cvs.create_polygon(
            *self._rrect(2, 2, w - 2, bh, r),
            smooth=True, fill=self._BODY, outline=self._BORD, width=2,
        )
        self._text_item = cvs.create_text(
            w // 2, bh // 2,
            text="",
            font=("Segoe UI", 9),
            fill=self._FG,
            width=w - 22,
            justify="center",
        )

    def _reposition(self):
        try:
            px = self._parent.winfo_x()
            py = self._parent.winfo_y()
            pw = self._parent.winfo_width()
        except Exception:
            return
        x = px + pw // 2 - self._W // 2
        y = py - self._H - 6
        try:
            self._win.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    @staticmethod
    def _rrect(x1, y1, x2, y2, r):
        return (
            x1 + r, y1,     x2 - r, y1,
            x2,     y1,     x2,     y1 + r,
            x2,     y2 - r, x2,     y2,
            x2 - r, y2,     x1 + r, y2,
            x1,     y2,     x1,     y2 - r,
            x1,     y1 + r, x1,     y1,
        )


# ── 商店卡片（帶 hover 特效）────────────────────────────────

class _ItemCard(tk.Frame):
    NORMAL = "#FFFFFF"
    HOVER  = "#EFF6FF"

    def __init__(self, parent, item: dict, on_buy, is_food: bool):
        super().__init__(parent, bg=self.NORMAL, relief="solid", bd=1, cursor="hand2")

        tk.Label(self, text=item["icon"], font=("Arial", 22), bg=self.NORMAL).pack(pady=(10, 2))
        tk.Label(self, text=item["name"], font=("Arial", 10, "bold"), bg=self.NORMAL).pack()
        tk.Label(self, text=item["desc"], font=("Arial", 8), fg="#888", bg=self.NORMAL).pack()

        if not is_food:
            self._cnt_lbl = tk.Label(self, text="背包: 0", font=("Arial", 8),
                                     fg="#555", bg=self.NORMAL)
            self._cnt_lbl.pack()

        btm = tk.Frame(self, bg=self.NORMAL)
        btm.pack(fill="x", padx=10, pady=(6, 10))
        tk.Label(btm, text=f"💰 {item['cost']}", font=("Arial", 10, "bold"),
                 fg="#E65100", bg=self.NORMAL).pack(side="left")
        clr = "#E53935" if is_food else "#7B1FA2"
        tk.Button(btm, text="購買", font=("Arial", 9, "bold"), width=4,
                  bg=clr, fg="white", relief="flat", cursor="hand2",
                  command=on_buy).pack(side="right")

        self._bind_hover(self)

    def _bind_hover(self, w: tk.Widget):
        if not isinstance(w, tk.Button):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
        for child in w.winfo_children():
            self._bind_hover(child)

    def _on_enter(self, _):
        self._set_bg(self, self.HOVER)

    def _on_leave(self, event):
        # 滑鼠移至子元件時 Leave 也會觸發，需判斷是否仍在卡片內
        rx, ry = self.winfo_rootx(), self.winfo_rooty()
        rw, rh = self.winfo_width(), self.winfo_height()
        if rx <= event.x_root <= rx + rw and ry <= event.y_root <= ry + rh:
            return   # 仍在卡片內
        self._set_bg(self, self.NORMAL)

    def _set_bg(self, w: tk.Widget, color: str):
        if isinstance(w, tk.Button): return
        try: w.config(bg=color)
        except Exception: pass
        for child in w.winfo_children():
            self._set_bg(child, color)

    def update_count(self, count: int):
        if hasattr(self, "_cnt_lbl"):
            self._cnt_lbl.config(text=f"背包: {count}")


# ── 商店視窗 ─────────────────────────────────────────────────

class ShopView:
    WIN_BG = "#F8F9FA"
    HDR_BG = "#FF5722"
    BAR_BG = "#FFF3E0"

    def __init__(self, master, ctrl):
        self._master = master
        self._ctrl   = ctrl
        self._win    = None
        self._cards: dict[str, _ItemCard] = {}
        self._coin_lbl = self._hp_lbl = self._ci_btn = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._refresh(); return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("🛍️ 寵物商店")
        w.config(bg=self.WIN_BG)
        w.resizable(False, False)

        # 標題
        hdr = tk.Frame(w, bg=self.HDR_BG, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛍️  寵物商店", font=("Arial", 16, "bold"),
                 bg=self.HDR_BG, fg="white").pack()
        tk.Label(hdr, text="購買後存入背包，隨時餵食！",
                 font=("Arial", 9), bg=self.HDR_BG, fg="#FFCCBC").pack()

        # 狀態列
        bar = tk.Frame(w, bg=self.BAR_BG, pady=7)
        bar.pack(fill="x")
        self._coin_lbl = tk.Label(bar, font=("Arial", 11, "bold"),
                                   bg=self.BAR_BG, fg="#BF360C")
        self._coin_lbl.pack(side="left", padx=16)
        self._hp_lbl = tk.Label(bar, font=("Arial", 11, "bold"),
                                 bg=self.BAR_BG, fg="#B71C1C")
        self._hp_lbl.pack(side="left")

        # 每日簽到
        ci_f = tk.Frame(w, bg=self.WIN_BG, pady=8)
        ci_f.pack()
        self._ci_btn = tk.Button(ci_f, font=("Arial", 10, "bold"),
                                  relief="flat", padx=18, pady=6, cursor="hand2",
                                  command=self._do_checkin)
        self._ci_btn.pack()

        # Notebook 分頁
        style = ttk.Style()
        style.configure("Shop.TNotebook.Tab", padding=[14, 6], font=("Arial", 10))
        nb = ttk.Notebook(w, style="Shop.TNotebook")
        nb.pack(padx=16, pady=8, fill="both", expand=True)

        food_f = tk.Frame(nb, bg=self.WIN_BG, padx=10, pady=10)
        item_f = tk.Frame(nb, bg=self.WIN_BG, padx=10, pady=10)
        nb.add(food_f, text="  🍔 食物  ")
        nb.add(item_f, text="  🎒 道具  ")

        self._cards = {}

        # 食物：3 欄網格
        for col in range(3):
            food_f.columnconfigure(col, weight=1)
        for idx, item in enumerate(SHOP_FOOD):
            r, c = divmod(idx, 3)
            card = _ItemCard(food_f, item,
                             on_buy=lambda i=item: self._buy(i),
                             is_food=True)
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            self._cards[item["id"]] = card

        # 道具：2 欄網格
        for col in range(2):
            item_f.columnconfigure(col, weight=1)
        for idx, item in enumerate(SHOP_ITEMS):
            r, c = divmod(idx, 2)
            card = _ItemCard(item_f, item,
                             on_buy=lambda i=item: self._buy(i),
                             is_food=False)
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            self._cards[item["id"]] = card

        # 關閉
        tk.Button(w, text="關閉", width=12, relief="flat",
                  bg="#607D8B", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=10)

        self._refresh()

    def _buy(self, item: dict):
        ok = self._ctrl.buy_item(item)
        if ok:
            self._refresh()
            _info_dialog(self._win, "加入背包！",
                         f"{item['icon']} {item['name']} 已放入背包！\n右鍵選單 → 餵食 隨時使用。")

    def _do_checkin(self):
        self._ctrl.daily_checkin()
        self._refresh()

    def _refresh(self):
        if not (self._win and self._win.winfo_exists()): return
        m = self._ctrl.model
        self._coin_lbl.config(text=f"💰 金幣：{m.coins} 枚")
        self._hp_lbl.config(  text=f"❤️ 心情：{m.happiness}%")
        today  = str(date.today())
        can_ci = m.last_checkin != today
        self._ci_btn.config(
            text  = "🎁 每日簽到 (+5 金幣)" if can_ci else "✅ 今日已簽到",
            state = "normal" if can_ci else "disabled",
            bg    = "#43A047" if can_ci else "#B0BEC5", fg="white",
        )
        inv = m.inventory
        for iid, card in self._cards.items():
            card.update_count(inv.get(iid, 0))


# ── 背包視窗 ─────────────────────────────────────────────────

class BackpackView:
    def __init__(self, master, ctrl):
        self._master = master
        self._ctrl   = ctrl
        self._win    = None
        self._body   = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._rebuild(); return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("🎒 我的背包")
        w.resizable(False, False)

        hdr = tk.Frame(w, bg="#E8EAF6", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎒 我的背包", font=("Arial", 14, "bold"),
                 bg="#E8EAF6", fg="#283593").pack()
        tk.Label(hdr, text="點擊使用食物或道具",
                 font=("Arial", 9), bg="#E8EAF6", fg="#5C6BC0").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        self._body = tk.Frame(w, padx=14, pady=4)
        self._body.pack(fill="both", expand=True)
        self._rebuild()

        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        tk.Button(w, text="關閉", width=10, relief="flat",
                  bg="#78909C", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=8)

    def _rebuild(self):
        if not self._body: return
        for c in self._body.winfo_children(): c.destroy()

        inv      = self._ctrl.model.inventory
        has_item = False
        for iid, count in inv.items():
            if count <= 0: continue
            has_item = True
            item = ALL_ITEMS.get(iid, {"id":iid,"name":iid,"icon":"📦","desc":""})
            row  = tk.Frame(self._body, relief="groove", bd=1, padx=8, pady=6)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=item["icon"], font=("Arial", 20)).pack(side="left")
            info = tk.Frame(row); info.pack(side="left", fill="both", expand=True, padx=8)
            tk.Label(info, text=f"{item['name']}  ×{count}",
                     font=("Arial", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=item.get("desc",""), font=("Arial", 9),
                     fg="#888", anchor="w").pack(fill="x")

            def _use(i=iid):
                self._ctrl.use_item(i); self._rebuild()

            tk.Button(row, text="使用", font=("Arial", 9), width=5,
                      bg="#1565C0", fg="white", relief="flat",
                      command=_use).pack(side="right")

        if not has_item:
            tk.Label(self._body, text="\n背包是空的～去商店買些道具吧！\n",
                     font=("Arial", 11), fg="#aaa").pack()


# ── 統計視窗 ─────────────────────────────────────────────────

class StatsView:
    def __init__(self, master, ctrl):
        self._master = master
        self._ctrl   = ctrl
        self._win    = None
        self._frame  = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._refresh(); return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("📊 統計數據"); w.resizable(False, False)
        hdr = tk.Frame(w, bg="#E0F2F1", pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="📊 寵物統計", font=("Arial", 14, "bold"),
                 bg="#E0F2F1", fg="#004D40").pack()
        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        self._frame = tk.Frame(w, padx=24, pady=4); self._frame.pack()
        self._refresh()
        ttk.Separator(w).pack(fill="x", padx=12, pady=6)
        tk.Button(w, text="關閉", width=10, relief="flat",
                  bg="#78909C", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(pady=8)

    def _refresh(self):
        if not self._frame: return
        for c in self._frame.winfo_children(): c.destroy()
        m  = self._ctrl.model
        s  = m.stats
        hp = m.happiness
        hpc = "#C62828" if hp < 30 else ("#F57F17" if hp < 60 else "#2E7D32")
        rows = [
            ("🐾","寵物名稱",  m.pet_name,              "#37474F"),
            ("❤️","目前心情",  f"{hp}%",                hpc),
            ("💰","目前金幣",  f"{m.coins} 枚",         "#E65100"),
            ("🍅","完成番茄鐘",f"{s['pomodoro_done']} 次","#37474F"),
            ("💰","累計獲得",  f"{s['coins_earned']} 枚","#37474F"),
            ("🛍️","累計消費", f"{s['coins_spent']} 枚", "#37474F"),
            ("🎒","使用道具",  f"{s.get('items_used',0)} 次","#37474F"),
            ("📅","上次簽到",  m.last_checkin or "—",   "#37474F"),
        ]
        for i, (icon, lbl, val, vc) in enumerate(rows):
            tk.Label(self._frame, text=icon, font=("Arial",12),
                     width=3, anchor="e").grid(row=i, column=0, pady=4)
            tk.Label(self._frame, text=lbl, font=("Arial",10),
                     fg="#555", anchor="w", width=12).grid(row=i, column=1, sticky="w", padx=4)
            tk.Label(self._frame, text=val, font=("Arial",10,"bold"),
                     fg=vc, anchor="w").grid(row=i, column=2, sticky="w", padx=6)


# ── 設定視窗 ─────────────────────────────────────────────────

class SettingsView:
    def __init__(self, master, ctrl):
        self._master = master
        self._ctrl   = ctrl
        self._win    = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("⚙️ 設定"); w.resizable(False, False); w.grab_set()

        hdr = tk.Frame(w, bg="#F3E5F5", pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙️ 設定", font=("Arial",14,"bold"),
                 bg="#F3E5F5", fg="#4A148C").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=8)
        g = tk.Frame(w, padx=24); g.pack()
        cfg = self._ctrl.model.settings
        row = 0

        # 寵物名稱
        tk.Label(g, text="🐾 寵物名稱", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._name = tk.StringVar(value=self._ctrl.model.pet_name)
        tk.Entry(g, textvariable=self._name, width=14, font=("Arial",10)
                 ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        # ── 番茄鐘時間 ─────────────────────────────────────────
        tk.Label(g, text="🍅 工作時間（分）", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._work = tk.IntVar(value=cfg["work_min"])
        tk.Spinbox(g, from_=1, to=120, textvariable=self._work,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="☀️ 短休息（分）", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._rest = tk.IntVar(value=cfg["rest_min"])
        tk.Spinbox(g, from_=1, to=60, textvariable=self._rest,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="🌙 長休息（分）", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._long_rest = tk.IntVar(value=cfg.get("long_rest_min", 15))
        tk.Spinbox(g, from_=5, to=60, textvariable=self._long_rest,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="🔁 每輪工作節數", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._sessions_n = tk.IntVar(value=cfg.get("sessions_before_long", 4))
        tk.Spinbox(g, from_=2, to=10, textvariable=self._sessions_n,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="⚡ 自動開始下一節", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._auto_start = tk.BooleanVar(value=cfg.get("auto_start", False))
        tk.Checkbutton(g, variable=self._auto_start
                       ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        ttk.Separator(g).grid(row=row, column=0, columnspan=2,
                              sticky="ew", pady=6); row+=1

        # ── 視窗 ───────────────────────────────────────────────
        tk.Label(g, text="📌 永遠置頂", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._topmost = tk.BooleanVar(value=cfg["always_on_top"])
        tk.Checkbutton(g, variable=self._topmost
                       ).grid(row=row, column=1, sticky="w", padx=10)

        ttk.Separator(w).pack(fill="x", padx=12, pady=10)
        bf = tk.Frame(w); bf.pack(pady=6)
        tk.Button(bf, text="✔ 套用", font=("Arial",10,"bold"), width=8,
                  bg="#2E7D32", fg="white", relief="flat",
                  command=self._apply).pack(side="left", padx=6)
        tk.Button(bf, text="✖ 取消", font=("Arial",10), width=8,
                  relief="flat", command=w.destroy).pack(side="left", padx=6)

    def _apply(self):
        self._ctrl.apply_settings(
            name                 = self._name.get().strip() or "小白",
            work_min             = max(1,  self._work.get()),
            rest_min             = max(1,  self._rest.get()),
            long_rest_min        = max(5,  self._long_rest.get()),
            sessions_before_long = max(2,  self._sessions_n.get()),
            auto_start           = self._auto_start.get(),
            topmost              = self._topmost.get(),
            character            = "default",
        )
        self._win.destroy()


# ── 主視窗（PetView）─────────────────────────────────────────

class PetView:
    """
    視圖層（View）。
    純負責 tkinter 渲染與事件轉發，不含任何業務邏輯。
    透過 set_controller() 連結 Controller。
    """
    FALLBACK = "(ovo)"

    def __init__(self, root: tk.Tk, model: PetModel):
        self._root  = root
        self._model = model
        self._ctrl  = None

        self._cache     = AnimationCache()
        self._character = model.settings.get("character", "default")
        self._status    = "idle"
        self._frame_i = 0
        self._dragging = False
        self._ox = self._oy = 0
        self._pre_drag = "idle"

        self._anim_id = self._eat_id = self._hp_id = None
        # 目前若有被 post 的選單，會放在這裡以便其他事件可以關閉它
        self._posted_menu = None

        cfg = model.settings
        self._setup_window(cfg)
        self._build_ui(cfg)

        # 子視窗（需要 ctrl，先置 None）
        self._shop_v    = None
        self._pack_v    = None
        self._stats_v   = None
        self._sett_v    = None

    def set_controller(self, ctrl):
        self._ctrl   = ctrl
        self._shop_v  = ShopView(self._root, ctrl)
        self._pack_v  = BackpackView(self._root, ctrl)
        self._stats_v = StatsView(self._root, ctrl)
        self._sett_v  = SettingsView(self._root, ctrl)
        self._bind_events()
        self._animate()
        self._hp_loop()
        self._root.after(0, self._snap_to_bottom_right)

    # ── 視窗初始化 ────────────────────────────────────────────

    def _setup_window(self, cfg: dict):
        r = self._root
        r.overrideredirect(True)
        r.wm_attributes("-topmost", cfg.get("always_on_top", True))
        r.attributes("-transparentcolor", BG)
        r.config(bg=BG)
        r.geometry("+0+0")
        r.grid_columnconfigure(0, weight=1)

    def _build_ui(self, cfg: dict):
        # 對話氣泡（Toplevel 浮動，不影響主視窗 grid）
        self._speech = SpeechBubble(self._root)

        # row=0：對話框（頭頂計時器）
        self._bubble = TimerBubble(self._root)

        # row=1：寵物圖片 / 備用文字
        self._img_lbl = tk.Label(self._root, bg=BG, bd=0)
        self._img_lbl.grid(row=1, column=0)

        self._txt_lbl = tk.Label(self._root, text=self.FALLBACK,
                                  font=("Courier", 32, "bold"), bg=BG, fg="#333")
        self._txt_lbl.grid(row=1, column=0)   # 預先登記位置，讓 grid_remove 可正常呼叫
        self._txt_lbl.grid_remove()            # 初始隱藏

        # row=2：心情 & 金幣快速資訊
        self._info_lbl = tk.Label(self._root, text="", bg=BG, font=("Arial", 9))
        self._info_lbl.grid(row=2, column=0, pady=(0, 2))

        self._refresh_info()

    def _snap_to_bottom_right(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        pw = self._root.winfo_width()
        ph = self._root.winfo_height()
        x = max(0, sw - pw - 20)
        y = max(0, sh - ph - 60)   # 60px 保留 Windows 工作列空間
        self._root.geometry(f"+{x}+{y}")

    # ── 公開介面（供 Controller 呼叫）─────────────────────────

    def refresh_info(self):
        self._refresh_info()

    def set_status(self, status: str):
        if self._status != status:
            self._status, self._frame_i = status, 0

    def update_timer(self, minutes: int, seconds: int, phase: str,
                     session_done: int, sessions_n: int, total_s: int, visible: bool):
        self._bubble.set_visible(visible)
        if visible:
            self._bubble.update(minutes, seconds, phase, session_done, sessions_n, total_s)

    def hide_timer(self):
        self._bubble.set_visible(False)

    def show_speech(self, text: str, duration_ms: int = 4000):
        self._speech.show(text, duration_ms)

    def trigger_eating(self, return_to: str):
        if self._eat_id:
            self._root.after_cancel(self._eat_id)
        self.set_status("eating")
        self._eat_id = self._root.after(
            EATING_MS,
            lambda: self.set_status(return_to) if self._status == "eating" else None,
        )

    def update_character(self, character: str):
        self._character = character

    def apply_window_settings(self, cfg: dict):
        self._root.wm_attributes("-topmost", cfg["always_on_top"])

    def open_shop(self):      self._shop_v.open()
    def open_backpack(self):  self._pack_v.open()
    def open_stats(self):     self._stats_v.open()
    def open_settings(self):  self._sett_v.open()

    def show_info(self, title: str, msg: str):
        _info_dialog(self._root, title, msg)

    def show_warn(self, title: str, msg: str):
        _warn_dialog(self._root, title, msg)

    def destroy(self):
        for aid in (self._anim_id, self._eat_id, self._hp_id):
            if aid: self._root.after_cancel(aid)
        self._speech.cancel()
        if getattr(self, '_posted_menu', None):
            try:
                self._posted_menu.unpost()
            except Exception:
                pass
            try:
                self._posted_menu.grab_release()
            except Exception:
                pass
            self._posted_menu = None
        self._root.destroy()

    # ── 內部渲染 ──────────────────────────────────────────────

    def _refresh_info(self):
        hp     = self._model.happiness
        coins  = self._model.coins
        filled = hp // 25
        hearts = "♥" * filled + "♡" * (4 - filled)
        color  = "#C62828" if hp < 30 else ("#F57F17" if hp < 60 else "#777")
        self._info_lbl.config(text=f"{hearts}  💰 {coins}", fg=color)

    def _animate(self):
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return
        # 若有選單被 post，當動畫驅動時強制關閉它，避免選單殘留
        if getattr(self, '_posted_menu', None):
            try:
                self._posted_menu.unpost()
            except Exception:
                pass
            try:
                self._posted_menu.grab_release()
            except Exception:
                pass
            self._posted_menu = None
        frames = self._cache.get(self._status, self._character)
        if frames:
            # 若切換為動畫幀，確保文字標籤隱藏
            self._txt_lbl.grid_remove()
            self._img_lbl.grid(row=1, column=0)
            frame = frames[self._frame_i % len(frames)]
            self._img_lbl.config(image=frame)
            self._img_lbl.image = frame
            self._frame_i = (self._frame_i + 1) % len(frames)
        else:
            # 切換到文字（圖片隱藏）時，一併關閉任何已打開的選單，避免殘留
            self._img_lbl.grid_remove()
            self._txt_lbl.grid(row=1, column=0)
            if getattr(self, '_posted_menu', None):
                try:
                    self._posted_menu.unpost()
                except Exception:
                    pass
                try:
                    self._posted_menu.grab_release()
                except Exception:
                    pass
                self._posted_menu = None
        self._anim_id = self._root.after(FRAME_MS, self._animate)

    def _hp_loop(self):
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return
        if self._ctrl:
            self._ctrl.on_hp_tick()
        self._hp_id = self._root.after(HP_DECAY_MS, self._hp_loop)

    # ── 拖曳 ──────────────────────────────────────────────────

    def _drag_start(self, event):
        self._ox = event.x_root - self._root.winfo_x()
        self._oy = event.y_root - self._root.winfo_y()
        if not self._dragging:
            self._dragging = True
            self._pre_drag = self._status
            self.set_status("drag")
        # 開始拖曳時若有選單正在顯示，先關閉它，避免選單殘留
        if getattr(self, '_posted_menu', None):
            try:
                self._posted_menu.unpost()
            except Exception:
                pass
            try:
                self._posted_menu.grab_release()
            except Exception:
                pass
            self._posted_menu = None

    def _drag_move(self, event):
        self._root.geometry(f"+{event.x_root - self._ox}+{event.y_root - self._oy}")
        self._speech.reposition()

    def _drag_end(self, event):
        if self._dragging:
            self._dragging = False
            self.set_status(self._pre_drag)

    def _right_click(self, event):
        if self._ctrl:
            try:
                self._ctrl.show_menu(event)
            except tk.TclError:
                pass

    def _bind_events(self):
        for w in (self._root, self._img_lbl, self._txt_lbl, self._info_lbl):
            w.bind("<Button-1>",        self._drag_start)
            w.bind("<B1-Motion>",       self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_end)
            w.bind("<Button-3>",        self._right_click)


# ── 自訂對話框（統一入口）────────────────────────────────────

def _show_dialog(anchor: tk.Misc, title: str, body: str, color: str):
    """所有自訂對話框的共用實作，置頂顯示於螢幕正中心，阻塞直到使用者確認。"""
    win = tk.Toplevel(anchor)
    win.resizable(False, False)
    win.wm_attributes("-topmost", True)
    win.grab_set()

    hdr = tk.Frame(win, bg=color, pady=10)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, font=("Segoe UI", 12, "bold"),
             bg=color, fg="white", padx=14).pack(anchor="w")

    tk.Label(win, text=body, font=("Segoe UI", 10),
             justify="center", wraplength=260,
             padx=20, pady=14).pack()

    tk.Button(win, text="  確認  ",
              font=("Segoe UI", 10, "bold"),
              bg=color, fg="white", relief="flat",
              padx=16, pady=5,
              command=win.destroy).pack(pady=(0, 14))

    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    ww = win.winfo_width()
    wh = win.winfo_height()
    win.geometry(f"+{(sw - ww) // 2}+{(sh - wh) // 2}")
    anchor.wait_window(win)


def _info_dialog(anchor: tk.Misc, title: str, body: str):
    _show_dialog(anchor, title, body, "#1565C0")


def _warn_dialog(anchor: tk.Misc, title: str, body: str):
    _show_dialog(anchor, title, body, "#C0392B")


# ════════════════════════════════════════════════════════════════
# LAYER 4 — CONTROLLER（業務邏輯）
# ════════════════════════════════════════════════════════════════

class PetController:
    """
    控制層（Controller/Presenter）。
    接收 View 的事件 → 操作 Model → 驅動 View 更新。
    持有 PomodoroTimer 和 MusicPlayer。
    """

    def __init__(self, root: tk.Tk, model: PetModel, view: PetView):
        self._root   = root
        self._model  = model
        self._view   = view
        self._music        = MusicPlayer()
        self._status       = "idle"
        self._checkin_id   = None
        self._idle_chat_id = None

        cfg = model.settings
        self._pomo = PomodoroTimer(
            root,
            work_min             = cfg["work_min"],
            rest_min             = cfg["rest_min"],
            long_rest_min        = cfg.get("long_rest_min", 15),
            sessions_before_long = cfg.get("sessions_before_long", 4),
            auto_start           = cfg.get("auto_start", False),
            on_tick              = self._on_tick,
            on_work_end          = self._on_work_end,
            on_short_rest_end    = self._on_short_rest_end,
            on_long_rest_end     = self._on_long_rest_end,
        )
        view.set_controller(self)
        self._schedule_idle_chat()

    @property
    def model(self) -> PetModel:
        return self._model

    # ── 番茄鐘回呼 ───────────────────────────────────────────

    def _on_tick(self, m: int, s: int, phase: str,
                 session_done: int, sessions_n: int, total_s: int):
        self._view.update_timer(m, s, phase, session_done, sessions_n, total_s,
                                visible=self._pomo.running)

    def _on_work_end(self):
        self._cancel_work_checkin()
        mult   = self._model.bonus_mult
        reward = 10 * mult
        self._model.coins += reward
        self._model.inc_stat("coins_earned", reward)
        self._model.inc_stat("pomodoro_done")
        if mult > 1:
            self._model.bonus_mult = 1

        new_phase = self._pomo.phase
        self._set_status("alert")
        self._view.refresh_info()

        bonus = f"⚡ 加倍符文生效 ×{mult}！\n" if mult > 1 else ""
        if new_phase == "long_rest":
            head, color = "一輪完成！確認後開始大休息。", "#1A5276"
        else:
            head, color = "番茄鐘結束！確認後開始休息。", "#B03A2E"

        _show_dialog(
            self._root, "🍅 番茄鐘結束！",
            f"{head}\n\n{bonus}🎉 獲得金幣 +{reward}！（目前：{self._model.coins} 枚）",
            color,
        )
        self._set_status_for_rest(new_phase)
        key = "long_rest_start" if new_phase == "long_rest" else "rest_start"
        self._root.after(300, lambda: self._view.show_speech(
            random.choice(DIALOGUES[key]), 5000))

    def _on_short_rest_end(self):
        _show_dialog(self._root, "☀️ 休息結束！",
                     "確認後開始下一節工作！💪", "#1E8449")
        self._set_status_for_work()
        if self._pomo.auto_start:
            self._root.after(300, self._start_work_session_feedback)

    def _on_long_rest_end(self):
        _show_dialog(self._root, "🎉 大休息結束！",
                     "一個完整週期完成！\n確認後開始新一輪，加油！💪", "#1A5276")
        self._set_status_for_work()
        if self._pomo.auto_start:
            self._root.after(300, self._start_work_session_feedback)

    # ── 心情衰減 ──────────────────────────────────────────────

    def on_hp_tick(self):
        if self._status not in ("eating", "alert"):
            old_hp = self._model.happiness
            self._model.happiness -= 1
            self._view.refresh_info()
            if old_hp == 30:
                self._view.show_speech(random.choice(DIALOGUES["low_hp"]), 6000)
            elif old_hp == 60:
                self._view.show_speech(random.choice(DIALOGUES["mid_hp"]))

    # ── 狀態機 ────────────────────────────────────────────────

    def _set_status(self, status: str):
        self._status = status
        self._view.set_status(status)

    def do_idle(self):
        self._set_status("idle")

    def do_coding(self):
        self._set_status("coding")

    def do_studying(self):
        self._set_status("studying")

    def do_sleep(self):
        folder = resource_path(os.path.join("assets", "sleep"))
        self._set_status("sleep" if os.path.isdir(folder) else "idle")

    # ── 番茄鐘控制 ───────────────────────────────────────────

    def toggle_pomo(self):
        if self._pomo.running:
            self._pomo.pause()
            self._cancel_work_checkin()
            self._view.hide_timer()
            if self._pomo.phase == "work":
                self._music.stop()
        else:
            self._pomo.start()
            if self._pomo.phase == "work":
                self._set_status("studying")
                self._music.play()
                self._root.after(200, self._start_work_session_feedback)

    def reset_pomo(self):
        self._pomo.reset()
        self._music.stop()
        self._view.hide_timer()


    # ── 商店 / 庫存 ──────────────────────────────────────────

    def buy_item(self, item: dict) -> bool:
        """購買後放入背包，不立即使用。"""
        cost = item["cost"]
        if self._model.coins < cost:
            self._view.show_warn("金幣不足",
                f"需要 {cost} 金幣，目前只有 {self._model.coins} 枚。")
            return False
        self._model.coins -= cost
        self._model.inc_stat("coins_spent", cost)
        self._model.add_inv(item["id"])
        self._view.refresh_info()
        return True

    def use_item(self, item_id: str):
        """從背包使用道具或食物。"""
        if not self._model.remove_inv(item_id):
            self._view.show_warn("道具不足", "背包中沒有這個道具了！"); return
        self._model.inc_stat("items_used")

        if item_id in FOOD_IDS:
            food = FOOD_MAP[item_id]
            self._model.happiness += food["hp"]
            self._view.refresh_info()
            self._view.trigger_eating(self._status)
            self._view.show_speech(random.choice(DIALOGUES["eating"]), 3000)
        elif item_id == "potion":
            self._model.happiness = 100
            self._view.refresh_info()
            self._view.show_info("💊 快樂藥水",
                f"{self._model.pet_name} 心情恢復至 100%！開心極了！")
        elif item_id == "giftbox":
            reward = random.randint(5, 30)
            self._model.coins += reward
            self._model.inc_stat("coins_earned", reward)
            self._view.refresh_info()
            self._view.show_info("🎁 神秘禮盒", f"恭喜！獲得 💰 {reward} 金幣！")
        elif item_id == "rune":
            self._model.bonus_mult = 2
            self._view.show_info("⚡ 加倍符文", "符文激活！下個番茄鐘金幣 ×2！")
        elif item_id == "ribbon":
            self._view.show_info("🎀 蝴蝶結",
                f"{self._model.pet_name} 戴上了可愛的蝴蝶結～真漂亮！")

    def daily_checkin(self):
        today = str(date.today())
        if self._model.last_checkin == today:
            return
        self._model.last_checkin = today
        self._model.coins += 5
        self._model.inc_stat("coins_earned", 5)
        self._view.refresh_info()
        self._view.show_info("🎁 每日簽到",
            f"簽到成功！獲得 +5 金幣！\n目前：{self._model.coins} 枚")

    # ── 設定套用 ──────────────────────────────────────────────

    def apply_settings(self, name: str, work_min: int, rest_min: int,
                       long_rest_min: int, sessions_before_long: int,
                       auto_start: bool, topmost: bool,
                       character: str = "default"):
        self._model.pet_name = name
        self._model.patch_settings(
            work_min=work_min, rest_min=rest_min,
            long_rest_min=long_rest_min,
            sessions_before_long=sessions_before_long,
            auto_start=auto_start,
            always_on_top=topmost,
            character=character,
        )
        self._pomo.update_config(work_min, rest_min, long_rest_min,
                                 sessions_before_long, auto_start)
        self._view.apply_window_settings(self._model.settings)
        self._view.update_character(character)

    # ── 右鍵選單 ──────────────────────────────────────────────

    def show_menu(self, event):
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return

        m   = self._model
        inv = m.inventory
        FNT    = ("Segoe UI", 10)
        FNT_SM = ("Segoe UI",  9)
        FNT_BD = ("Segoe UI", 10, "bold")

        menu = tk.Menu(self._root, tearoff=0, font=FNT)

        # ── 寵物資訊（唯讀）────────────────────────────────────
        menu.add_command(label=f"  🐾  {m.pet_name}",
                         state="disabled", font=FNT_BD)
        hp     = m.happiness
        hp_bar = "♥" * (hp // 25) + "♡" * (4 - hp // 25)
        warn   = "  ⚠ 心情過低！" if hp < 30 else ""
        bonus  = "  ⚡ 加倍符文" if m.bonus_mult > 1 else ""
        menu.add_command(
            label=f"     {hp_bar} {hp}%{warn}   💰 {m.coins} 枚{bonus}",
            state="disabled", font=FNT_SM)
        menu.add_separator()

        # ── 活動 ─────────────────────────────────────────────
        menu.add_command(label="  😴  發呆",   command=self.do_idle)
        menu.add_command(label="  💻  寫程式", command=self.do_coding)
        menu.add_command(label="  📚  讀書",   command=self.do_studying)
        menu.add_command(label="  💤  睡覺",   command=self.do_sleep)
        menu.add_separator()

        # ── 餵食（背包中的食物）──────────────────────────────
        foods = [(iid, cnt) for iid, cnt in inv.items()
                 if iid in FOOD_IDS and cnt > 0]
        if foods:
            for iid, cnt in foods:
                food = FOOD_MAP[iid]
                menu.add_command(
                    label=f"  {food['icon']}  {food['name']} ×{cnt}"
                          f"  （{food['desc']}）",
                    command=lambda i=iid: self.use_item(i))
            menu.add_separator()

        # ── 商店 & 背包 ───────────────────────────────────────
        bag_n     = sum(v for v in inv.values() if v > 0)
        bag_label = f"  🎒  背包（{bag_n} 件）" if bag_n else "  🎒  背包（空）"
        menu.add_command(label="  🏪  商店",   command=self._view.open_shop)
        menu.add_command(label=bag_label,       command=self._view.open_backpack)
        menu.add_separator()

        # ── 音樂 ─────────────────────────────────────────────
        music = tk.Menu(menu, tearoff=0, font=FNT)
        music.add_command(label="  🎶  神隱少女",
                          command=self._music.play)
        music.add_separator()
        music.add_command(label="  📴  關閉音樂",
                          command=self._music.stop)
        menu.add_cascade(label="  🎵  切換音樂", menu=music)

        # ── 番茄鐘子選單 ──────────────────────────────────────
        phase = self._pomo.phase
        sd, sn = self._pomo.session_done, self._pomo.sessions_n
        status = {"work":      f"工作中  第 {sd+1}/{sn} 節",
                  "rest":      f"休息中（{sd}/{sn} 節完成）",
                  "long_rest": "大休息中"}.get(phase, "")

        pomo = tk.Menu(menu, tearoff=0, font=FNT)
        pomo.add_command(label=f"     {status}",
                         state="disabled", font=FNT_SM)
        pomo.add_separator()
        pomo.add_command(
            label="  ⏸️  暫停" if self._pomo.running else "  ▶️  開始",
            command=self.toggle_pomo)
        pomo.add_command(label="  🔁  重設全部", command=self.reset_pomo)
        
        pomo.add_separator()

        pre = tk.Menu(pomo, tearoff=0, font=FNT)
        pre.add_command(label="  🍅  經典   25 / 5 / 15 分",
                        command=lambda: self._apply_preset(25, 5, 15, 4))
        pre.add_command(label="  💪  雙倍   50 / 10 / 30 分",
                        command=lambda: self._apply_preset(50, 10, 30, 4))
        pre.add_command(label="  ⚡  迷你   15 / 3 / 10 分",
                        command=lambda: self._apply_preset(15, 3, 10, 4))
        pre.add_separator()
        pre.add_command(label="  ⚙  自訂時間…", command=self._show_custom_dialog)
        pomo.add_cascade(label="  ⏱  快速預設", menu=pre)

        menu.add_cascade(label="  🍅  番茄鐘",  menu=pomo)
        menu.add_separator()

        # ── 底部 ──────────────────────────────────────────────
        menu.add_command(label="  📊  統計",     command=self._view.open_stats)
        menu.add_command(label="  ⚙️  設定",     command=self._view.open_settings)
        menu.add_separator()
        def _exit_app():
            try: menu.unpost()
            except Exception: pass
            try: menu.grab_release()
            except Exception: pass
            self._root.after_idle(self._quit)

        menu.add_command(label="  ❌  結束程式",
                          command=_exit_app)

        try:
            # 記錄目前顯示的選單，讓 View 可在必要時主動關閉它
            try: self._view._posted_menu = menu
            except Exception: pass
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try: menu.unpost()
            except Exception: pass
            try: menu.grab_release()
            except Exception: pass
            try: self._view._posted_menu = None
            except Exception: pass

    def _apply_preset(self, work: int, rest: int, long_rest: int, sessions: int):
        auto = self._model.settings.get("auto_start", False)
        self._model.patch_settings(
            work_min=work, rest_min=rest,
            long_rest_min=long_rest, sessions_before_long=sessions,
        )
        self._pomo.update_config(work, rest, long_rest, sessions, auto)
        self._view.hide_timer()

    def _show_custom_dialog(self):
        cfg = self._model.settings
        win = tk.Toplevel(self._root)
        win.title("自訂番茄鐘時間")
        win.resizable(False, False)
        win.grab_set()

        hdr = tk.Frame(win, bg="#FF5722", pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙ 自訂番茄鐘", font=("Arial", 12, "bold"),
                 bg="#FF5722", fg="white").pack()

        g = tk.Frame(win, padx=20, pady=10); g.pack()
        fields = [
            ("🍅 工作時間（分）", cfg["work_min"],                  1,  120),
            ("☀️ 短休息（分）",   cfg["rest_min"],                  1,   60),
            ("🌙 長休息（分）",   cfg.get("long_rest_min", 15),     5,   60),
            ("🔁 每輪節數",       cfg.get("sessions_before_long",4), 2,   10),
        ]
        vars_ = []
        for i, (lbl, val, lo, hi) in enumerate(fields):
            tk.Label(g, text=lbl, font=("Arial", 10), anchor="w"
                     ).grid(row=i, column=0, sticky="w", pady=5)
            v = tk.IntVar(value=val)
            vars_.append(v)
            tk.Spinbox(g, from_=lo, to=hi, textvariable=v,
                       width=6, font=("Arial", 10)
                       ).grid(row=i, column=1, sticky="w", padx=12)

        def _ok():
            bounds = [(1, 120), (1, 60), (5, 60), (2, 10)]
            values = [v.get() for v in vars_]
            w, r, lr, sn = (
                max(lo, min(hi, val))
                for (lo, hi), val in zip(bounds, values)
            )
            auto = self._model.settings.get("auto_start", False)
            self._model.patch_settings(
                work_min=w, rest_min=r,
                long_rest_min=lr, sessions_before_long=sn,
            )
            self._pomo.update_config(w, r, lr, sn, auto)
            self._view.hide_timer()
            win.destroy()

        bf = tk.Frame(win); bf.pack(pady=8)
        tk.Button(bf, text="✔ 套用", font=("Arial", 10, "bold"), width=8,
                  bg="#2E7D32", fg="white", relief="flat",
                  command=_ok).pack(side="left", padx=6)
        tk.Button(bf, text="✖ 取消", font=("Arial", 10), width=8,
                  relief="flat", command=win.destroy).pack(side="left", padx=6)

    def _set_status_for_work(self):
        self._set_status("studying")
        self._music.play()

    def _set_status_for_rest(self, phase: str):
        self._music.stop()
        if phase == "long_rest":
            folder = resource_path(os.path.join("assets", "sleep"))
            self._set_status("sleep" if os.path.isdir(folder) else "idle")
        else:
            self._set_status("idle")

    # ── 對話系統 ──────────────────────────────────────────────

    def _start_work_session_feedback(self):
        self._view.show_speech(random.choice(DIALOGUES["work_start"]), 3000)
        self._schedule_work_checkin()

    def _schedule_work_checkin(self, delay_ms: int = _CHECKIN_FIRST_MS):
        self._cancel_work_checkin()
        self._checkin_id = self._root.after(delay_ms, self._do_work_checkin)

    def _cancel_work_checkin(self):
        if self._checkin_id:
            self._root.after_cancel(self._checkin_id)
            self._checkin_id = None

    def _do_work_checkin(self):
        self._checkin_id = None
        if not self._pomo.running or self._pomo.phase != "work":
            return
        remain = self._pomo._remain
        total  = self._pomo._work_s
        ratio  = remain / max(1, total)
        if ratio > 0.66:
            key = "work_early"
        elif ratio > 0.33:
            key = "work_mid"
        else:
            key = "work_late"
        self._view.show_speech(random.choice(DIALOGUES[key]))
        self._schedule_work_checkin(_CHECKIN_INTERVAL_MS)

    def _schedule_idle_chat(self):
        self._cancel_idle_chat()
        self._idle_chat_id = self._root.after(_IDLE_CHAT_MS, self._do_idle_chat)

    def _cancel_idle_chat(self):
        if self._idle_chat_id:
            self._root.after_cancel(self._idle_chat_id)
            self._idle_chat_id = None

    def _do_idle_chat(self):
        self._idle_chat_id = None
        if self._status == "idle" and not self._pomo.running:
            self._view.show_speech(random.choice(DIALOGUES["idle"]))
        self._schedule_idle_chat()

    def _quit(self):
        self._music.stop()
        self._pomo.pause()
        self._cancel_work_checkin()
        self._cancel_idle_chat()
        self._model.sync_save()
        self._view.destroy()


# ════════════════════════════════════════════════════════════════
# 程式入口
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root  = tk.Tk()
    model = PetModel()
    view  = PetView(root, model)
    ctrl = PetController(root, model, view)    # 內部會呼叫 view.set_controller()
    root.mainloop()
