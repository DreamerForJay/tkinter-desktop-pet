"""
generate_sprites.py — 用 DALL-E 3 自動生成角色素材
=======================================================

使用方式：
  1. pip install openai pillow
  2. 設定 API Key（擇一）：
       set OPENAI_API_KEY=sk-...          (Windows CMD)
       $env:OPENAI_API_KEY="sk-..."      (PowerShell)
  3. python generate_sprites.py

生成結果：
  assets/{char_id}/{state}/0.png
  （共 5 角色 × 7 狀態 = 35 張圖）

注意：
  - DALL-E 3 standard 每張約 $0.04，35 張約 $1.40
  - 已存在的圖片會跳過（不重複扣費）
  - 可加 --chars cat,bunny 只生成特定角色
  - 去背採白色像素替換法，非完美去背，建議再用 remove.bg 精修
"""

import os
import sys
import argparse
import urllib.request
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    sys.exit("[錯誤] 請先安裝：pip install openai")

try:
    from PIL import Image
    import io
except ImportError:
    sys.exit("[錯誤] 請先安裝：pip install pillow")


# ── 角色描述 ────────────────────────────────────────────────────
CHAR_PROMPTS = {
    "cat":     "an adorable orange tabby kitten with big sparkly eyes and tiny paws",
    "bunny":   "a fluffy white rabbit with long floppy ears and pink nose",
    "penguin": "a round baby penguin with a tiny bow tie and black-and-white feathers",
    "fox":     "a cute red fox with a bushy tail, pointy ears, and bright eyes",
    "dragon":  "a tiny magical purple dragon with golden wing tips and emerald eyes",
}

STATE_PROMPTS = {
    "idle":     "sitting upright, relaxed and happy, looking forward with a gentle smile",
    "coding":   "typing on a tiny miniature laptop computer with focused expression",
    "studying": "reading a small book, wearing tiny round glasses, thoughtful expression",
    "eating":   "happily eating from a small bowl, cheeks puffed, eyes closed in delight",
    "drag":     "floating in midair, arms slightly spread, surprised happy expression",
    "alert":    "wide-eyed surprised look, small lightning bolt effect around it",
    "sleep":    "curled up sleeping peacefully, eyes closed, small zzz bubbles floating up",
}

STYLE_SUFFIX = (
    "chibi kawaii anime style, simple flat 2D illustration, "
    "pure white background, no shadow, no gradient background, "
    "cute pastel colors, clean outlines, full body visible"
)

OUTPUT_SIZE = 200   # 最終輸出圖片大小（像素）
BG_THRESHOLD = 210  # 白色判定閾值（0-255），越高去背越積極


# ── 工具函式 ────────────────────────────────────────────────────

def remove_white_bg(img: Image.Image) -> Image.Image:
    """把白色及接近白色的像素替換為透明。"""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > BG_THRESHOLD and g > BG_THRESHOLD and b > BG_THRESHOLD:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)


def download_image(url: str) -> Image.Image:
    """從 URL 下載圖片並回傳 PIL Image。"""
    with urllib.request.urlopen(url, timeout=30) as resp:
        return Image.open(io.BytesIO(resp.read()))


def generate_one(client: OpenAI, char_id: str, state: str, out_path: Path) -> bool:
    """呼叫 DALL-E 3 生成單張圖，儲存到 out_path。回傳是否成功。"""
    prompt = (
        f"{CHAR_PROMPTS[char_id]}, {STATE_PROMPTS[state]}, {STYLE_SUFFIX}"
    )
    print(f"  → 生成 {char_id}/{state} … ", end="", flush=True)

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        img = download_image(url)
        img = remove_white_bg(img)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_path), "PNG")
        print("✓")
        return True
    except Exception as e:
        print(f"✗ ({e})")
        return False


# ── 主程式 ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="用 DALL-E 3 生成角色素材")
    parser.add_argument("--chars", default="",
                        help="指定角色（逗號分隔），如 cat,bunny；預設全部")
    parser.add_argument("--states", default="",
                        help="指定狀態（逗號分隔），如 idle,coding；預設全部")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="跳過已存在的圖片（預設開啟）")
    parser.add_argument("--force", action="store_true",
                        help="強制重新生成，覆蓋已存在的圖片")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        sys.exit(
            "[錯誤] 未設定 OPENAI_API_KEY\n"
            "  Windows CMD:    set OPENAI_API_KEY=sk-...\n"
            "  PowerShell:     $env:OPENAI_API_KEY='sk-...'"
        )

    client = OpenAI(api_key=api_key)

    chars  = [c.strip() for c in args.chars.split(",") if c.strip()] or list(CHAR_PROMPTS)
    states = [s.strip() for s in args.states.split(",") if s.strip()] or list(STATE_PROMPTS)
    skip   = args.skip_existing and not args.force

    # assets/ 路徑（與本腳本同層）
    base = Path(__file__).parent / "assets"

    total = len(chars) * len(states)
    done  = 0
    skipped = 0
    failed  = 0

    print(f"\n🎨 開始生成素材（{len(chars)} 角色 × {len(states)} 狀態 = {total} 張）\n")

    for char_id in chars:
        if char_id not in CHAR_PROMPTS:
            print(f"[警告] 未知角色 '{char_id}'，跳過")
            continue
        print(f"【{CHAR_PROMPTS[char_id][:30]}…】")
        for state in states:
            if state not in STATE_PROMPTS:
                print(f"  [警告] 未知狀態 '{state}'，跳過")
                continue
            out = base / char_id / state / "0.png"
            if skip and out.exists():
                print(f"  → {char_id}/{state} 已存在，跳過")
                skipped += 1
                continue
            ok = generate_one(client, char_id, state, out)
            if ok:
                done += 1
            else:
                failed += 1
        print()

    print("=" * 48)
    print(f"完成：{done} 張  跳過：{skipped} 張  失敗：{failed} 張")
    print(f"素材儲存位置：{base}")
    if done > 0:
        print("\n✅ 重新啟動 desktop_pet.py，角色素材即生效！")


if __name__ == "__main__":
    main()
