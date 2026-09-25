"""生成 Tauri 客户端全套应用图标：与网页 favicon / WPF 客户端同款铃铛（#2f6fed）。

用法：python gen_icons.py   （依赖 Pillow；用 server/venv 或任意装有 Pillow 的 Python）
产物：client/desktop/src-tauri/icons/ 下的 png/ico/icns 全套
"""
import os

from PIL import Image, ImageDraw

BLUE = (47, 111, 237, 255)      # #2f6fed 品牌蓝
S = 1024                        # 超采样绘制尺寸
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "src-tauri", "icons")


def draw_bell() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    r = 6 / 24 * S
    cx, cy = S / 2, 8 / 24 * S + r
    d.pieslice((cx - r, cy - r, cx + r, cy + r), 180, 360, fill=BLUE)

    top = cy
    side_bottom = (8 + 3.6) / 24 * S
    base_y = 15.5 / 24 * S
    half_span = 8 / 24 * S
    d.polygon([
        (cx - r, top),
        (cx - r, side_bottom),
        (cx - half_span, base_y),
        (cx + half_span, base_y),
        (cx + r, side_bottom),
        (cx + r, top),
    ], fill=BLUE)

    r2 = 2.5 / 24 * S
    c2y = 17 / 24 * S
    d.pieslice((cx - r2, c2y - r2, cx + r2, c2y + r2), 0, 180, fill=BLUE)
    return img


def main():
    base = draw_bell()
    os.makedirs(OUT, exist_ok=True)

    def png(size, name):
        base.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, name))

    png(512, "icon.png")
    png(256, "128x128@2x.png")
    png(128, "128x128.png")
    png(32, "32x32.png")
    # Windows Store 方块图标（msi 打包需要）
    for n in (30, 44, 71, 89, 107, 142, 150, 284, 310):
        png(n, f"Square{n}x{n}Logo.png")
    png(50, "StoreLogo.png")

    # ico：多尺寸
    big = base.resize((256, 256), Image.LANCZOS)
    big.save(os.path.join(OUT, "icon.ico"), format="ICO",
             append_images=[big.resize((s, s), Image.LANCZOS) for s in (16, 24, 32, 48, 64)])
    # icns：Pillow 原生支持
    big.save(os.path.join(OUT, "icon.icns"), format="ICNS")
    print("icons written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
