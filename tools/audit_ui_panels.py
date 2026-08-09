"""UI 面板化审计脚本（可复用门禁辅助）

扫描 ui/*.gd：
  A. 面板构建清单（PanelContainer/Panel + 样式来源）
  B. make_style 硬编码圆角（非 Style.RADIUS_*）
  C. 灰白主题风险（深底/白字裸色）
  D. 裸 Color( 硬编码（对应 test_ui_tokens 门禁）

用法：python tools/audit_ui_panels.py [ui目录]
"""

import os
import re
import sys


def scan(ui_dir: str) -> None:
    files = sorted(f for f in os.listdir(ui_dir) if f.endswith(".gd"))
    print("=== A. 面板构建清单 ===")
    for name in files:
        lines = open(os.path.join(ui_dir, name), encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines, 1):
            if re.search(r"PanelContainer\.new\(\)|Panel\.new\(\)", ln):
                src = "?"
                for j in range(i, min(i + 8, len(lines))):
                    if 'theme_stylebox_override("panel"' in lines[j]:
                        src = lines[j].split('"panel",')[1].strip()[:70]
                        break
                print(f"  {name:26s} L{i:4d} {ln.strip()[:38]:40s} -> {src}")

    print("\n=== B. make_style 硬编码圆角 ===")
    for name in files:
        if name == "style.gd":
            continue
        lines = open(os.path.join(ui_dir, name), encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines, 1):
            if re.search(r"make_style\([^)]*,\s*\d+,\s*\d+\)", ln) and "RADIUS" not in ln:
                print(f"  {name:26s} L{i:4d} {ln.strip()[:95]}")

    print("\n=== C. 灰白主题风险（深底/白字裸色） ===")
    pat = re.compile(r"Color\.WHITE|Color\(1,\s*1,\s*1|Color\(0\.(9|1)")
    for name in files:
        if name == "style.gd":
            continue
        lines = open(os.path.join(ui_dir, name), encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines, 1):
            if pat.search(ln) and "Style." not in ln and (
                    "font_color" in ln or "color =" in ln or "bg_color" in ln or "bg.color" in ln):
                print(f"  {name:26s} L{i:4d} {ln.strip()[:90]}")

    print("\n=== D. 裸 Color( 硬编码（门禁对应） ===")
    total = 0
    for name in files:
        if name == "style.gd":
            continue
        lines = open(os.path.join(ui_dir, name), encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines, 1):
            if "Color(" in ln and "Style." not in ln:
                total += 1
                print(f"  {name:26s} L{i:4d} {ln.strip()[:90]}")
    print(f"  bare Color( count = {total}")


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ui")
    scan(os.path.abspath(base))
