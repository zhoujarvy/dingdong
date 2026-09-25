"""生成 Tauri 客户端全套应用图标：精确复刻网页 favicon 的铃铛 SVG 路径（#2f6fed）。

用法：python gen_icons.py   （依赖 Pillow；用 server/venv 或任意装有 Pillow 的 Python）
产物：client/desktop/src-tauri/icons/ 下的 png/ico/icns 全套

实现：内置迷你 SVG path 解析器（M/L/H/V/C/A/Z），曲线密采样为多边形后填充，
与 web/public/favicon.svg 像素级一致，不再用几何近似。
"""
import math
import os
import re

from PIL import Image, ImageDraw

BLUE = (47, 111, 237, 255)      # #2f6fed 品牌蓝
S = 1024                        # 超采样绘制尺寸（viewBox 24 → 1024）
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "src-tauri", "icons")

# 与 web/public/favicon.svg 完全一致的路径
FAVICON_PATHS = [
    "M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z",
    "M9.5 17a2.5 2.5 0 0 0 5 0z",
]

_TOKEN = re.compile(r"([MmLlHhVvCcAaZz])|(-?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)")


def _numbers(d: str):
    """按命令切分 SVG path，返回 [(cmd, [floats])]。"""
    out, cmd, nums = [], None, []
    for m in _TOKEN.finditer(d):
        if m.group(1):
            if cmd is not None:
                out.append((cmd, nums))
            cmd, nums = m.group(1), []
        else:
            nums.append(float(m.group(2)))
    if cmd is not None:
        out.append((cmd, nums))
    return out


def _arc_to_points(x, y, rx, ry, phi, large, sweep, x2, y2, n=64):
    """SVG 椭圆弧（终点参数化）→ 圆心参数化 → 采样点列表（不含起点）。"""
    if rx == 0 or ry == 0:
        return [(x2, y2)]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi % 360)
    cosp, sinp = math.cos(phi), math.sin(phi)
    dx, dy = (x - x2) / 2, (y - y2) / 2
    x1p = cosp * dx + sinp * dy
    y1p = -sinp * dx + cosp * dy
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    co = math.sqrt(max(num / den, 0.0)) * (-1 if large == sweep else 1)
    cxp = co * rx * y1p / ry
    cyp = -co * ry * x1p / rx
    cx = cosp * cxp - sinp * cyp + (x + x2) / 2
    cy = sinp * cxp + cosp * cyp + (y + y2) / 2

    def ang(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        len_ = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, dot / len_)))
        if ux * vy - uy * vx < 0:
            a = -a
        return a

    th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry,
              (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    return [
        (
            cx + rx * math.cos(th1 + dth * i / n) * cosp
            - ry * math.sin(th1 + dth * i / n) * sinp,
            cy + rx * math.cos(th1 + dth * i / n) * sinp
            + ry * math.sin(th1 + dth * i / n) * cosp,
        )
        for i in range(1, n + 1)
    ]


def _path_points(d: str, scale: float):
    """SVG path（相对/绝对命令）→ [(x,y)] 多边形顶点（viewBox 坐标 × scale）。"""
    pts, cur, start = [], (0.0, 0.0), (0.0, 0.0)
    prev_cmd = None
    for cmd, ns in _numbers(d):
        rel = cmd.islower()
        c = cmd.upper()
        i = 0
        if c == "M":
            while i + 1 < len(ns):
                x, y = ns[i], ns[i + 1]
                cur = (cur[0] + x, cur[1] + y) if rel else (x, y)
                if i == 0:
                    start = cur
                pts.append(cur)
                i += 2
                c = "L"  # 后续隐式线段
        elif c == "L":
            while i + 1 < len(ns):
                x, y = ns[i], ns[i + 1]
                cur = (cur[0] + x, cur[1] + y) if rel else (x, y)
                pts.append(cur)
                i += 2
        elif c == "H":
            for x in ns:
                cur = (cur[0] + x, cur[1]) if rel else (x, cur[1])
                pts.append(cur)
        elif c == "V":
            for y in ns:
                cur = (cur[0], cur[1] + y) if rel else (cur[0], y)
                pts.append(cur)
        elif c == "C":
            while i + 5 < len(ns):
                c1 = (cur[0] + ns[i], cur[1] + ns[i + 1]) if rel else (ns[i], ns[i + 1])
                c2 = (cur[0] + ns[i + 2], cur[1] + ns[i + 3]) if rel else (ns[i + 2], ns[i + 3])
                end = (cur[0] + ns[i + 4], cur[1] + ns[i + 5]) if rel else (ns[i + 4], ns[i + 5])
                for k in range(1, 33):  # 贝塞尔 32 段采样
                    t = k / 32
                    mt = 1 - t
                    px = mt ** 3 * cur[0] + 3 * mt ** 2 * t * c1[0] + 3 * mt * t ** 2 * c2[0] + t ** 3 * end[0]
                    py = mt ** 3 * cur[1] + 3 * mt ** 2 * t * c1[1] + 3 * mt * t ** 2 * c2[1] + t ** 3 * end[1]
                    pts.append((px, py))
                cur = end
                i += 6
        elif c == "A":
            while i + 6 < len(ns):
                rx, ry, phi, large, sweep = ns[i], ns[i + 1], ns[i + 2], ns[i + 3], ns[i + 4]
                x, y = ns[i + 5], ns[i + 6]
                end = (cur[0] + x, cur[1] + y) if rel else (x, y)
                pts.extend(_arc_to_points(cur[0], cur[1], rx, ry, phi, large, sweep, *end))
                cur = end
                i += 7
        elif c == "Z":
            cur = start
        prev_cmd = cmd
    return [(x * scale, y * scale) for x, y in pts]


def draw_bell() -> Image.Image:
    """渲染 favicon 铃铛（超采样抗锯齿）。"""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for path in FAVICON_PATHS:
        d.polygon(_path_points(path, S / 24.0), fill=BLUE)
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
