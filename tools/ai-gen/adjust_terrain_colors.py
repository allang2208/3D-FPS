"""地形贴图色彩校正：把 AmbientCG 偏黄的草地校正成参考图质感的自然绿。

背景：实例参考图地面是"低饱和自然绿+棕色泥土"，而我们直接用的 grass001
偏黄（渲染 hue≈70，yellow 35-52%）。此脚本对指定贴图做 HSV 色相偏移，
并保留 RGBA 的 alpha（Terrain3D 高度/粗糙度通道），避免破坏已修复的 alpha。

用法：
    python tools/ai-gen/adjust_terrain_colors.py            # 默认校正 grass001
    python tools/ai-gen/adjust_terrain_colors.py --all      # 四张贴图一起调

参数（grass001 实测值，参考图 hue≈102-144 / green 26-59%）：
    --hue 30   色相 +30°（黄 -> 绿）
    --sat 1.15 饱和度 +15%
    --val 0.88 亮度 -12%（避免过曝发白）
"""

import argparse
import os
import colorsys

import numpy as np
from PIL import Image

OUT = r"E:\3d\3-dfps\assets\textures\terrain_prepared"
DEFAULT = {
    "grass001": dict(hue=30.0, sat=1.15, val=0.88),
    "ground037": dict(hue=0.0, sat=1.0, val=0.92),
    "rock063": dict(hue=0.0, sat=1.0, val=0.95),
    "ground080": dict(hue=0.0, sat=1.0, val=0.9),
}


def shift(png_path: str, hue: float, sat: float, val: float) -> None:
    im = Image.open(png_path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    rgb = arr[:, :, :3]
    a = arr[:, :, 3]
    hsv = np.asarray([colorsys.rgb_to_hsv(r, g, b) for r, g, b in rgb.reshape(-1, 3)])
    hsv = hsv.reshape(rgb.shape[0], rgb.shape[1], 3)
    hsv[:, :, 0] = ((hsv[:, :, 0] * 360 + hue) % 360) / 360.0
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat, 0, 1)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * val, 0, 1)
    rgb2 = np.asarray([colorsys.hsv_to_rgb(h, s, v) for h, s, v in hsv.reshape(-1, 3)])
    rgb2 = rgb2.reshape(rgb.shape) * 255.0
    out = np.dstack([rgb2, a]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(png_path)
    print(f"[colors] shifted {os.path.basename(png_path)} hue+{hue} sat*{sat} val*{val}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="校正全部四张贴图")
    ap.add_argument("--hue", type=float, help="色相偏移角度（默认 grass001=30）")
    ap.add_argument("--sat", type=float, help="饱和度倍率（默认 grass001=1.15）")
    ap.add_argument("--val", type=float, help="亮度倍率（默认 grass001=0.88）")
    args = ap.parse_args()
    names = list(DEFAULT) if args.all else ["grass001"]
    for n in names:
        p = os.path.join(OUT, f"{n}_alb_ht.png")
        if not os.path.exists(p):
            print(f"[colors] skip missing {p}")
            continue
        cfg = dict(DEFAULT[n])
        if args.hue is not None:
            cfg["hue"] = args.hue
        if args.sat is not None:
            cfg["sat"] = args.sat
        if args.val is not None:
            cfg["val"] = args.val
        shift(p, cfg["hue"], cfg["sat"], cfg["val"])
    print("[colors] DONE（如需回退，重新跑 prepare_terrain_textures.gd 再执行本脚本）")


if __name__ == "__main__":
    main()
