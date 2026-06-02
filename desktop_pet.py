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
import sys, os, json, threading, queue, random, time, re, math, shutil, uuid, winsound
from datetime import date, timedelta


def _nat_key(s: str) -> list:
    """自然排序 key，讓 slice_10 排在 slice_9 之後。"""
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r'(\d+)', s)]

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
_TODO_REMIND_MS      = 300_000   # 每 5 分鐘隨機提醒一項待辦
_TODO_CHECK_MS       =  60_000   # 每 1 分鐘檢查到期提醒

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

FREE_CHARS = {"default", "小紫"}

GACHA_POOL = {
    "貓咪": {"name":"橘橘貓咪", "rarity":"普通", "rarity_color":"78909C",
             "egg_color":"FF8C42", "desc":"一隻調皮的橘貓，愛撒嬌！"},
    "兔兔": {"name":"雪白兔兔", "rarity":"普通", "rarity_color":"78909C",
             "egg_color":"F4C2C2", "desc":"圓滾滾的雪白兔子！"},
    "企鵝": {"name":"企鵝紳士", "rarity":"稀有", "rarity_color":"42A5F5",
             "egg_color":"2C3E50", "desc":"搖搖擺擺的小紳士！"},
    "狐狸": {"name":"狡黠狐狸", "rarity":"稀有", "rarity_color":"42A5F5",
             "egg_color":"E8572E", "desc":"聰明伶俐，愛惡作劇！"},
    "小龍": {"name":"神秘小龍", "rarity":"傳說", "rarity_color":"FFD700",
             "egg_color":"7B2FBE", "desc":"千年一見的珍稀生物！"},
}
GACHA_WEIGHTS = {"貓咪": 35, "兔兔": 30, "企鵝": 18, "狐狸": 12, "小龍": 5}

# 孵蛋背景星星（模組載入時隨機生成一次）
_EGG_STARS = [(random.randint(5, 435), random.randint(5, 350)) for _ in range(50)]

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
    {"id":"egg",    "name":"角色蛋",  "icon":"🥚","cost":30,"desc":"孵出隨機新角色"},
]
FOOD_IDS  = frozenset(i["id"] for i in SHOP_FOOD)
FOOD_MAP  = {i["id"]: i for i in SHOP_FOOD}
ITEM_MAP  = {i["id"]: i for i in SHOP_ITEMS}
ALL_ITEMS = {**FOOD_MAP, **ITEM_MAP}

DEFAULT_DATA: dict = {
    "pet_name":      "小白",
    "coins":         0,
    "happiness":     100,
    "bonus_mult":    1,
    "last_checkin":  "",
    "inventory":     {},
    "first_launch":  False,
    "unlocked_chars": [],
    "stats": {
        "pomodoro_done": 0, "coins_earned": 0, "coins_spent": 0, "items_used": 0,
        "focus_minutes": 0, "today_count": 0,  "today_date":  "",
        "streak_days":   0, "last_focus_date": "",
    },
    "settings": {
        "work_min":25,"rest_min":5,"long_rest_min":15,
        "sessions_before_long":4,"auto_start":False,
        "always_on_top":True,
        "character":"default",
        "todo_remind_before_min": 5,
    },
    "todos": [],
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

    @property
    def first_launch(self) -> bool:  return self._d.get("first_launch", True)
    @first_launch.setter
    def first_launch(self, v: bool): self._d["first_launch"] = v; self._dirty()

    @property
    def unlocked_chars(self) -> list: return self._d.get("unlocked_chars", [])

    def add_unlocked_char(self, char_id: str):
        chars = self._d.setdefault("unlocked_chars", [])
        if char_id not in chars:
            chars.append(char_id)
            self._dirty()

    def remove_unlocked_char(self, char_id: str):
        chars = self._d.get("unlocked_chars", [])
        if char_id in chars:
            chars.remove(char_id)
            self._dirty()

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

    def set_stat(self, key: str, val) -> None:
        self._d["stats"][key] = val
        self._dirty()

    @property
    def todos(self) -> list:
        todos = self._d.setdefault("todos", [])
        # 補齊新欄位（舊格式相容）
        for t in todos:
            t.setdefault("priority", "medium")
            t.setdefault("category", "其他")
            t.setdefault("due_datetime", "")
            t.setdefault("remind_minutes", 0)
            t.setdefault("reminded", False)
            t.setdefault("note", "")
        return todos

    def add_todo(self, text: str, priority: str = "medium", category: str = "其他",
                 due: str = "", remind: int = 0, note: str = ""):
        self._d.setdefault("todos", []).append({
            "id": uuid.uuid4().hex[:8], "text": text, "done": False,
            "priority": priority, "category": category,
            "due_datetime": due, "remind_minutes": remind,
            "reminded": False, "note": note,
        })
        self._dirty()

    def update_todo(self, tid: str, **fields):
        for t in self._d.get("todos", []):
            if t["id"] == tid:
                t.update(fields); self._dirty(); return

    def toggle_todo(self, tid: str):
        for t in self._d.get("todos", []):
            if t["id"] == tid:
                t["done"] = not t["done"]; self._dirty(); return

    def remove_todo(self, tid: str):
        self._d["todos"] = [t for t in self._d.get("todos", []) if t["id"] != tid]
        self._dirty()

    def mark_reminded(self, tid: str):
        for t in self._d.get("todos", []):
            if t["id"] == tid:
                t["reminded"] = True; self._dirty(); return

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

def _list_characters(unlocked_chars=None) -> list[tuple[str, str]]:
    """掃描 assets/ 找出可用角色，回傳 [(顯示名, 資料夾/ID)]。
    FREE_CHARS 永遠顯示；unlocked_chars 列出已解鎖的抽蛋角色。"""
    STATES = ("idle", "coding", "studying", "eating", "drag")
    assets = resource_path("assets")

    name_map: dict[str, str] = {"default": "預設"}
    cfg_path = os.path.join(assets, "characters.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                name_map.update(json.load(f))
        except Exception as e:
            print(f"[Characters] 讀取名稱設定失敗：{e}")

    result = [(name_map.get("default", "帥潮教授"), "default")]
    if os.path.isdir(assets):
        for folder in sorted(os.listdir(assets)):
            if folder in ("default", "帥潮教授"):  # 帥潮教授 = default 的子目錄，避免重複
                continue
            subdir = os.path.join(assets, folder)
            if not (os.path.isdir(subdir) and any(
                    os.path.isdir(os.path.join(subdir, s)) for s in STATES)):
                continue
            if folder in GACHA_POOL:
                # GACHA 角色：只有解鎖才顯示
                if unlocked_chars and folder in unlocked_chars:
                    result.append((name_map.get(folder, folder), folder))
            else:
                # FREE_CHARS 或自訂匯入角色：永遠顯示
                result.append((name_map.get(folder, folder), folder))

    # 已解鎖但資料夾尚未存在的抽蛋角色
    if unlocked_chars:
        existing = {v for _, v in result}
        for char_id in unlocked_chars:
            if char_id in GACHA_POOL and char_id not in existing:
                result.append((GACHA_POOL[char_id]["name"], char_id))
    return result


class AnimationCache:
    """載入並快取各狀態 PNG 序列，支援多角色子目錄。"""

    def __init__(self):
        self._cache: dict[str, list] = {}

    def get(self, state: str, character: str = "default") -> list:
        key = f"{character}/{state}"
        if key in self._cache:
            return self._cache[key]
        if character == "default":
            prof = resource_path(os.path.join("assets", "帥潮教授", state))
            folder = prof if os.path.isdir(prof) else resource_path(os.path.join("assets", state))
        else:
            folder = resource_path(os.path.join("assets", character, state))
        frames = []
        if PIL_OK and os.path.isdir(folder):
            try:
                for name in sorted(
                    (f for f in os.listdir(folder) if f.lower().endswith(".png")),
                    key=_nat_key,
                ):
                    try:
                        img = Image.open(os.path.join(folder, name)).convert("RGBA")
                        bg  = Image.new("RGBA", img.size, BG)
                        bg.paste(img, mask=img.split()[3])
                        frames.append(ImageTk.PhotoImage(bg.convert("RGB")))
                    except Exception as e:
                        print(f"[Anim] {name}: {e}")
            except Exception as e:
                print(f"[Anim] {folder}: {e}")
        if not frames and state != "idle":
            idle_frames = self.get("idle", character)
            self._cache[key] = idle_frames
            return idle_frames
        self._cache[key] = frames
        return frames

    def invalidate(self, character: str = None):
        if character:
            self._cache = {k: v for k, v in self._cache.items()
                           if not k.startswith(f"{character}/")}
        else:
            self._cache.clear()


class MusicPlayer:
    """pygame 音樂播放器，支援淡入（啟動）／淡出（停止）。"""

    FADE = 2.0   # 淡入 / 淡出秒數

    def __init__(self):
        self._dir     = resource_path(os.path.join("assets", "music"))
        self._path    = resource_path(os.path.join("assets", "music", "study.mp3"))
        self._playing = False
        self._cancel  = threading.Event()
        self._tracks: list[str] = []
        self._index   = 0
        self._scan_tracks()

    def _scan_tracks(self):
        exts = {".mp3", ".ogg", ".wav"}
        if os.path.isdir(self._dir):
            self._tracks = sorted(
                os.path.join(self._dir, f)
                for f in os.listdir(self._dir)
                if os.path.splitext(f)[1].lower() in exts
            )
        if not self._tracks:
            self._tracks = [self._path]

    def next(self):
        """切換到下一首音樂。"""
        if not PYGAME_OK: return
        self._scan_tracks()
        self._index = (self._index + 1) % len(self._tracks)
        self._path  = self._tracks[self._index]
        was_playing = self._playing
        if was_playing:
            self._hard_stop()
            self.play()

    def get_tracks(self) -> list:
        """回傳音樂清單（只含檔名，不含副檔名）。"""
        self._scan_tracks()
        return [os.path.splitext(os.path.basename(t))[0] for t in self._tracks]

    def play_index(self, idx: int):
        """播放指定索引的音樂。"""
        if not PYGAME_OK or not self._tracks: return
        self._index = idx % len(self._tracks)
        self._path  = self._tracks[self._index]
        if self._playing:
            self._hard_stop()
        self.play()

    def delete_track(self, idx: int) -> bool:
        """從磁碟刪除指定索引的音樂，回傳是否成功。"""
        self._scan_tracks()
        if not self._tracks or idx >= len(self._tracks): return False
        path = self._tracks[idx]
        was_this = (self._playing and self._path == path)
        try:
            os.remove(path)
        except Exception as e:
            print(f"[Music] 刪除失敗: {e}"); return False
        self._scan_tracks()
        if was_this:
            if self._tracks:
                self._index = 0; self._path = self._tracks[0]
                self._hard_stop(); self.play()
            else:
                self._hard_stop()
        return True

    @property
    def current_track_name(self) -> str:
        if not self._path: return ""
        return os.path.splitext(os.path.basename(self._path))[0]

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
    def auto_start(self)       -> bool: return self._auto_start
    @property
    def remaining_seconds(self) -> int:  return self._remain
    @property
    def work_seconds(self)      -> int:  return self._work_s

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
        try:
            self._ensure_win()
        except Exception:
            return
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
        try:
            if not self._parent.winfo_exists():
                return
        except Exception:
            return
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


# ── 自製右鍵彈出選單 ─────────────────────────────────────────

class _PopupMenu:
    """
    自製右鍵彈出選單，以 Toplevel 實作。
    完美解決點擊空白處自動關閉、子選單、滑鼠移開收合等問題。
    """
    _BG      = "#FFFFFF"
    _HOV     = "#EAF0FC"
    _SEP_CLR = "#E0E0E0"
    _FG      = "#202124"
    _FG_DIS  = "#AAAAAA"
    _FONT    = ("Segoe UI", 10)

    def __init__(self, root: tk.Tk, parent_menu=None):
        self._root        = root
        self._parent_menu = parent_menu
        self._win         = None
        self._sub_menu    = None
        self._active_lbl  = None
        self._hover_after_id = None

    def popup(self, x: int, y: int, items: list):
        self.close()
        win = self._win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.wm_attributes("-topmost", True)
        win.config(bg=self._SEP_CLR)
        win.focus_set()

        body = tk.Frame(win, bg=self._BG, pady=4)
        body.pack(padx=1, pady=1)

        for item in items:
            if item.get("sep"):
                tk.Frame(body, height=1, bg=self._SEP_CLR).pack(
                    fill="x", padx=8, pady=2)
                continue

            text      = item.get("label", "")
            cmd       = item.get("cmd")
            sub_items = item.get("items")
            disabled  = item.get("disabled", False)
            font      = item.get("font", self._FONT)
            fg        = self._FG_DIS if disabled else self._FG

            display_text = f"{text}    ➔" if sub_items else text

            lbl = tk.Label(body, text=display_text, font=font, fg=fg, bg=self._BG,
                           anchor="w", padx=16, pady=4,
                           cursor="hand2" if (not disabled and (cmd or sub_items)) else "")
            lbl.pack(fill="x")

            if not disabled:
                lbl.bind("<Enter>", lambda e, w=lbl, si=sub_items: self._on_item_enter(w, si))
                lbl.bind("<Leave>", lambda e, w=lbl: self._on_item_leave(w))
                if cmd:
                    lbl.bind("<Button-1>", lambda e, c=cmd: self._invoke(c))

        win.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        ww = win.winfo_width()
        wh = win.winfo_height()
        px = min(x, sw - ww - 4)
        py = min(y, sh - wh - 4)
        win.geometry(f"+{max(0, px)}+{max(0, py)}")

        if self._parent_menu is None:
            self._root.bind_all("<ButtonPress>", self._on_global_click, add="+")
            win.bind("<FocusOut>", self._on_focus_out)
        else:
            win.bind("<FocusOut>", self._on_focus_out)

    def _on_item_enter(self, lbl, sub_items):
        self._active_lbl = lbl
        lbl.config(bg=self._HOV)
        if self._hover_after_id:
            self._root.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        if not sub_items and self._sub_menu:
            self._sub_menu.close()
            self._sub_menu = None
        if sub_items:
            self._hover_after_id = self._root.after(
                120, lambda: self._trigger_sub_menu(lbl, sub_items))

    def _trigger_sub_menu(self, lbl, sub_items):
        if self._sub_menu and self._sub_menu._win:
            self._sub_menu.close()
            self._sub_menu = None
        self._sub_menu = _PopupMenu(self._root, parent_menu=self)
        self._win.update_idletasks()
        rx  = self._win.winfo_rootx()
        rw  = self._win.winfo_width()
        ly  = lbl.winfo_rooty()
        sw  = self._root.winfo_screenwidth()
        sub_w = 170
        sub_x = rx + rw - 2 if rx + rw + sub_w < sw else rx - sub_w + 2
        sub_y = ly - 4
        self._sub_menu.popup(sub_x, sub_y, sub_items)

    def _on_item_leave(self, lbl):
        lbl.config(bg=self._BG)
        if self._hover_after_id:
            self._root.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        self._root.after(100, self._check_cascade_leave)

    def _check_cascade_leave(self):
        mx = self._root.winfo_pointerx()
        my = self._root.winfo_pointery()
        if not self._is_mouse_in_menu_tree(mx, my):
            if self._sub_menu:
                self._sub_menu.close()
                self._sub_menu = None

    def _is_mouse_in_menu_tree(self, mx, my) -> bool:
        if self._win and self._win.winfo_exists():
            wx, wy = self._win.winfo_rootx(), self._win.winfo_rooty()
            ww, wh = self._win.winfo_width(),  self._win.winfo_height()
            if wx <= mx <= wx + ww and wy <= my <= wy + wh:
                return True
        if self._sub_menu:
            return self._sub_menu._is_mouse_in_menu_tree(mx, my)
        return False

    def close(self):
        if self._hover_after_id:
            self._root.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        if self._sub_menu:
            self._sub_menu.close()
            self._sub_menu = None
        if self._win:
            try: self._win.destroy()
            except Exception: pass
            self._win = None

    def close_all(self):
        try: self._root.unbind_all("<ButtonPress>")
        except Exception: pass
        if self._parent_menu:
            self._parent_menu.close_all()
        else:
            self.close()

    def _invoke(self, cmd):
        self.close_all()
        try:
            self._root.after(10, cmd)
        except Exception as e:
            print(f"[Popup] {e}")

    def _on_global_click(self, event):
        mx, my = event.x_root, event.y_root
        if not self._is_mouse_in_menu_tree(mx, my):
            self.close_all()

    def _on_focus_out(self, event):
        self._root.after(100, self._check_focus_loss)

    def _check_focus_loss(self):
        mx = self._root.winfo_pointerx()
        my = self._root.winfo_pointery()
        top_menu = self
        while top_menu._parent_menu:
            top_menu = top_menu._parent_menu
        if not top_menu._is_mouse_in_menu_tree(mx, my):
            top_menu.close_all()


# ── 孵蛋抽角色畫面 ───────────────────────────────────────────

class EggGachaScreen:
    """孵蛋抽角色畫面（Toplevel overlay）。
    首次啟動或購買角色蛋後顯示，點擊蛋 CLICKS_TO_HATCH 次後破殼。
    callback: on_complete(char_id, pet_name)
    """
    CLICKS_TO_HATCH = 7
    EGG_W, EGG_H    = 460, 330

    _EGG_THEMES = [
        {"main": "FFD700", "pattern": "FFA500", "glow": "FFF9C4", "name": "金色神蛋"},
        {"main": "9C27B0", "pattern": "E040FB", "glow": "F3E5F5", "name": "魔法紫蛋"},
        {"main": "1565C0", "pattern": "42A5F5", "glow": "E3F2FD", "name": "海洋藍蛋"},
        {"main": "C62828", "pattern": "FF5252", "glow": "FFEBEE", "name": "炎熱紅蛋"},
        {"main": "2E7D32", "pattern": "69F0AE", "glow": "E8F5E9", "name": "翡翠綠蛋"},
    ]

    def __init__(self, root: tk.Tk, on_complete):
        self._root       = root
        self._on_complete= on_complete
        self._frame      = 0
        self._phase      = "idle"
        self._phase_t    = 0
        self._click_cnt  = 0
        self._shake_x    = 0
        self._shake_f    = 0
        self._cracks: list = []
        self._particles: list = []
        self._result     = None
        self._pet_name   = ""
        self._egg        = random.choice(self._EGG_THEMES)
        self._running    = True

        self._build()
        self._tick()

    # ── UI ──────────────────────────────────────────────────────

    def _build(self):
        win = self._win = tk.Toplevel(self._root)
        win.title("🥚 孵蛋")
        win.resizable(False, False)
        win.configure(bg="#1A1B2E")
        win.wm_attributes("-topmost", True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: None)  # 孵化中不可關閉

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"520x760+{(sw-520)//2}+{(sh-760)//2}")

        tk.Label(win, text="🥚  神秘之蛋", bg="#1A1B2E", fg="#FFFFFF",
                 font=("Microsoft JhengHei", 18, "bold")).pack(pady=(18, 2))
        tk.Label(win, text="一顆蘊含神秘力量的蛋正在等待你孵化…",
                 bg="#1A1B2E", fg="#8888BB",
                 font=("Microsoft JhengHei", 10)).pack(pady=(0, 4))

        self._canvas = tk.Canvas(win, width=self.EGG_W, height=self.EGG_H,
                                  bg="#1A1B2E", highlightthickness=0)
        self._canvas.pack()

        self._egg_name_var = tk.StringVar(value=f"✨  {self._egg['name']}  ✨")
        tk.Label(win, textvariable=self._egg_name_var, bg="#1A1B2E",
                 fg=f"#{self._egg['main']}",
                 font=("Microsoft JhengHei", 12, "bold")).pack(pady=2)

        # 名字輸入區
        self._inp_frame = tk.Frame(win, bg="#252640", padx=20, pady=10)
        self._inp_frame.pack(fill="x", padx=44, pady=6)
        tk.Label(self._inp_frame, text="為你的新夥伴取個名字：",
                 bg="#252640", fg="#CCCCEE",
                 font=("Microsoft JhengHei", 10)).pack()
        self._name_var = tk.StringVar()
        self._entry = tk.Entry(
            self._inp_frame, textvariable=self._name_var,
            font=("Microsoft JhengHei", 13), bg="#1E1E38", fg="#FFFFFF",
            insertbackground="#FFFFFF", relief="flat", justify="center", width=18
        )
        self._entry.pack(ipady=6, pady=4)
        self._entry.focus()
        self._entry.bind("<Return>", lambda e: self._confirm_name())
        self._hint_var = tk.StringVar(value="2–8 個字，按 Enter 或點「確認」")
        tk.Label(self._inp_frame, textvariable=self._hint_var, bg="#252640",
                 fg="#7777AA", font=("Microsoft JhengHei", 9)).pack()

        self._confirm_btn = tk.Button(
            win, text="確認名字，開始孵化！",
            font=("Microsoft JhengHei", 11, "bold"),
            bg="#6C5CE7", fg="white",
            activebackground="#8B7CF8", activeforeground="white",
            relief="flat", padx=24, pady=8, cursor="hand2",
            command=self._confirm_name
        )
        self._confirm_btn.pack(pady=4)

        self._status_var = tk.StringVar(value="")
        tk.Label(win, textvariable=self._status_var, bg="#1A1B2E",
                 fg="#E84393", font=("Microsoft JhengHei", 11, "bold")).pack(pady=2)

        self._claim_btn = tk.Button(
            win, text="✨ 確認領取！",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="#E84393", fg="white",
            activebackground="#FF5AB0", activeforeground="white",
            relief="flat", padx=28, pady=10, cursor="hand2",
            command=self._claim
        )

    # ── 互動 ────────────────────────────────────────────────────

    def _confirm_name(self):
        name = self._name_var.get().strip()
        if not name:
            self._hint_var.set("⚠ 請先幫你的夥伴取個名字！"); return
        if len(name) > 8:
            self._hint_var.set("⚠ 名字最多 8 個字哦！"); return
        self._pet_name = name
        self._inp_frame.pack_forget()
        self._confirm_btn.pack_forget()
        self._phase = "waiting"
        self._status_var.set(f"點擊蛋孵化！還需 {self.CLICKS_TO_HATCH} 下 🥚")
        self._canvas.config(cursor="hand2")
        self._canvas.bind("<Button-1>", self._on_click)

    def _on_click(self, _=None):
        if self._phase != "waiting":
            return
        self._click_cnt += 1
        remaining = self.CLICKS_TO_HATCH - self._click_cnt
        self._shake_x = 16
        self._shake_f = 12

        templates = [
            (-15,-60,-30,-10), (-30,-10,-10,30),
            (5,-70,20,-20),    (20,-20,35,20),
            (-5,-55,15,-5),    (-40,0,-15,40),
            (30,-40,45,10),
        ]
        idx = self._click_cnt - 1
        if idx < len(templates):
            self._cracks.append(templates[idx])

        if remaining <= 0:
            self._status_var.set("💥 破殼而出！！")
            self._phase = "explode"
            self._phase_t = 0
            ex, ey = self.EGG_W // 2, self.EGG_H // 2 - 10
            self._gen_explosion(ex, ey)
            self._result = random.choices(
                list(GACHA_POOL.keys()),
                weights=[GACHA_WEIGHTS[k] for k in GACHA_POOL.keys()],
                k=1
            )[0]
            self._result_tk_frames: list = []
            self._load_result_sprite()
        else:
            self._status_var.set(f"繼續點！還需 {remaining} 下 💥")

    # ── 動畫 ────────────────────────────────────────────────────

    def _tick(self):
        if not self._running:
            return
        self._frame += 1
        self._phase_t += 1
        self._draw()
        self._win.after(50, self._tick)

    def _draw(self):
        c = self._canvas
        c.delete("all")
        self._draw_bg(c)
        ex, ey = self.EGG_W // 2, self.EGG_H // 2 - 10

        if self._shake_f > 0:
            self._shake_f -= 1
            sx = int(math.sin(self._shake_f * 1.8) * self._shake_x)
        else:
            sx = int(math.sin(self._frame * 0.07) * 2)

        if self._phase in ("idle", "waiting"):
            self._draw_egg(c, ex + sx, ey)
            if self._cracks:
                self._draw_cracks(c, ex + sx, ey)

        elif self._phase == "explode":
            if self._phase_t >= 35:
                self._phase = "reveal"
                self._phase_t = 0
            self._tick_particles(c)

        elif self._phase == "reveal":
            self._tick_particles(c)
            alpha = min(1.0, self._phase_t / 20)
            if self._result:
                self._draw_result(c, alpha)
            if self._phase_t >= 28:
                self._phase = "done"
                self._show_claim()

    def _draw_bg(self, c):
        c.create_rectangle(0, 0, self.EGG_W, self.EGG_H, fill="#1A1B2E", outline="")
        for i, (sx, sy) in enumerate(_EGG_STARS):
            blink = (self._frame // 8 + i) % 20
            r = 1.5 if blink < 15 else 2.5
            c.create_oval(sx-r, sy-r, sx+r, sy+r, fill="white", outline="")

    def _draw_egg(self, c, ex, ey):
        t = self._egg
        scale = 1 + math.sin(self._frame * 0.07) * 0.025 + min(self._click_cnt / 25, 0.08)
        ew, eh = int(90 * scale), int(115 * scale)

        glow_c = f"#{t['glow']}"
        for gi in range(2 + self._click_cnt // 2):
            g = (gi + 1) * 5
            c.create_oval(ex-ew-g, ey-eh-g, ex+ew+g, ey+eh+g, fill="", outline=glow_c, width=1)

        c.create_oval(ex-ew, ey-eh, ex+ew, ey+eh,
                      fill=f"#{t['main']}", outline=f"#{t['pattern']}", width=3)
        random.seed(42)
        for _ in range(10):
            px, py = random.randint(-50, 50), random.randint(-70, 60)
            if (px/ew)**2 + (py/eh)**2 < 0.85:
                r = random.randint(5, 12)
                c.create_oval(ex+int(px*scale)-r, ey+int(py*scale)-r,
                              ex+int(px*scale)+r, ey+int(py*scale)+r,
                              fill=f"#{t['pattern']}", outline="")
        random.seed()
        c.create_oval(ex-int(ew*.45), ey-int(eh*.5), ex+int(ew*.1), ey+int(eh*.05),
                      fill="#FFFFFF", outline="", stipple="gray50")

    def _draw_cracks(self, c, ex, ey):
        for x1, y1, x2, y2 in self._cracks:
            c.create_line(ex+x1, ey+y1, ex+x2, ey+y2, fill="#1A1A2E", width=2)

    def _load_result_sprite(self):
        if not PIL_OK or not self._result: return
        folder = resource_path(os.path.join("assets", self._result, "idle"))
        if not os.path.isdir(folder): return
        pngs = sorted([f for f in os.listdir(folder) if f.lower().endswith(".png")], key=_nat_key)
        size = 130
        bg_col = (26, 27, 46, 255)
        for p in pngs:
            try:
                img = Image.open(os.path.join(folder, p)).convert("RGBA")
                bg  = Image.new("RGBA", img.size, bg_col)
                bg.paste(img, mask=img.split()[3])
                self._result_tk_frames.append(
                    ImageTk.PhotoImage(bg.convert("RGB").resize((size, size), Image.LANCZOS)))
            except Exception: pass

    def _draw_result(self, c, alpha):
        if not self._result or self._result not in GACHA_POOL:
            return
        info = GACHA_POOL[self._result]
        cx, cy = self.EGG_W // 2, self.EGG_H // 2
        g  = int(240 * alpha)
        wc = f"#{g:02x}{g:02x}{min(255,g+15):02x}"
        rh = info["rarity_color"]
        rc = (f"#{int(int(rh[0:2],16)*alpha):02x}"
              f"{int(int(rh[2:4],16)*alpha):02x}"
              f"{int(int(rh[4:6],16)*alpha):02x}")
        # 真實角色圖片
        if self._result_tk_frames:
            fidx = (self._phase_t // 5) % len(self._result_tk_frames)
            c.create_image(cx, cy - 10, image=self._result_tk_frames[fidx], anchor="center")
        else:
            c.create_text(cx, cy - 52, text="✨", font=("Segoe UI Emoji", 32), fill=wc)
        # 角色名稱、稀有度、描述
        c.create_text(cx, cy + 48, text=info["name"],
                      font=("Microsoft JhengHei", 20, "bold"), fill=wc)
        c.create_text(cx, cy + 74, text=f"【{info['rarity']}】",
                      font=("Microsoft JhengHei", 13, "bold"), fill=rc)
        c.create_text(cx, cy + 98, text=info["desc"],
                      font=("Microsoft JhengHei", 10), fill=wc)

    def _gen_explosion(self, ex, ey):
        t = self._egg
        colors = [f"#{t['main']}", f"#{t['pattern']}", "#FFFFFF", "#FFD700", "#FF6B8A"]
        self._particles = [{
            "x": ex+random.randint(-20,20), "y": ey+random.randint(-20,20),
            "dx": math.cos(a:=random.uniform(0, math.pi*2)) * (s:=random.uniform(3,12)),
            "dy": math.sin(a) * s - 3,
            "color": random.choice(colors),
            "size": random.randint(4,14),
            "life": 0, "max_life": random.randint(25,50),
        } for _ in range(60)]

    def _tick_particles(self, c):
        alive = []
        for p in self._particles:
            p["x"] += p["dx"]; p["y"] += p["dy"]
            p["dy"] += 0.2; p["life"] += 1
            if p["life"] >= p["max_life"]: continue
            alive.append(p)
            a = 1 - p["life"] / p["max_life"]
            r = max(1, int(p["size"] * a))
            x, y = int(p["x"]), int(p["y"])
            c.create_oval(x-r, y-r, x+r, y+r, fill=p["color"], outline="")
        self._particles = alive

    def _show_claim(self):
        if not self._result: return
        info = GACHA_POOL[self._result]
        self._claim_btn.config(text=f"✨ 確認領取「{info['name']}」！")
        self._claim_btn.pack(pady=8)
        self._status_var.set("")

    def _claim(self):
        self._running = False
        char_id, pet_name = self._result, self._pet_name
        try: self._win.destroy()
        except Exception: pass
        if char_id:
            self._on_complete(char_id, pet_name)


# ── 放生告別畫面 ─────────────────────────────────────────────

FAREWELL_LINES = [
    "你走近 {name}，輕聲說：「是時候讓你自由了...」",
    "{name} 抬起頭，用溫柔的眼神凝視著你。",
    "牠輕輕地蹭了蹭你的手，好像在道謝。",
    "然後，緩緩轉身，朝著遠方邁出第一步。",
    "「{name}——」你忍不住輕喚了一聲。",
    "牠停下腳步，回頭對你眨了眨眼，微微笑了。",
    "轉身，踏入那片閃著金光的廣闊草原...",
    "感謝你曾給予的每一份愛與陪伴。\n再見了，{name}。願你自由快樂。 💕",
]


class FarewellScreen:
    """放生告別動畫（Toplevel）。
    日落天空場景 + chibi 角色漸遠 + 打字機台詞卡片。
    callback: on_complete(char_id)
    """
    W, H     = 580, 680
    CVS_H    = 220
    CHARS_PER_FRAME = 3
    LINE_WAIT_FRAMES = 38
    WALK_START_LINE  = 3

    # 日落天空色帶（由上至下）
    _SKY = ["#0B0C1A","#131530","#1E1850","#3A1F5C",
            "#5C2358","#8B3050","#B5402A","#D45E20","#E88030"]
    # 草地色帶
    _GRASS = ["#0A2014","#0D2A1A","#112E1E","#153524","#1A3D28"]

    def __init__(self, root: tk.Tk, char_name: str, char_id: str,
                 char_color: str, on_complete):
        self._root        = root
        self._name        = char_name
        self._char_id     = char_id
        self._color       = f"#{char_color}"
        self._on_complete = on_complete

        self._frame    = 0
        self._running  = True
        self._line_idx = 0
        self._reveal   = 0.0
        self._wait     = 0
        self._pet_x    = float(self.W // 2)
        self._walking  = False
        self._done_txt = False
        self._footprints: list = []

        # 隨機星星位置（只用在放生場景，不重用 _EGG_STARS 避免混用）
        self._stars = [(random.randint(0, self.W), random.randint(0, int(self.CVS_H * 0.55)))
                       for _ in range(45)]

        # 預載真實角色 sprite（10 個縮放尺寸）
        self._sprite_frames: list = []  # [scale_idx][frame_idx] = ImageTk.PhotoImage
        self._sprite_sizes:  list = []  # [scale_idx] = float
        self._load_sprites(char_id)

        self._build()
        self._tick()

    # ── UI 建構 ─────────────────────────────────────────────────

    def _build(self):
        win = self._win = tk.Toplevel(self._root)
        win.title("放生告別")
        win.resizable(False, False)
        win.configure(bg="#0B0C1A")
        win.wm_attributes("-topmost", True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

        # 頂部標題
        hdr = tk.Frame(win, bg="#0B0C1A")
        hdr.pack(fill="x", padx=24, pady=(16, 4))
        tk.Label(hdr, text="⛩️  放生告別", bg="#0B0C1A", fg="#FFD580",
                 font=("Microsoft JhengHei", 17, "bold"), anchor="w").pack(side="left")
        tk.Button(hdr, text="略過 ▶▶", bg="#1A1A30", fg="#666",
                  relief="flat", font=("Arial", 9), cursor="hand2",
                  command=self._skip).pack(side="right", padx=4)
        tk.Label(hdr, text=f"「{self._name}」的旅程", bg="#0B0C1A",
                 fg="#AA8855", font=("Microsoft JhengHei", 11), anchor="e").pack(side="right")

        # 場景畫布
        self._cvs = tk.Canvas(win, width=self.W, height=self.CVS_H,
                               bg="#0B0C1A", highlightthickness=0)
        self._cvs.pack()

        # 分隔線
        sep = tk.Frame(win, height=1, bg="#2A2040")
        sep.pack(fill="x", padx=0)

        # 台詞卡片區
        card = tk.Frame(win, bg="#12112A")
        card.pack(fill="both", expand=True, padx=0)

        # 建立 8 個 Label 預留位，每行一個
        self._line_lbls: list[tk.Label] = []
        for _ in range(len(FAREWELL_LINES)):
            lbl = tk.Label(card, text="", bg="#12112A",
                           fg="#C8C8E8", wraplength=self.W - 48,
                           font=("Microsoft JhengHei", 11),
                           anchor="w", justify="left", padx=24, pady=3)
            lbl.pack(fill="x")
            self._line_lbls.append(lbl)

        # 底部送別按鈕（劇情結束後才 pack）
        self._bye_btn = tk.Button(
            win, text="✨  送別，一路好走  ✨",
            font=("Microsoft JhengHei", 13, "bold"),
            bg="#C87020", fg="#FFF8E1",
            activebackground="#E89030", activeforeground="#FFFFFF",
            relief="flat", padx=28, pady=12, cursor="hand2",
            command=self._finish
        )

    # ── Sprite 預載 ─────────────────────────────────────────────

    def _load_sprites(self, char_id: str):
        if not PIL_OK: return
        if char_id == "default":
            folder = resource_path(os.path.join("assets", "idle"))
        else:
            folder = resource_path(os.path.join("assets", char_id, "idle"))
        if not os.path.isdir(folder): return
        pngs = sorted([f for f in os.listdir(folder) if f.lower().endswith(".png")],
                      key=_nat_key)
        if not pngs: return
        try:
            raw = [Image.open(os.path.join(folder, p)).convert("RGBA") for p in pngs]
        except Exception as e:
            print(f"[Farewell] sprite 載入失敗: {e}"); return
        for scale in [1.0, 0.85, 0.70, 0.55, 0.42, 0.30, 0.22, 0.16, 0.12, 0.08]:
            size = max(8, int(80 * scale))
            try:
                self._sprite_frames.append([
                    ImageTk.PhotoImage(r.resize((size, size), Image.LANCZOS)) for r in raw
                ])
                self._sprite_sizes.append(scale)
            except Exception:
                pass

    def _draw_sprite(self, c, px: int, py: int, scale: float, frame_idx: int):
        if not self._sprite_frames:
            self._draw_chibi(c, px, py, scale)
            return
        si = min(range(len(self._sprite_sizes)),
                 key=lambda i: abs(self._sprite_sizes[i] - scale))
        frames = self._sprite_frames[si]
        c.create_image(px, py, image=frames[frame_idx % len(frames)], anchor="s")

    def _skip(self):
        self._running = False
        char_id = self._char_id
        try: self._win.destroy()
        except Exception: pass
        self._on_complete(char_id)

    # ── 動畫主迴圈 ──────────────────────────────────────────────

    def _tick(self):
        if not self._running: return
        self._frame += 1
        self._draw_scene()
        self._update_text()
        self._win.after(50, self._tick)

    # ── 場景繪製 ─────────────────────────────────────────────────

    def _draw_scene(self):
        c = self._cvs
        c.delete("all")
        W, H = self.W, self.CVS_H
        sky_n   = len(self._SKY)
        grass_n = len(self._GRASS)
        ground_y = int(H * 0.62)

        # 天空色帶
        for i, col in enumerate(self._SKY):
            y0 = int(i * ground_y / sky_n)
            y1 = int((i+1) * ground_y / sky_n)
            c.create_rectangle(0, y0, W, y1, fill=col, outline="")

        # 草地色帶
        for i, col in enumerate(self._GRASS):
            y0 = ground_y + int(i * (H - ground_y) / grass_n)
            y1 = ground_y + int((i+1) * (H - ground_y) / grass_n)
            c.create_rectangle(0, y0, W, y1, fill=col, outline="")

        # 地平線橙光
        for g in range(6):
            gy = ground_y - g * 4
            bright = ["#FF9020","#E07818","#C05C10","#A04408","#803408","#602C06"][g]
            c.create_rectangle(0, gy, W, gy+4, fill=bright, outline="")

        # 遠山剪影
        pts = [0, ground_y]
        for xi in range(0, W+1, 30):
            pts += [xi, ground_y - 18 - int(14 * math.sin(xi * 0.07))]
        pts += [W, ground_y]
        c.create_polygon(pts, fill="#0A1A0F", outline="")

        # 月亮
        mx, my = int(W * 0.83), 28
        c.create_oval(mx-16, my-16, mx+16, my+16, fill="#FFF5CC", outline="#FFE080", width=1)
        c.create_oval(mx-10, my-18, mx+8, my+18, fill=self._SKY[1], outline="")

        # 星星（閃爍）
        for i, (sx, sy) in enumerate(self._stars):
            blink = (self._frame // 10 + i) % 18
            if sy > ground_y * 0.8: continue
            r = 2.0 if blink < 14 else 1.0
            c.create_oval(sx-r, sy-r, sx+r, sy+r, fill="#FFFDE0", outline="")

        # 小路（橢圓透視感）
        path_y = ground_y + 8
        c.create_oval(W//2 - 40, path_y, W//2 + 40, path_y + 8,
                      fill="#1E3A28", outline="#2A4A35", width=1)

        # 腳印（走路後留下）
        for fp in self._footprints:
            fx, fy, fa = fp
            fc_val = max(0, int(40 * fa))
            fc = f"#{fc_val:02x}{fc_val+10:02x}{fc_val:02x}"
            c.create_oval(fx-3, fy-2, fx+3, fy+2, fill=fc, outline="")

        # 角色主體
        px = int(self._pet_x)
        py = ground_y - 4
        progress = max(0.0, (px - self.W * 0.4) / (self.W * 0.6))
        scale = max(0.15, 1.0 - progress * 0.82)
        bob = int(math.sin(self._frame * 0.35) * 4 * scale) if self._walking else 0

        frame_idx = self._frame // 6
        self._draw_sprite(c, px, py + bob, scale, frame_idx)

        # 走路更新
        if self._walking and px < W + 60:
            self._pet_x += 1.8 * (0.5 + progress * 0.5)
            if self._frame % 12 == 0:
                fp_alpha = max(0.1, 1.0 - progress)
                self._footprints.append([px - 8, py + 4, fp_alpha])
            self._footprints = [[fx, fy, fa * 0.97] for fx, fy, fa in self._footprints
                                 if fa > 0.05]

    def _draw_chibi(self, c, px: int, py: int, scale: float):
        """繪製簡潔 chibi 角色：頭＋身體＋耳朵＋眼睛＋光澤。"""
        col  = self._color
        r_h  = int(20 * scale)   # 頭半徑
        r_b  = int(14 * scale)   # 身體半徑
        ey   = py - r_h * 2      # 頭頂

        # 陰影
        c.create_oval(px - r_b, py, px + r_b, py + int(5 * scale),
                      fill="#081008", outline="")

        # 身體
        c.create_oval(px - r_b, py - r_b * 2, px + r_b, py,
                      fill=col, outline="")

        # 頭
        c.create_oval(px - r_h, ey, px + r_h, ey + r_h * 2,
                      fill=col, outline="")

        # 耳朵
        er = max(3, int(8 * scale))
        c.create_oval(px - r_h + 2, ey - er + 2, px - r_h + 2 + er*2, ey + er + 2,
                      fill=col, outline="")
        c.create_oval(px + r_h - 2 - er*2, ey - er + 2, px + r_h - 2, ey + er + 2,
                      fill=col, outline="")

        # 眼睛
        if r_h >= 6:
            eo = max(2, int(6 * scale))
            er2 = max(2, int(4 * scale))
            for ex_off in (-eo, eo):
                c.create_oval(px + ex_off - er2, ey + r_h - er2 * 2,
                              px + ex_off + er2, ey + r_h + er2 * 2 - 4,
                              fill="white", outline="")
                dot = max(1, int(2 * scale))
                c.create_oval(px + ex_off - dot, ey + r_h - dot * 2 - 2,
                              px + ex_off + dot, ey + r_h + dot * 2 - 2,
                              fill="#222222", outline="")

        # 頭上光澤
        if r_h >= 8:
            c.create_oval(px - int(r_h * 0.4), ey + int(r_h * 0.2),
                          px,                   ey + int(r_h * 0.7),
                          fill="white", outline="", stipple="gray50")

    # ── 打字機文字 ───────────────────────────────────────────────

    def _update_text(self):
        if self._done_txt: return
        if self._line_idx >= len(FAREWELL_LINES):
            self._done_txt = True
            self._bye_btn.pack(side="bottom", pady=10)
            return

        if self._wait > 0:
            self._wait -= 1
            return

        line = FAREWELL_LINES[self._line_idx].format(name=self._name)
        self._reveal += self.CHARS_PER_FRAME
        shown = line[:int(self._reveal)]

        # 更新目前行
        lbl = self._line_lbls[self._line_idx]
        lbl.config(text=shown, fg="#FFFFFF", font=("Microsoft JhengHei", 11, "bold"))

        if int(self._reveal) >= len(line):
            # 目前行完成 → 降調
            lbl.config(fg="#8888AA", font=("Microsoft JhengHei", 11))
            # 最後一行特別保留亮色
            if self._line_idx == len(FAREWELL_LINES) - 1:
                lbl.config(fg="#FFD080", font=("Microsoft JhengHei", 11, "bold"))
            self._line_idx += 1
            self._reveal = 0.0
            self._wait = self.LINE_WAIT_FRAMES
            if self._line_idx >= self.WALK_START_LINE:
                self._walking = True

    # ── 完成 ─────────────────────────────────────────────────────

    def _finish(self):
        self._running = False
        char_id = self._char_id
        try: self._win.destroy()
        except Exception: pass
        self._on_complete(char_id)


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
        w.title("🛍️ 商店")
        w.config(bg=self.WIN_BG)
        w.resizable(False, False)

        # 標題
        hdr = tk.Frame(w, bg=self.HDR_BG, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛍️  商店", font=("Arial", 16, "bold"),
                 bg=self.HDR_BG, fg="white").pack()
        tk.Label(hdr, text="購買後存入背包，隨時使用！",
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
        tk.Label(hdr, text="📊 統計數據", font=("Arial", 14, "bold"),
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
        # 同時清除之前可能殘留的森林 Label
        win = self._frame.master
        for c in win.winfo_children():
            if getattr(c, "_forest_label", False):
                c.destroy()
        m  = self._ctrl.model
        s  = m.stats
        hp = m.happiness
        hpc = "#C62828" if hp < 30 else ("#F57F17" if hp < 60 else "#2E7D32")
        focus_min = s.get("focus_minutes", 0)
        focus_str = (f"{focus_min // 60} 小時 {focus_min % 60} 分"
                     if focus_min >= 60 else f"{focus_min} 分鐘")
        rows = [
            ("🎭", "角色名稱",  m.pet_name,                          "#37474F"),
            ("❤️", "目前心情",  f"{hp}%",                            hpc),
            ("💰", "目前金幣",  f"{m.coins} 枚",                     "#E65100"),
            ("🍅", "完成番茄鐘",f"{s['pomodoro_done']} 次",          "#37474F"),
            ("⏱️", "累積專注",  focus_str,                           "#1565C0"),
            ("📅", "今日番茄",  f"{s.get('today_count',0)} 次",      "#6A1B9A"),
            ("🔥", "連續天數",  f"{s.get('streak_days',0)} 天",      "#BF360C"),
            ("💰", "累計獲得",  f"{s['coins_earned']} 枚",           "#37474F"),
            ("🛍️", "累計消費", f"{s['coins_spent']} 枚",            "#37474F"),
            ("🎒", "使用道具",  f"{s.get('items_used',0)} 次",       "#37474F"),
            ("🗓️", "上次簽到",  m.last_checkin or "—",              "#37474F"),
        ]
        for i, (icon, lbl, val, vc) in enumerate(rows):
            tk.Label(self._frame, text=icon, font=("Arial", 13),
                     anchor="w").grid(row=i, column=0, pady=3, padx=(12, 4), sticky="w")
            tk.Label(self._frame, text=lbl, font=("Arial", 10),
                     fg="#555", anchor="w", width=12).grid(row=i, column=1, sticky="w")
            tk.Label(self._frame, text=val, font=("Arial", 10, "bold"),
                     fg=vc, anchor="w").grid(row=i, column=2, sticky="w", padx=(4, 12))
        # 森林視覺
        total = s.get("pomodoro_done", 0)
        level = min(total // 10, 3)
        tree  = ["🌱", "🌿", "🌳", "🌲"][level]
        trees = tree * min(total, 10)
        suffix = f"  ×{total}" if total > 10 else ""
        forest_text = (f"🌳 我的森林：{trees}{suffix}"
                       if total > 0 else "🌱 完成番茄鐘，開始種下第一棵樹！")
        sep = ttk.Separator(win)
        sep._forest_label = True
        sep.pack(fill="x", padx=12, pady=(6, 2))
        lbl_f = tk.Label(win, text=forest_text, font=("Arial", 11),
                         fg="#2E7D32", pady=6)
        lbl_f._forest_label = True
        lbl_f.pack()


# ── 待辦清單 ──────────────────────────────────────────────────

_PRIORITY_ICON   = {"high": "🔴", "medium": "🟡", "low": "🟢"}
_PRIORITY_LABEL  = {"high": "高", "medium": "中", "low": "低"}
_PRIO_COLORS     = {"high": "#E53935", "medium": "#FB8C00", "low": "#43A047"}
_CATEGORIES      = ["讀書", "工作", "運動", "生活", "其他"]
_CAT_ICONS       = {"讀書":"📚","工作":"💼","運動":"🏃","生活":"🏠","其他":"📌"}
_GROUP_LABELS    = {
    0: ("逾期",      "#E53935"),
    1: ("今天",      "#FB8C00"),
    2: ("明天",      "#1565C0"),
    3: ("本週",      "#555555"),
    4: ("之後",      "#777777"),
    5: ("無截止日期","#999999"),
}


def _fmt_due(due_str: str, now) -> tuple:
    """將 ISO 日期字串轉為 (顯示文字, 顏色) 的相對格式。"""
    from datetime import datetime as _dt
    try:
        dt    = _dt.fromisoformat(due_str)
        delta = (dt.date() - now.date()).days
        t_str = dt.strftime("%H:%M")
        if delta < -1: return f"逾期 {-delta} 天", "#E53935"
        if delta == -1: return f"昨天 {t_str}",    "#E53935"
        if delta == 0:  return f"今天 {t_str}",    "#FB8C00"
        if delta == 1:  return f"明天 {t_str}",    "#1565C0"
        if delta < 7:   return dt.strftime(f"%a {t_str}"), "#555"
        return dt.strftime(f"%m/%d {t_str}"), "#777"
    except Exception:
        return due_str, "#777"


def _todo_group(t: dict, today) -> int:
    """回傳任務所屬分組 key (0=逾期 … 5=無截止日期)。"""
    from datetime import datetime as _dt
    due = t.get("due_datetime", "")
    if not due: return 5
    try:
        delta = (_dt.fromisoformat(due).date() - today).days
        if delta < 0:  return 0
        if delta == 0: return 1
        if delta == 1: return 2
        if delta < 7:  return 3
        return 4
    except Exception:
        return 5


def _play_reminder_chime():
    """播放三音上行提示音（C5-E5-G5），背景執行緒，不阻塞主迴圈。"""
    def _run():
        try:
            for freq, dur in [(523, 120), (659, 120), (784, 250)]:
                winsound.Beep(freq, dur)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


class TodoEditDialog:
    """新增/編輯單一待辦事項的對話框。"""

    def __init__(self, master, ctrl, todo: dict = None, on_save=None):
        self._master      = master
        self._ctrl        = ctrl
        self._todo        = todo
        self._on_save     = on_save
        self._priority_var = None
        self._prio_btns   = {}
        self._build()

    def _build(self):
        from datetime import datetime as _dt
        is_edit = bool(self._todo)
        title   = "✏️ 編輯待辦" if is_edit else "📝 新增待辦"
        w = self._win = tk.Toplevel(self._master)
        w.title(title)
        w.resizable(True, False)
        w.grab_set()
        w.wm_attributes("-topmost", True)
        w.minsize(360, 0)

        # ── 標題 ─────────────────────────────────────────────
        hdr = tk.Frame(w, bg="#DB4035", pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=("Arial", 12, "bold"),
                 bg="#DB4035", fg="white").pack()

        # ── 表單主體 ──────────────────────────────────────────
        body = tk.Frame(w, padx=20, pady=12); body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        row = 0

        # 任務名稱
        tk.Label(body, text="任務名稱", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1
        self._text_var = tk.StringVar(value=self._todo["text"] if is_edit else "")
        tk.Entry(body, textvariable=self._text_var, font=("Arial", 11)).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(2, 10))
        row += 1

        # 優先程度（toggle buttons）
        tk.Label(body, text="優先程度", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1
        self._priority_var = tk.StringVar(
            value=self._todo["priority"] if is_edit else "medium")
        pf = tk.Frame(body); pf.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 10))

        def _select_prio(val):
            self._priority_var.set(val)
            for v, (b, c) in self._prio_btns.items():
                b.config(bg=c if v == val else "white",
                         fg="white" if v == val else c,
                         relief="solid" if v == val else "flat")

        for val, lbl, col in [("high", "● 高", "#E53935"),
                               ("medium", "● 中", "#FB8C00"),
                               ("low",  "● 低", "#43A047")]:
            btn = tk.Button(pf, text=lbl, font=("Arial", 9, "bold"),
                            relief="flat", bd=0, padx=12, pady=5,
                            bg="white", fg=col, cursor="hand2",
                            command=lambda v=val: _select_prio(v))
            btn.pack(side="left", padx=(0, 6))
            self._prio_btns[val] = (btn, col)
        _select_prio(self._priority_var.get())
        row += 1

        # 分類
        tk.Label(body, text="分類", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, sticky="w")
        self._cat_var = tk.StringVar(
            value=self._todo["category"] if is_edit else "其他")
        ttk.Combobox(body, textvariable=self._cat_var, values=_CATEGORIES,
                     state="readonly", width=12).grid(
            row=row, column=1, sticky="w", pady=(2, 10))
        row += 1

        ttk.Separator(body).grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        # 解析預設日期時間
        now = _dt.now()
        due = self._todo.get("due_datetime", "") if is_edit else ""
        try:
            ddt = _dt.fromisoformat(due) if due else now
        except Exception:
            ddt = now
        dy, dm, dd, dh, dmin = ddt.year, ddt.month, ddt.day, ddt.hour, ddt.minute

        # 到期日期 + 時間（同一行）
        tk.Label(body, text="到期時間", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1
        dt_frm = tk.Frame(body); dt_frm.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 10))

        self._year  = tk.Spinbox(dt_frm, from_=2024, to=2035, width=5, font=("Arial", 10))
        self._month = tk.Spinbox(dt_frm, from_=1, to=12,   width=3, font=("Arial", 10))
        self._day   = tk.Spinbox(dt_frm, from_=1, to=31,   width=3, font=("Arial", 10))
        self._hour  = tk.Spinbox(dt_frm, from_=0, to=23,   width=3, font=("Arial", 10), wrap=True)
        self._min   = tk.Spinbox(dt_frm, from_=0, to=59,   width=3, font=("Arial", 10), wrap=True)
        for sp, val in [(self._year, dy), (self._month, f"{dm:02d}"),
                        (self._day, f"{dd:02d}"), (self._hour, f"{dh:02d}"),
                        (self._min, f"{dmin:02d}")]:
            sp.delete(0, "end"); sp.insert(0, val)

        for widget, lbl in [(self._year,"年"),(self._month,"月"),(self._day,"日 "),
                            (self._hour,"時"),(self._min,"分")]:
            widget.pack(side="left")
            tk.Label(dt_frm, text=lbl, font=("Arial", 9), fg="#555").pack(side="left")
        row += 1

        # 提醒
        tk.Label(body, text="提醒", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1
        remind_val = self._todo.get("remind_minutes", 30) if is_edit else 30
        self._remind_en  = tk.BooleanVar(value=(remind_val > 0))
        self._remind_var = tk.IntVar(value=max(1, remind_val))
        rf = tk.Frame(body); rf.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 10))
        tk.Checkbutton(rf, text="到期前", variable=self._remind_en,
                       font=("Arial", 10)).pack(side="left")
        tk.Spinbox(rf, from_=1, to=1440, width=5, textvariable=self._remind_var,
                   font=("Arial", 10)).pack(side="left", padx=4)
        tk.Label(rf, text="分鐘提醒", font=("Arial", 10), fg="#555").pack(side="left")
        row += 1

        # 備註
        tk.Label(body, text="備註（選填）", font=("Arial", 9), fg="#888", anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1
        self._note_txt = tk.Text(body, height=2, font=("Arial", 10), relief="solid", bd=1)
        self._note_txt.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        if is_edit and self._todo.get("note"):
            self._note_txt.insert("1.0", self._todo["note"])
        row += 1

        # ── 按鈕列 ───────────────────────────────────────────
        ttk.Separator(w).pack(fill="x", padx=10, pady=4)
        btn_row = tk.Frame(w, pady=8); btn_row.pack()
        tk.Button(btn_row, text="取消", width=9, relief="flat",
                  bg="#78909C", fg="white", font=("Arial", 10),
                  command=w.destroy).pack(side="left", padx=8)
        tk.Button(btn_row, text="💾  儲存", width=10, relief="flat",
                  bg="#DB4035", fg="white", font=("Arial", 10, "bold"),
                  activebackground="#C0392B",
                  command=self._save).pack(side="left", padx=8)

    def _save(self):
        text = self._text_var.get().strip()
        if not text:
            tk.messagebox.showwarning("提示", "請輸入任務名稱", parent=self._win); return
        try:
            y  = int(self._year.get());  mo = int(self._month.get())
            d  = int(self._day.get());   h  = int(self._hour.get())
            mi = int(self._min.get())
            due_str = f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}"
        except Exception:
            due_str = ""
        remind   = self._remind_var.get() if self._remind_en.get() else 0
        note_txt = self._note_txt.get("1.0", "end").strip()

        if self._todo:
            # 編輯模式：直接 update（update_todo 接受任意 key-value）
            self._ctrl.model.update_todo(self._todo["id"],
                text=text,
                priority=self._priority_var.get(),
                category=self._cat_var.get(),
                due_datetime=due_str,
                remind_minutes=remind,
                reminded=False,
                note=note_txt)
        else:
            # 新增模式：使用正確的參數名（due= 不是 due_datetime=）
            self._ctrl.model.add_todo(
                text=text,
                priority=self._priority_var.get(),
                category=self._cat_var.get(),
                due=due_str,
                remind=remind,
                note=note_txt)
        try: self._win.destroy()
        except Exception: pass
        if self._on_save: self._on_save()


class TodoView:
    """待辦清單視窗 — Todoist 風格：分組顯示、左側色條、相對日期、快速新增。"""

    _FILTER_OPTS  = ["全部", "未完成", "今天", "已完成"]
    _PLACEHOLDER  = "＋ 輸入新任務，按 Enter 快速新增…"

    def __init__(self, master, ctrl):
        self._master      = master
        self._ctrl        = ctrl
        self._win         = None
        self._list_frame  = None
        self._filter_var  = None
        self._cvs         = None
        self._stat_lbl    = None
        self._quick_entry = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._refresh(); return
        self._build()

    # ── 建構 ────────────────────────────────────────────────────

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("📋 待辦清單")
        w.resizable(True, True)
        w.minsize(480, 420)

        # 全視窗 grid：只有 row=2（清單）可延伸
        w.columnconfigure(0, weight=1)
        w.rowconfigure(2, weight=1)

        # row=0：標題列
        hdr = tk.Frame(w, bg="#DB4035", pady=8)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        tk.Label(hdr, text="📋 待辦清單", font=("Arial", 13, "bold"),
                 bg="#DB4035", fg="white").pack(side="left", padx=14)
        tk.Button(hdr, text="＋ 新增任務", font=("Arial", 9, "bold"),
                  bg="#C0392B", fg="white", relief="flat", cursor="hand2",
                  activebackground="#A93226",
                  command=self._new_todo).pack(side="right", padx=10, pady=3)

        # row=1：篩選 Tab
        tab_frm = tk.Frame(w, bg="#FAFAFA", pady=0)
        tab_frm.grid(row=1, column=0, sticky="ew")
        self._filter_var = tk.StringVar(value="全部")
        for opt in self._FILTER_OPTS:
            tk.Radiobutton(tab_frm, text=f"  {opt}  ", variable=self._filter_var,
                           value=opt, bg="#FAFAFA", fg="#555",
                           font=("Arial", 10), indicatoron=False,
                           selectcolor="#DB4035", activeforeground="white",
                           relief="flat", padx=4, pady=6,
                           command=self._refresh).pack(side="left")
        tk.Frame(w, height=1, bg="#DDD").grid(row=1, column=0, sticky="sew")

        # 滾動清單（row=2，可延伸）
        container = tk.Frame(w, bg="white")
        container.grid(row=2, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._cvs = tk.Canvas(container, bg="white", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self._cvs.yview)
        self._list_frame = tk.Frame(self._cvs, bg="white")
        self._list_frame.bind("<Configure>",
            lambda e: self._cvs.configure(scrollregion=self._cvs.bbox("all")))
        self._cvs.create_window((0, 0), window=self._list_frame, anchor="nw")
        self._cvs.configure(yscrollcommand=sb.set)
        self._cvs.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self._cvs.bind("<MouseWheel>",
            lambda e: self._cvs.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        # 快速新增列（row=3，固定高度）
        qa_frm = tk.Frame(w, bg="#F5F5F5", pady=8)
        qa_frm.grid(row=3, column=0, sticky="ew")
        qa_frm.columnconfigure(0, weight=1)
        self._quick_entry = tk.Entry(qa_frm, font=("Arial", 11), fg="#AAA",
                                     bg="#F5F5F5", relief="flat", bd=0,
                                     insertbackground="#333")
        self._quick_entry.grid(row=0, column=0, sticky="ew", padx=14, ipady=5)
        self._quick_entry.insert(0, self._PLACEHOLDER)
        self._quick_entry.bind("<FocusIn>",  self._qa_clear)
        self._quick_entry.bind("<FocusOut>", self._qa_restore)
        self._quick_entry.bind("<Return>",   self._quick_add)
        tk.Frame(w, height=1, bg="#E0E0E0").grid(row=3, column=0, sticky="sew")

        # row=4：底部統計 + 清除
        bot = tk.Frame(w, pady=6)
        bot.grid(row=4, column=0, sticky="ew", padx=12)
        self._stat_lbl = tk.Label(bot, text="", font=("Arial", 10),
                                   fg="#888", anchor="w")
        self._stat_lbl.pack(side="left")
        tk.Button(bot, text="清除已完成", font=("Arial", 9), relief="flat",
                  fg="#E53935", bg="white",
                  command=self._clear_done).pack(side="right")

        # row=5：關閉按鈕
        tk.Button(w, text="關閉", width=10, relief="flat",
                  bg="#78909C", fg="white", font=("Arial", 10),
                  command=w.destroy).grid(row=5, column=0, pady=(2, 10))

        self._refresh()

    # ── 資料 / 篩選 ─────────────────────────────────────────────

    def _refresh(self):
        if not self._list_frame: return
        for c in self._list_frame.winfo_children(): c.destroy()
        from datetime import datetime as _dt
        now   = _dt.now()
        today = now.date()
        filt  = self._filter_var.get() if self._filter_var else "全部"
        todos = self._ctrl.model.todos

        def _sort_key(t):
            due = t.get("due_datetime", "")
            gk  = _todo_group(t, today)
            if due:
                try: return (gk, _dt.fromisoformat(due))
                except Exception: pass
            return (gk, _dt.max)

        if filt == "全部":
            self._render_grouped(sorted(todos, key=_sort_key), now, today, skip_done=False)
        elif filt == "未完成":
            items = [t for t in todos if not t["done"]]
            self._render_grouped(sorted(items, key=_sort_key), now, today, skip_done=False)
        elif filt == "今天":
            items = [t for t in sorted(todos, key=_sort_key)
                     if not t["done"] and t.get("due_datetime","") and
                     self._is_today_or_overdue(t, today)]
            if not items:
                tk.Label(self._list_frame, text="🎉  今天沒有待辦，好好休息！",
                         fg="#888", font=("Arial", 10), pady=20, bg="white").pack()
            else:
                for t in items: self._add_row(t, now, today)
        elif filt == "已完成":
            items = [t for t in todos if t["done"]]
            if not items:
                tk.Label(self._list_frame, text="尚未完成任何任務",
                         fg="#CCC", font=("Arial", 10), pady=20, bg="white").pack()
            else:
                for t in items: self._add_row(t, now, today)

        done_n = sum(1 for t in todos if t["done"])
        if self._stat_lbl:
            self._stat_lbl.config(text=f"✅ 已完成 {done_n} / 共 {len(todos)} 項")

    @staticmethod
    def _is_today_or_overdue(t: dict, today) -> bool:
        from datetime import datetime as _dt
        due = t.get("due_datetime", "")
        if not due: return False
        try: return _dt.fromisoformat(due).date() <= today
        except Exception: return False

    def _render_grouped(self, items, now, today, skip_done: bool):
        """依分組 key 顯示區段 header + 任務列。"""
        if not items:
            tk.Label(self._list_frame, text="✅  什麼都沒有，很棒！",
                     fg="#CCC", font=("Arial", 10), pady=20, bg="white").pack()
            return
        from itertools import groupby
        for gk, group in groupby(items, key=lambda t: _todo_group(t, today)):
            group_list = list(group)
            if skip_done and all(t["done"] for t in group_list): continue
            label, color = _GROUP_LABELS.get(gk, ("其他", "#888"))
            self._section_header(label, color)
            for t in group_list:
                self._add_row(t, now, today)

    def _section_header(self, label: str, color: str):
        frm = tk.Frame(self._list_frame, bg="#F8F8F8", pady=5)
        frm.pack(fill="x")
        tk.Frame(frm, width=4, bg=color, height=16).pack(side="left", fill="y", padx=(8, 6))
        tk.Label(frm, text=label, font=("Arial", 10, "bold"),
                 fg=color, bg="#F8F8F8", anchor="w").pack(side="left")

    # ── 任務列 ─────────────────────────────────────────────────

    def _add_row(self, t: dict, now, today):
        from datetime import datetime as _dt
        due_str = t.get("due_datetime", "")
        is_done = t["done"]
        prio    = t.get("priority", "medium")
        pcolor  = _PRIO_COLORS.get(prio, "#CCCCCC")

        # 背景（逾期略帶紅、今日略帶橙）
        bg = "white"
        if not is_done and due_str:
            try:
                d = _dt.fromisoformat(due_str)
                if d < now:              bg = "#FFF5F5"
                elif d.date() == today:  bg = "#FFFBF0"
            except Exception: pass

        row = tk.Frame(self._list_frame, bg=bg, pady=6)
        row.pack(fill="x", padx=2, pady=0)

        # 左側優先度色條
        tk.Frame(row, width=5, bg=pcolor).pack(side="left", fill="y")

        # 勾選
        var = tk.BooleanVar(value=is_done)
        def on_toggle(tid=t["id"]):
            self._ctrl.model.toggle_todo(tid); self._refresh()
        tk.Checkbutton(row, variable=var, command=on_toggle,
                       bg=bg, activebackground=bg).pack(side="left", padx=(6, 0))

        # 任務名稱
        txt_fg   = "#BBBBBB" if is_done else "#1A1A1A"
        txt_font = ("Arial", 11, "overstrike") if is_done else ("Arial", 11, "bold")
        tk.Label(row, text=t["text"], font=txt_font, fg=txt_fg,
                 bg=bg, anchor="w", width=18).pack(side="left", padx=6)

        # 相對日期
        if due_str and not is_done:
            disp, dfg = _fmt_due(due_str, now)
            tk.Label(row, text=disp, font=("Arial", 10),
                     fg=dfg, bg=bg).pack(side="left", padx=4)

        # 分類標籤
        cat = t.get("category", "")
        if cat and not is_done:
            tk.Label(row, text=f"{_CAT_ICONS.get(cat,'📌')} {cat}",
                     font=("Arial", 9), fg="#AAA", bg=bg).pack(side="left", padx=3)

        # 備註提示
        note = t.get("note", "")
        if note and not is_done:
            tk.Label(row, text="💬", font=("Arial", 8), fg="#CCC",
                     bg=bg).pack(side="left")

        # 操作按鈕
        def on_del(tid=t["id"]): self._ctrl.model.remove_todo(tid); self._refresh()
        def on_edit(td=t): self._edit_todo(td)
        tk.Button(row, text="🗑", font=("Arial", 8), relief="flat",
                  fg="#DDD", bg=bg, activeforeground="#E53935",
                  command=on_del).pack(side="right", padx=1)
        tk.Button(row, text="✏", font=("Arial", 8), relief="flat",
                  fg="#DDD", bg=bg, activeforeground="#1565C0",
                  command=on_edit).pack(side="right")

        # 分隔線
        tk.Frame(self._list_frame, height=1, bg="#F0F0F0").pack(fill="x", padx=12)

    # ── 動作 ────────────────────────────────────────────────────

    def _new_todo(self):
        TodoEditDialog(self._win, self._ctrl, todo=None, on_save=self._refresh)

    def _edit_todo(self, t: dict):
        TodoEditDialog(self._win, self._ctrl, todo=t, on_save=self._refresh)

    def _clear_done(self):
        done_ids = [t["id"] for t in self._ctrl.model.todos if t["done"]]
        for tid in done_ids:
            self._ctrl.model.remove_todo(tid)
        self._refresh()

    # ── 快速新增 ────────────────────────────────────────────────

    def _qa_clear(self, _=None):
        if self._quick_entry and self._quick_entry.get() == self._PLACEHOLDER:
            self._quick_entry.delete(0, "end")
            self._quick_entry.config(fg="#333")

    def _qa_restore(self, _=None):
        if self._quick_entry and not self._quick_entry.get():
            self._quick_entry.insert(0, self._PLACEHOLDER)
            self._quick_entry.config(fg="#AAA")

    def _quick_add(self, _=None):
        if not self._quick_entry: return
        text = self._quick_entry.get().strip()
        if not text or text == self._PLACEHOLDER: return
        self._ctrl.model.add_todo(text)
        self._quick_entry.delete(0, "end")
        self._quick_entry.config(fg="#AAA")
        self._quick_entry.insert(0, self._PLACEHOLDER)
        self._refresh()


# ── 音樂管理視窗 ──────────────────────────────────────────────

class MusicView:
    """音樂管理視窗：顯示播放清單，支援選播、刪除、匯入。"""

    def __init__(self, master, music):
        self._master = master
        self._music  = music
        self._win    = None
        self._list_frame = None

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); self._refresh(); return
        self._build()

    def _build(self):
        w = self._win = tk.Toplevel(self._master)
        w.title("🎵 音樂管理"); w.resizable(False, False)

        hdr = tk.Frame(w, bg="#1A237E", pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text="🎵 音樂管理", font=("Arial", 13, "bold"),
                 bg="#1A237E", fg="white").pack(side="left", padx=16)
        tk.Button(hdr, text="📂 匯入音樂", font=("Arial", 9),
                  bg="#3949AB", fg="white", relief="flat",
                  command=self._import).pack(side="right", padx=12, pady=2)

        ttk.Separator(w).pack(fill="x")
        frm = tk.Frame(w, padx=10, pady=6); frm.pack(fill="both", expand=True)
        self._list_frame = frm
        self._refresh()
        ttk.Separator(w).pack(fill="x", padx=10)

        ctrl = tk.Frame(w, pady=8); ctrl.pack()
        tk.Button(ctrl, text="▶  播放", bg="#43A047", fg="white",
                  relief="flat", padx=10,
                  command=lambda: self._music.play()).pack(side="left", padx=4)
        tk.Button(ctrl, text="⏹  停止", bg="#E53935", fg="white",
                  relief="flat", padx=10,
                  command=lambda: self._music.stop()).pack(side="left", padx=4)
        tk.Button(ctrl, text="關閉", bg="#78909C", fg="white",
                  relief="flat", padx=10,
                  command=w.destroy).pack(side="left", padx=4)

    def _refresh(self):
        if not self._list_frame: return
        for c in self._list_frame.winfo_children(): c.destroy()
        tracks = self._music.get_tracks()
        cur    = self._music.current_track_name
        if not tracks:
            tk.Label(self._list_frame, text="沒有音樂，請先匯入！",
                     fg="#888", font=("Arial", 10), pady=12).pack()
            return
        for i, name in enumerate(tracks):
            row = tk.Frame(self._list_frame); row.pack(fill="x", pady=2)
            is_cur = (name == cur)
            icon = "▶  " if is_cur else "     "
            fg   = "#43A047" if is_cur else "#222"
            tk.Label(row, text=f"{icon}{i+1:02d}. {name}",
                     font=("Arial", 10, "bold" if is_cur else "normal"),
                     fg=fg, anchor="w", width=34).pack(side="left")
            tk.Button(row, text="播放", font=("Arial", 8), relief="flat",
                      bg="#1565C0", fg="white",
                      command=lambda idx=i: self._play(idx)).pack(side="left", padx=2)
            tk.Button(row, text="🗑", font=("Arial", 9), relief="flat",
                      fg="#C62828",
                      command=lambda idx=i: self._delete(idx)).pack(side="left")

    def _play(self, idx: int):
        self._music.play_index(idx); self._refresh()

    def _delete(self, idx: int):
        tracks = self._music.get_tracks()
        if idx >= len(tracks): return
        if not tk.messagebox.askyesno("確認刪除",
                f"確定要從磁碟刪除「{tracks[idx]}」？",
                parent=self._win): return
        self._music.delete_track(idx); self._refresh()

    def _import(self):
        from tkinter import filedialog
        fpath = filedialog.askopenfilename(
            title="選擇音樂檔案",
            filetypes=[("音樂", "*.mp3 *.ogg *.wav"), ("所有", "*.*")],
            parent=self._win)
        if not fpath: return
        dest = resource_path(os.path.join("assets", "music", os.path.basename(fpath)))
        try:
            shutil.copy2(fpath, dest)
        except Exception as e:
            tk.messagebox.showerror("匯入失敗", str(e), parent=self._win); return
        self._music._scan_tracks(); self._refresh()


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
        w.title("⚙️ 設定"); w.resizable(False, False)

        hdr = tk.Frame(w, bg="#F3E5F5", pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙️ 設定", font=("Arial",14,"bold"),
                 bg="#F3E5F5", fg="#4A148C").pack()

        ttk.Separator(w).pack(fill="x", padx=12, pady=8)
        g = tk.Frame(w, padx=24); g.pack()
        cfg = self._ctrl.model.settings
        row = 0

        # 寵物名稱
        tk.Label(g, text="🎭 角色名稱", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        self._name = tk.StringVar(value=self._ctrl.model.pet_name)
        tk.Entry(g, textvariable=self._name, width=14, font=("Arial",10)
                 ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        # ── 外觀角色 ──────────────────────────────────────────
        tk.Label(g, text="🎨 外觀角色", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=5)
        try:
            chars = _list_characters(unlocked_chars=self._ctrl.model.unlocked_chars)
            self._char_labels = [c[0] for c in chars]
            self._char_values = [c[1] for c in chars]
            cur = self._ctrl.model.settings.get("character", "default")
            try:    cur_idx = self._char_values.index(cur)
            except ValueError: cur_idx = 0
            self._char_var = tk.StringVar(value=self._char_labels[cur_idx])
            ttk.Combobox(g, textvariable=self._char_var,
                         values=self._char_labels, state="readonly", width=12
                         ).grid(row=row, column=1, sticky="w", padx=10)
        except Exception as e:
            print(f"[Settings] 角色掃描失敗：{e}")
            self._char_labels = ["預設"]
            self._char_values = ["default"]
            self._char_var = tk.StringVar(value="預設")
            tk.Label(g, text="（無法掃描）", font=("Arial", 9),
                     fg="#aaa").grid(row=row, column=1, sticky="w", padx=10)
        row += 1

        # ── 番茄鐘時間 ─────────────────────────────────────────
        tk.Label(g, text="🍅 工作時間（分）", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._work = tk.IntVar(value=cfg["work_min"])
        tk.Spinbox(g, from_=1, to=120, textvariable=self._work,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="😴 短休息（分）", font=("Arial",10), anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=4)
        self._rest = tk.IntVar(value=cfg["rest_min"])
        tk.Spinbox(g, from_=1, to=60, textvariable=self._rest,
                   width=6, font=("Arial",10)
                   ).grid(row=row, column=1, sticky="w", padx=10); row+=1

        tk.Label(g, text="🌙  長休息（分）", font=("Arial",10), anchor="w"
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
        try:
            idx = self._char_labels.index(self._char_var.get())
            character = self._char_values[idx]
        except (ValueError, AttributeError):
            character = self._ctrl.model.settings.get("character", "default")
        self._ctrl.apply_settings(
            name                 = self._name.get().strip() or "小白",
            work_min             = max(1,  self._work.get()),
            rest_min             = max(1,  self._rest.get()),
            long_rest_min        = max(5,  self._long_rest.get()),
            sessions_before_long = max(2,  self._sessions_n.get()),
            auto_start           = self._auto_start.get(),
            topmost              = self._topmost.get(),
            character            = character,
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
        self._todo_v  = TodoView(self._root, ctrl)
        self._music_v = MusicView(self._root, ctrl._music)
        self._bind_events()
        self._animate()
        self._hp_loop()
        self._root.after(100, self._snap_to_bottom_right)

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
        pw = self._root.winfo_width()
        ph = self._root.winfo_height()
        if pw <= 1 or ph <= 1:
            self._root.after(150, self._snap_to_bottom_right)
            return
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(0, sw - pw - 20)
        y = max(0, sh - ph - 60)
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
        self._frame_i = 0

    def apply_window_settings(self, cfg: dict):
        self._root.wm_attributes("-topmost", cfg["always_on_top"])

    def open_shop(self):      self._shop_v.open()
    def open_backpack(self):  self._pack_v.open()
    def open_stats(self):     self._stats_v.open()
    def open_settings(self):  self._sett_v.open()
    def open_todos(self):     self._todo_v.open()
    def open_music(self):     self._music_v.open()

    def show_info(self, title: str, msg: str):
        _info_dialog(self._root, title, msg)

    def show_warn(self, title: str, msg: str):
        _warn_dialog(self._root, title, msg)

    def destroy(self):
        for aid in (self._anim_id, self._eat_id, self._hp_id):
            if aid: self._root.after_cancel(aid)
        self._speech.cancel()
        if self._ctrl:
            self._ctrl.close_popup()
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
        frames = self._cache.get(self._status, self._character)
        if frames:
            self._txt_lbl.grid_remove()
            self._img_lbl.grid(row=1, column=0)
            frame = frames[self._frame_i % len(frames)]
            self._img_lbl.config(image=frame)
            self._img_lbl.image = frame
            self._frame_i = (self._frame_i + 1) % len(frames)
        else:
            self._img_lbl.grid_remove()
            self._txt_lbl.grid(row=1, column=0)
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
        self._music           = MusicPlayer()
        self._popup           = _PopupMenu(root)
        self._status          = "idle"
        self._checkin_id      = None
        self._idle_chat_id    = None
        self._todo_idle_id    = None
        self._todo_check_id   = None
        self._todo_today_idx  = 0      # 今日待辦輪播指針
        self._eat_restore_id  = None

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
        self._schedule_todo_remind()
        self._schedule_todo_check()
        if self._model.first_launch:
            self._model.first_launch = False
            self._root.after(800, lambda: self._view.show_speech(
                "你好！我是帥潮教授 👋\n"
                "完成番茄鐘賺金幣 🍅\n"
                "存到 30 枚去商店買角色蛋 🥚", 8000))

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

        # 累積專注時間
        work_min = self._pomo._work_s // 60
        self._model.inc_stat("focus_minutes", work_min)

        # 今日番茄（跨日重置）
        today = date.today().isoformat()
        s = self._model.stats
        if s.get("today_date") != today:
            self._model.set_stat("today_count", 1)
            self._model.set_stat("today_date", today)
        else:
            self._model.inc_stat("today_count")

        # 連續天數
        last = s.get("last_focus_date", "")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if last == today:
            pass
        elif last == yesterday:
            self._model.inc_stat("streak_days")
        else:
            self._model.set_stat("streak_days", 1)
        self._model.set_stat("last_focus_date", today)

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
            prev_status = self._status
            self._status = "eating"
            self._view.trigger_eating(prev_status)
            self._view.show_speech(random.choice(DIALOGUES["eating"]), 3000)
            if self._eat_restore_id:
                self._root.after_cancel(self._eat_restore_id)
            def _restore(s=prev_status):
                if self._status == "eating":
                    self._status = s
            self._eat_restore_id = self._root.after(EATING_MS, _restore)
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
        elif item_id == "egg":
            self._show_egg_screen()

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

    def switch_character(self, character: str):
        """輕量角色切換，只更新角色設定、不動其他參數。"""
        self._model.patch_settings(character=character)
        self._view.update_character(character)

    # ── 右鍵選單 ──────────────────────────────────────────────

    def close_popup(self):
        self._popup.close_all()

    def _show_egg_screen(self):
        EggGachaScreen(self._root, on_complete=self._on_egg_hatched)

    def farewell_char(self, char_id: str):
        """觸發放生告別動畫。"""
        info = GACHA_POOL.get(char_id, {})
        FarewellScreen(
            self._root,
            char_name=info.get("name", char_id),
            char_id=char_id,
            char_color=info.get("egg_color", "888888"),
            on_complete=self._on_farewell_done,
        )

    def _on_farewell_done(self, char_id: str):
        if self._model.settings.get("character") == char_id:
            self.switch_character("default")
        self._model.remove_unlocked_char(char_id)
        self._model.sync_save()
        info = GACHA_POOL.get(char_id, {})
        self._view.show_info("⛩️ 放生", f"「{info.get('name', char_id)}」已自由啟程。\n感謝你的陪伴。")

    def _import_character(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="選擇角色素材資料夾（含 idle/ 等子目錄）")
        if not folder: return
        char_id = os.path.basename(folder)
        dest = resource_path(os.path.join("assets", char_id))
        try:
            shutil.copytree(folder, dest, dirs_exist_ok=True)
        except Exception as e:
            self._view.show_speech(f"❌ 匯入失敗：{e}", 5000); return
        cfg_path = resource_path(os.path.join("assets", "characters.json"))
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cmap = json.load(f)
        except Exception:
            cmap = {}
        if char_id not in cmap:
            cmap[char_id] = char_id
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cmap, f, ensure_ascii=False, indent=2)
        self._view._cache.invalidate(char_id)
        self._view.show_speech(f"✨ 已匯入角色「{char_id}」！可在切換角色中選用。", 5000)

    def _import_music(self):
        from tkinter import filedialog
        fpath = filedialog.askopenfilename(
            title="選擇音樂檔案",
            filetypes=[("音樂檔案", "*.mp3 *.ogg *.wav"), ("所有檔案", "*.*")])
        if not fpath: return
        fname = os.path.basename(fpath)
        dest  = resource_path(os.path.join("assets", "music", fname))
        try:
            shutil.copy2(fpath, dest)
        except Exception as e:
            self._view.show_speech(f"❌ 匯入失敗：{e}", 5000); return
        self._music._scan_tracks()
        self._view.show_speech(f"🎵 已匯入「{fname}」！", 4000)

    def _on_egg_hatched(self, char_id: str, pet_name: str):
        if pet_name:
            self._model.pet_name = pet_name
        self._model.add_unlocked_char(char_id)
        self._model.first_launch = False
        self._model.sync_save()
        info = GACHA_POOL.get(char_id, {})
        self._view.refresh_info()
        self._view.show_info(
            "🥚 孵化成功！",
            f"恭喜！「{pet_name}」孵出了\n"
            f"【{info.get('rarity', '?')}】{info.get('name', char_id)}\n\n"
            f"{info.get('desc', '')}\n\n"
            f"已加入右鍵選單「切換角色」！"
        )

    def show_menu(self, event):
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return

        m   = self._model
        inv = m.inventory
        hp  = m.happiness
        hp_bar = "♥" * (hp // 25) + "♡" * (4 - hp // 25)
        warn   = "  ⚠ 心情過低！" if hp < 30 else ""
        bonus  = "  ⚡ 加倍符文" if m.bonus_mult > 1 else ""
        bag_n  = sum(v for v in inv.values() if v > 0)

        # ── 活動子選單 ────────────────────────────────────────
        state_subitems = [
            {"label": "  😴  發呆",   "cmd": self.do_idle},
            {"label": "  💻  寫程式", "cmd": self.do_coding},
            {"label": "  📚  讀書",   "cmd": self.do_studying},
            {"label": "  💤  睡覺",   "cmd": self.do_sleep},
        ]

        # ── 切換角色子選單 ────────────────────────────────────
        chars = _list_characters(unlocked_chars=self._model.unlocked_chars)
        cur_char = m.settings.get("character", "default")
        char_subitems = []
        for lbl, val in chars:
            indicator = "✓  " if val == cur_char else "    "
            char_subitems.append({
                "label": f"  {indicator}{lbl}",
                "cmd": lambda v=val: self.switch_character(v),
            })
            if val in GACHA_POOL:
                char_subitems.append({
                    "label": f"      ⛩️ 放生 {lbl}",
                    "cmd": lambda v=val: self.farewell_char(v),
                })
        char_subitems.append({"sep": True})
        char_subitems.append({"label": "  ➕  匯入角色素材", "cmd": self._import_character})

        # ── 快速餵食子選單 ────────────────────────────────────
        foods = [(iid, cnt) for iid, cnt in inv.items() if iid in FOOD_IDS and cnt > 0]
        food_subitems = []
        for iid, cnt in foods:
            food = FOOD_MAP[iid]
            food_subitems.append({
                "label": f"  {food['icon']} {food['name']} ×{cnt}（{food['desc']}）",
                "cmd": lambda i=iid: self.use_item(i),
            })
        if not food_subitems:
            food_subitems.append({"label": "  背包目前沒有食物", "disabled": True})

        # ── 番茄鐘子選單 ─────────────────────────────────────
        phase = self._pomo.phase
        sd, sn = self._pomo.session_done, self._pomo.sessions_n
        pomo_status = {
            "work":      f"▸ 工作中  第 {sd+1}/{sn} 節",
            "rest":      f"▸ 休息中（{sd}/{sn} 節完成）",
            "long_rest": "▸ 大休息中",
        }.get(phase, "")
        pomo_subitems = [
            {"label": pomo_status, "disabled": True, "font": ("Segoe UI", 9)},
            {"label": "  ⏸️  暫停" if self._pomo.running else "  ▶️  開始",
             "cmd": self.toggle_pomo},
            {"label": "  🔁  重設全部", "cmd": self.reset_pomo},
            {"sep": True},
            {"label": "  🍅  經典   25 / 5 / 15 分",
             "cmd": lambda: self._apply_preset(25, 5, 15, 4)},
            {"label": "  💪  雙倍   50 / 10 / 30 分",
             "cmd": lambda: self._apply_preset(50, 10, 30, 4)},
            {"label": "  ⚡  迷你   15 / 3 / 10 分",
             "cmd": lambda: self._apply_preset(15, 3, 10, 4)},
            {"label": "  ⚙️  自訂時間…", "cmd": self._show_custom_dialog},
        ]

        # ── 音樂子選單 ────────────────────────────────────────
        music_subitems = [
            {"label": "  ▶️  播放",      "cmd": self._music.play},
            {"label": "  ⏹️  停止",      "cmd": self._music.stop},
            {"label": "  🔀  下一首",    "cmd": self._music.next},
            {"sep": True},
            {"label": "  🎵  音樂管理（選曲 / 刪除 / 匯入）",
             "cmd": self._view.open_music},
        ]

        # ── 主選單 ────────────────────────────────────────────
        items = [
            {"label": f"  🎭  {m.pet_name}",
             "disabled": True, "font": ("Segoe UI", 10, "bold")},
            {"label": f"     {hp_bar} {hp}%{warn}   💰 {m.coins} 枚{bonus}",
             "disabled": True, "font": ("Segoe UI", 9)},
            {"sep": True},
            {"label": "  🎭  角色狀態",  "items": state_subitems},
            {"label": "  🎨  切換角色",  "items": char_subitems},
            {"sep": True},
            {"label": "  🍅  番茄鐘",    "items": pomo_subitems},
            {"label": "  🍎  快速餵食",  "items": food_subitems},
            {"sep": True},
            {"label": "  🏪  商店",      "cmd": self._view.open_shop},
            {"label": f"  🎒  背包（{bag_n} 件）" if bag_n else "  🎒  背包（空）",
             "cmd": self._view.open_backpack},
            {"label": "  🎵  背景音樂",  "items": music_subitems},
            {"sep": True},
            {"label": "  📋  待辦清單",  "cmd": self._view.open_todos},
            {"label": "  📊  統計數據",  "cmd": self._view.open_stats},
            {"label": "  ⚙️  設定",      "cmd": self._view.open_settings},
            {"sep": True},
            {"label": "  ❌  結束程式",  "cmd": self._confirm_quit},
        ]

        self._popup.popup(event.x_root, event.y_root, items)

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
        remain = self._pomo.remaining_seconds
        total  = self._pomo.work_seconds
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

    def _schedule_todo_remind(self):
        self._cancel_todo_remind()
        self._todo_idle_id = self._root.after(_TODO_REMIND_MS, self._do_todo_remind)

    def _cancel_todo_remind(self):
        if self._todo_idle_id:
            self._root.after_cancel(self._todo_idle_id)
            self._todo_idle_id = None

    @staticmethod
    def _is_today_todo(t: dict, today) -> bool:
        from datetime import datetime as _dt
        due = t.get("due_datetime", "")
        if not due: return False
        try: return _dt.fromisoformat(due).date() <= today
        except Exception: return False

    def _do_todo_remind(self):
        from datetime import datetime as _dt, date
        self._todo_idle_id = None
        now   = _dt.now()
        today = date.today()

        # 今日（含逾期）未完成待辦 → 輪流顯示
        today_items = [t for t in self._model.todos
                       if not t["done"] and self._is_today_todo(t, today)]
        if today_items:
            idx = self._todo_today_idx % len(today_items)
            t   = today_items[idx]
            self._todo_today_idx += 1
            disp, _ = _fmt_due(t["due_datetime"], now)
            self._view.show_speech(f"📋 今日待辦：{t['text']}\n⏰ {disp}", 6000)
        else:
            # 無今日待辦 → 隨機提醒任一未完成
            pending = [t for t in self._model.todos if not t["done"]]
            if pending:
                t = random.choice(pending)
                self._view.show_speech(f"📋 別忘了：{t['text']}", 6000)
        self._schedule_todo_remind()

    def _schedule_todo_check(self):
        self._cancel_todo_check()
        self._todo_check_id = self._root.after(_TODO_CHECK_MS, self._do_todo_check)

    def _cancel_todo_check(self):
        if self._todo_check_id:
            self._root.after_cancel(self._todo_check_id)
            self._todo_check_id = None

    def _do_todo_check(self):
        from datetime import datetime as _dt
        self._todo_check_id = None
        now = _dt.now()
        for t in self._model.todos:
            if t.get("done") or t.get("reminded"): continue
            due_str = t.get("due_datetime", "")
            remind  = t.get("remind_minutes", 0)
            if not due_str or remind == 0: continue
            try:
                due  = _dt.fromisoformat(due_str)
                diff = (due - now).total_seconds() / 60
                if diff <= remind:
                    self._model.mark_reminded(t["id"])
                    msg = (f"⏰ 「{t['text']}」\n" +
                           (f"還有 {int(max(0,diff))} 分鐘到期！" if diff > 0 else "已到期！"))
                    _play_reminder_chime()
                    self._view.show_speech(msg, 7000)
            except Exception:
                pass
        self._schedule_todo_check()

    def _confirm_quit(self):
        win = tk.Toplevel(self._root)
        win.resizable(False, False)
        win.wm_attributes("-topmost", True)
        win.grab_set()

        hdr = tk.Frame(win, bg="#C0392B", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="❌  結束程式", font=("Segoe UI", 12, "bold"),
                 bg="#C0392B", fg="white", padx=14).pack(anchor="w")

        tk.Label(win, text="確定要結束程式嗎？",
                 font=("Segoe UI", 10), padx=24, pady=16).pack()

        bf = tk.Frame(win); bf.pack(pady=(0, 14))

        def _do_quit():
            win.destroy()
            self._quit()

        tk.Button(bf, text="  確定結束  ", font=("Segoe UI", 10, "bold"),
                  bg="#C0392B", fg="white", relief="flat", padx=8, pady=4,
                  command=_do_quit).pack(side="left", padx=8)
        tk.Button(bf, text="  取消  ", font=("Segoe UI", 10),
                  relief="flat", padx=8, pady=4,
                  command=win.destroy).pack(side="left", padx=8)

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        ww, wh = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{(sw - ww) // 2}+{(sh - wh) // 2}")

    def _quit(self):
        try: self._root.grab_release()
        except Exception: pass
        self._music.stop()
        self._pomo.pause()
        self._cancel_work_checkin()
        self._cancel_idle_chat()
        self._cancel_todo_remind()
        self._cancel_todo_check()
        if self._eat_restore_id:
            self._root.after_cancel(self._eat_restore_id)
            self._eat_restore_id = None
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
