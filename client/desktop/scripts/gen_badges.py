"""生成托盘未读角标图标（1-99）：铃铛 + 右上角红底白数字。

用法：python gen_badges.py   （依赖 Pillow）
产物：client/desktop/src-tauri/icons/badges/1.png .. 99.png（128x128）
"""
import os

from PIL import Image, ImageDraw, ImageFont

from gen_icons import draw_bell

RED = (245, 108, 108, 255)      # #f56c6c，与 WPF 托盘角标一致
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "src-tauri", "icons", "badges")
SIZE = 128
BADGE_R = 34                    # 角标圆半径
CENTER = (SIZE - BADGE_R - 6, BADGE_R + 6)


def font(sz):
    for path in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\seguisb.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, sz)
    return ImageFont.load_default(sz)


def main():
    os.makedirs(OUT, exist_ok=True)
    bell = draw_bell().resize((SIZE, SIZE), Image.LANCZOS)
    f2 = font(40)
    f1 = font(48)
    for n in range(1, 100):
        img = bell.copy()
        d = ImageDraw.Draw(img)
        cx, cy = CENTER
        d.ellipse((cx - BADGE_R, cy - BADGE_R, cx + BADGE_R, cy + BADGE_R), fill=RED)
        text = str(n)
        f = f2 if len(text) > 1 else f1
        w = d.textlength(text, font=f)
        bbox = d.textbbox((0, 0), text, font=f)
        h = bbox[3] - bbox[1]
        d.text((cx - w / 2, cy - h / 2 - bbox[1]), text, font=f, fill=(255, 255, 255, 255))
        img.save(os.path.join(OUT, f"{n}.png"))
    print("badges written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
