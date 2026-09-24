# -*- coding: utf-8 -*-
"""锭类物品占位图标（256x256 透明底，PIL 程序化绘制）。

规划依据：Docs/UI/smelting-panel-plan-20260923.md 第 1 节——锭类图标本次沿用占位图，
正式渲染图属后续 `ue5-item-asset-workflow` 范围。风格对齐冷钢图标约定：
左上柔光、无烘焙文字/数量/状态、透明背景。

绘制内容：正视铸锭（梯形顶面 + 收分前立面 + 落地软影），
金属身份色：铁=中性钢灰，铜=红棕，银=亮银白，金=金黄。
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4          # 超采样倍数
SIZE = 256
CANVAS = SIZE * SS
OUT_DIR = r"D:\FPS3D\FPSGAME\Content\ColdSteelData\Icons"

# sRGB 身份色（顶面亮 / 立面上 / 立面下 / 描边）
METALS = {
    "ironIngot":   {"top": (172, 177, 184), "hi": (126, 131, 138), "lo": (64, 68, 74),   "rim": (36, 38, 42)},
    "copperIngot": {"top": (216, 156, 112), "hi": (176, 110, 70),  "lo": (100, 56, 32),  "rim": (56, 28, 14)},
    "silverIngot": {"top": (236, 240, 244), "hi": (198, 204, 211), "lo": (118, 124, 132), "rim": (60, 63, 68)},
    "goldIngot":   {"top": (246, 216, 130), "hi": (212, 168, 74),  "lo": (138, 100, 36),  "rim": (78, 54, 18)},
}


def geometry():
    cx = CANVAS * 0.5
    ty = CANVAS * 0.34          # 顶面后缘
    fy = CANVAS * 0.50          # 顶面前缘（折线）
    by = CANVAS * 0.72          # 底缘
    hb = CANVAS * 0.17          # 顶面后缘半宽
    hf = CANVAS * 0.27          # 顶面前缘半宽
    hbf = CANVAS * 0.235        # 底缘半宽（收分）
    top = [(cx - hb, ty), (cx + hb, ty), (cx + hf, fy), (cx - hf, fy)]
    face = [(cx - hf, fy), (cx + hf, fy), (cx + hbf, by), (cx - hbf, by)]
    return top, face


def shade_region(poly, c_top, c_bot, x_left_gain=0.06, streaks=None, seed=1.0):
    """多边形内做 垂直渐变(上亮下暗) × 水平柔光(左亮) × 可选拉丝条纹。"""
    xs_all = [p[0] for p in poly]
    ys_all = [p[1] for p in poly]
    x0, x1 = min(xs_all), max(xs_all)
    y0, y1 = min(ys_all), max(ys_all)
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    m = np.asarray(mask) > 8
    ys, xs = np.nonzero(m)
    arr = np.zeros((CANVAS, CANVAS, 4), dtype=np.uint8)
    if not len(ys):
        return Image.fromarray(arr, "RGBA")
    t = np.clip((ys - y0) / max(1.0, y1 - y0), 0.0, 1.0)
    ct = np.array(c_top, dtype=np.float32)
    cb = np.array(c_bot, dtype=np.float32)
    col = ct[None, :] * (1.0 - t[:, None]) + cb[None, :] * t[:, None]
    xn = (xs - x0) / max(1.0, x1 - x0)
    col *= (1.0 + x_left_gain) - (2.0 * x_left_gain) * xn[:, None]
    if streaks == "brush":      # 横向拉丝（沿 y 的低频明暗带）
        col *= 1.0 + 0.030 * np.sin(ys * 0.55 + seed) * np.sin(ys * 0.09 + 1.7)
    elif streaks == "sheen":    # 顶面斜向柔光带
        col *= 1.0 + 0.045 * np.sin((xs * 0.6 + ys * 0.9) * 0.05 + seed)
    arr[ys, xs, :3] = np.clip(col, 0, 255).astype(np.uint8)
    arr[ys, xs, 3] = 255
    return Image.fromarray(arr, "RGBA")


def draw_ingot(pal):
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, face = geometry()

    # 落地软影
    shadow = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    by = CANVAS * 0.72
    sd.ellipse((CANVAS * 0.5 - CANVAS * 0.26, by + CANVAS * 0.015,
                CANVAS * 0.5 + CANVAS * 0.26, by + CANVAS * 0.085),
               fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(CANVAS * 0.010))
    img.alpha_composite(shadow)

    # 顶面：整体亮一档 + 斜向柔光
    img.alpha_composite(shade_region(top, pal["top"],
                                     tuple(int(c * 0.86) for c in pal["top"]),
                                     x_left_gain=0.05, streaks="sheen"))
    # 前立面：上亮下暗 + 拉丝
    img.alpha_composite(shade_region(face, pal["hi"], pal["lo"],
                                     x_left_gain=0.07, streaks="brush"))

    # 轮廓与折线
    rim = pal["rim"] + (255,)
    outline = [top[0], top[1], face[1], face[2], face[3], top[3]]
    d.line(outline + [outline[0]], fill=rim, width=max(2, int(SS * 0.9)))
    d.line([top[3], top[2]], fill=pal["rim"] + (180,), width=max(2, int(SS * 0.8)))

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    receipt = []
    for name, pal in METALS.items():
        path = os.path.join(OUT_DIR, f"{name}.png")
        draw_ingot(pal).save(path)
        receipt.append({"id": name, "target": f"Content\\ColdSteelData\\Icons\\{name}.png",
                        "source": "generated: SourceAssets/SmeltingPanel20260923/make_ingot_icons.py",
                        "note": "占位图标（规划文档 20260923 第 1 节），正式渲染图后续按 ue5-item-asset-workflow 替换"})
        print("wrote", path)
    with open(os.path.join(os.path.dirname(__file__), "ingot-icons.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
