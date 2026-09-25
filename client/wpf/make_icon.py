"""生成客户端应用图标 app.ico：与网页端 favicon 同款铃铛（品牌蓝 #2f6fed）。

用法：python make_icon.py   （依赖 Pillow：pip install pillow）
产物：DingDong/Assets/app.ico（16/24/32/48/64/128/256 多尺寸，256 为 PNG 压缩帧）
"""
import os

from PIL import Image, ImageDraw

BLUE = (47, 111, 237, 255)      # #2f6fed，与网页 favicon 一致
S = 1024                        # 超采样绘制尺寸（缩小后自带抗锯齿）
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "DingDong", "Assets", "app.ico")


def draw_bell() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 铃盖（半圆）：viewBox 24 → 1024，圆心 (12, 8) 半径 6
    r = 6 / 24 * S
    cx, cy = S / 2, 8 / 24 * S + r
    d.pieslice((cx - r, cy - r, cx + r, cy + r), 180, 360, fill=BLUE)

    # 铃身裙摆：从铃盖两侧向下外扩至底边 y=15.5/24，底边宽 4..20/24
    top = cy                      # 铃盖圆心高度（=铃身侧边起点）
    side_bottom = (8 + 3.6) / 24 * S   # 侧边结束
    base_y = 15.5 / 24 * S
    half_span = 8 / 24 * S             # 底边半宽（x: 4..20 → ±8）
    d.polygon([
        (cx - r, top),
        (cx - r, side_bottom),
        (cx - half_span, base_y),
        (cx + half_span, base_y),
        (cx + r, side_bottom),
        (cx + r, top),
    ], fill=BLUE)

    # 铃锤（下半圆）：圆心 (12, 17) 半径 2.5
    r2 = 2.5 / 24 * S
    c2y = 17 / 24 * S
    d.pieslice((cx - r2, c2y - r2, cx + r2, c2y + r2), 0, 180, fill=BLUE)
    return img


def main():
    base = draw_bell().resize((256, 256), Image.LANCZOS)
    frames = [base.resize((s, s), Image.LANCZOS) for s in (16, 24, 32, 48, 64, 128)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base.save(OUT, format="ICO", append_images=frames)
    print("written:", OUT)


if __name__ == "__main__":
    main()
