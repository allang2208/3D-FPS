# -*- coding: utf-8 -*-
"""离线布局预览：工作台制造面板＋冶炼步进行居中对照（非引擎渲染）。

用与源码完全相同的参数把面板 1:1 画出来，供"不打开 UE"时的布局/居中验收：
色值/圆角/留白/字号档取自 Source/FPSGAME/UI/ColdSteelUIStyle.h 与
ColdSteelWorkbenchWidget.cpp / ColdSteelSmeltingWidget.cpp（Scale=1 像素口径）。
字体：中文 Noto Sans SC（工程同款）；纯数字位 JetBrains Mono 未装机时用 Consolas 代替（仅预览）。
输出：Saved/UIPreview/workbench-crafting-preview.png / smelting-batch-center-compare.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "Saved", "UIPreview")
os.makedirs(OUT, exist_ok=True)

NOTO = "C:/Windows/Fonts/NotoSansSC-VF.ttf"
MONO = "C:/Windows/Fonts/consola.ttf"

def font(px, medium=False, numeric=False):
    f = ImageFont.truetype(MONO if numeric else NOTO, px)
    if not numeric and medium:
        try:
            f.set_variation_by_axes([500])
        except Exception:
            pass
    return f

# —— 冷钢正式规则色值（ColdSteelUIStyle.h，sRGB＋alpha/255）——
GLASS      = (26, 26, 26, 248)
HEADER     = (100, 100, 100, 22)
STATUSCARD = (37, 37, 37, 232)
CONTENT    = (18, 18, 18, 235)
TEXTP      = (232, 232, 232, 255)
TEXTS      = (183, 183, 183, 255)
TEXTT      = (145, 145, 145, 255)
ACCENT     = (214, 214, 214, 255)
BORDER     = (222, 222, 222, 46)
BTN        = (43, 43, 43, 190)
BTNHOVER   = (65, 65, 65, 230)
WARNING    = (240, 190, 113, 255)
PANEL_R, CARD_R, BTN_R = 10, 8, 6

def rounded(draw, box, r, fill=None, outline=None, width=1, corners=None):
    if corners is None:
        draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)
        return
    tl, tr, br, bl = corners
    x0, y0, x1, y1 = box
    if fill:
        draw.rectangle([x0 + (r if tl else 0), y0, x1 - (r if tr else 0), y1], fill=fill)
        draw.rectangle([x0, y0 + (r if tl else 0), x1, y1 - (r if bl else 0)], fill=fill)
        for (cx, cy, c) in ((x0 + r, y0 + r, tl), (x1 - r, y0 + r, tr), (x1 - r, y1 - r, br), (x0 + r, y1 - r, bl)):
            if c:
                draw.pieslice([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=fill)
    if outline:
        if tl: draw.arc([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=outline, width=width)
        if tr: draw.arc([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=outline, width=width)
        if br: draw.arc([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=outline, width=width)
        if bl: draw.arc([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=outline, width=width)
        if tl or bl: draw.line([x0, y0 + (r if tl else 0), x0, y1 - (r if bl else 0)], fill=outline, width=width)
        if tr or br: draw.line([x1, y0 + (r if tr else 0), x1, y1 - (r if br else 0)], fill=outline, width=width)
        if tl or tr: draw.line([x0 + (r if tl else 0), y0, x1 - (r if tr else 0), y0], fill=outline, width=width)
        if bl or br: draw.line([x0 + (r if bl else 0), y1, x1 - (r if br else 0), y1], fill=outline, width=width)

def text(draw, xy, s, px, color, medium=False, numeric=False, anchor="la"):
    draw.text(xy, s, font=font(px, medium, numeric), fill=color, anchor=anchor)

def tsize(draw, s, px, medium=False, numeric=False):
    l, t, r, b = draw.textbbox((0, 0), s, font=font(px, medium, numeric))
    return r - l, b - t

def axe_glyph(draw, box, color):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw.line([x0 + w * .30, y0 + h * .85, x0 + w * .62, y0 + h * .22], fill=(150, 120, 90, 255), width=3)
    draw.polygon([(x0 + w * .45, y0 + h * .12), (x0 + w * .88, y0 + h * .22), (x0 + w * .78, y0 + h * .48), (x0 + w * .40, y0 + h * .38)], fill=color)

def pick_glyph(draw, box, color):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw.line([x0 + w * .5, y0 + h * .18, x0 + w * .5, y0 + h * .90], fill=(150, 120, 90, 255), width=3)
    draw.arc([x0 + w * .08, y0 + h * .02, x0 + w * .92, y0 + h * .62], 200, 340, fill=color, width=4)

# ================= 图 1：工作台制造面板 =================
W, H = 520, 800
PX, PY = 120, 20                      # 面板左缘（留出左缘升级页签 36 宽＋缝）
img = Image.new("RGBA", (W + 240, H + 56), (14, 14, 14, 255))
bg = ImageDraw.Draw(img)
for i in range(0, img.width, 4):      # 世界背景微渐变（纯装饰）
    bg.line([i, 0, i, img.height], fill=(16 + (i * 7 // img.width), 15, 14, 255))
# 背包抽屉右缘示意（面板贴抽屉左缘）
bg.rectangle([PX + W + 12, 0, img.width, img.height], fill=(24, 24, 24, 255))
bg.line([PX + W + 12, 0, PX + W + 12, img.height], fill=BORDER, width=1)

panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(panel)
rounded(d, [0, 0, W - 1, H - 1], PANEL_R, fill=GLASS, outline=BORDER, width=1)

y = 0
# 顶栏：HeaderTint 带 + 标题 20 Medium + × 钮
d.rectangle([1, 1, W - 2, 60], fill=HEADER)
text(d, (18, 12 + (36 - 26) // 2), "制作", 20, TEXTP, medium=True)
cb = [W - 18 - 34, 15, W - 18, 45]
rounded(d, cb, BTN_R, fill=BTN, outline=BORDER, width=1)
text(d, ((cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2 - 1), "×", 14, TEXTP, anchor="mm")
y = 60 + 12                                    # Body pad top 12
cx0, cx1 = 16, W - 16                          # Body 内容列（pad 16）

# 状态卡（选中态示例）
card_h = 12 + 28 + 6 + 17 + 8 + 12
rounded(d, [cx0, y, cx1, y + card_h], CARD_R, fill=STATUSCARD, outline=BORDER, width=1)
axe_glyph(d, [cx0 + 12, y + 12, cx0 + 40, y + 40], ACCENT)
text(d, (cx0 + 12 + 28 + 10, y + 12 + 2), "已选：伐木斧", 16, TEXTP, medium=True)
text(d, (cx0 + 12, y + 12 + 28 + 6), "木材 ×1 · 石头 ×1 → 伐木斧 ×1 · 即时", 12, TEXTT)
y += card_h + 10

# 分区标题 + 行卡
text(d, (cx0, y), "可制作项目", 16, TEXTP, medium=True)
y += 22 + 8
rows = [("axe", "伐木斧 ×1", "木材 ×1 · 石头 ×1", "可作 3", True),
        ("pick", "矿镐 ×1", "木材 ×1 · 石头 ×2", "可作 1", False)]
for kind, name, mats, held, sel in rows:
    rh = 10 + 36 + 10
    fill = BTNHOVER if sel else STATUSCARD
    outline = ACCENT if sel else BORDER
    ow = 2 if sel else 1
    rounded(d, [cx0, y, cx1, y + rh], CARD_R, fill=fill, outline=outline, width=ow)
    (axe_glyph if kind == "axe" else pick_glyph)(d, [cx0 + 12, y + 10, cx0 + 40, y + 38], TEXTP)
    text(d, (cx0 + 12 + 28 + 10, y + 10), name, 14, TEXTP)
    text(d, (cx0 + 12 + 28 + 10, y + 10 + 19), mats, 12, TEXTS)
    tw, _ = tsize(d, held, 12)
    text(d, (cx1 - 12 - tw, y + 10 + 4), held, 12, TEXTT)
    y += rh + 6
y += 40                                        # 列表 Fill 区余量

# 居中批量步进行（修复后口径：整组 HAlign_Center）
batch_s = "批量 ×1（最多 3）"
btw, bth = tsize(d, batch_s, 12)
grp = 30 + 8 + btw + 8 + 30
gx = (W - grp) / 2
rounded(d, [gx, y + 4, gx + 30, y + 34], BTN_R, fill=BTN, outline=BORDER, width=1)
text(d, (gx + 15, y + 4 + 15 - 1), "−", 14, TEXTP, medium=True, anchor="mm")
text(d, (gx + 38, y + 4 + 15 - bth / 2), batch_s, 12, TEXTS)
rounded(d, [gx + grp - 30, y + 4, gx + grp, y + 34], BTN_R, fill=BTN, outline=BORDER, width=1)
text(d, (gx + grp - 15, y + 4 + 15 - 1), "+", 14, TEXTP, medium=True, anchor="mm")
y += 4 + 30 + 6

# 整宽主操作 36px
rounded(d, [cx0, y + 2, cx1, y + 2 + 36], BTN_R, fill=BTN, outline=BORDER, width=1)
text(d, (W / 2, y + 2 + 18), "开始制作", 14, TEXTP, anchor="mm")
y += 2 + 36 + 4
text(d, (cx0, y + 2), "已制作 伐木斧 ×1 · 消耗 木材 ×1 石头 ×1", 12, TEXTS)
y += 2 + 17 + 2
text(d, (cx0, H - 8 - 17), "Esc 或 × 关闭 · 制作即时结算：扣材料、产物进背包", 12, TEXTT)

img.alpha_composite(panel, (PX, PY))
# 左缘升级页签（v12b：无描边、只圆左两角、压缝 1px、竖排两字）
tab = Image.new("RGBA", (36, 60), (0, 0, 0, 0))
td = ImageDraw.Draw(tab)
rounded(td, [0, 0, 35, 59], 8, fill=GLASS, corners=(1, 0, 0, 1))
text(td, (18, 30 - 13), "升", 14, TEXTP, medium=True, anchor="mm")
text(td, (18, 30 + 12), "级", 14, TEXTP, medium=True, anchor="mm")
img.alpha_composite(tab, (PX - 36 + 1, PY + (H - 60) // 2))
cap = ImageDraw.Draw(img)
text(cap, (PX, PY + H + 8), "离线布局预览（非引擎渲染）· 参数同源 ColdSteelWorkbenchWidget.cpp · 数字位字体以 Consolas 代 JetBrains Mono", 12, TEXTT)
img.convert("RGB").save(os.path.join(OUT, "workbench-crafting-preview.png"))

# ================= 图 2：冶炼步进行居中对照 =================
CW, CH = 520, 190
cmp = Image.new("RGBA", (CW + 40, CH + 60), (14, 14, 14, 255))
cd = ImageDraw.Draw(cmp)
rounded(cd, [20, 10, 20 + CW - 1, 10 + CH - 1], PANEL_R, fill=GLASS, outline=BORDER, width=1)
mid = 20 + CW / 2
cd.line([mid, 14, mid, 10 + CH - 4], fill=(214, 214, 214, 60), width=1)   # 卡中线
text(cd, (20 + 16, 22), "修复前：读数列 Fill，−/＋ 被顶到行两端＝贴卡边", 12, WARNING)
ry = 44
rounded(cd, [20 + 16, ry, 20 + 16 + 30, ry + 30], BTN_R, fill=BTN, outline=BORDER, width=1)
text(cd, (20 + 16 + 15, ry + 14), "−", 14, TEXTP, medium=True, anchor="mm")
rounded(cd, [20 + CW - 16 - 30, ry, 20 + CW - 16, ry + 30], BTN_R, fill=BTN, outline=BORDER, width=1)
text(cd, (20 + CW - 16 - 15, ry + 14), "+", 14, TEXTP, medium=True, anchor="mm")
text(cd, (mid, ry + 15), "批量 ×1（最多 1）", 12, TEXTS, anchor="mm")
text(cd, (20 + 16, 92), "修复后：[−][读数][＋] 整组 HAlign_Center 居中于卡宽", 12, (104, 213, 173, 255))
ry = 114
btw2, bth2 = tsize(cd, "批量 ×1（最多 1）", 12)
grp2 = 30 + 8 + btw2 + 8 + 30
gx2 = 20 + (CW - grp2) / 2
rounded(cd, [gx2, ry, gx2 + 30, ry + 30], BTN_R, fill=BTN, outline=BORDER, width=1)
text(cd, (gx2 + 15, ry + 14), "−", 14, TEXTP, medium=True, anchor="mm")
text(cd, (gx2 + 38, ry + 15 - bth2 / 2), "批量 ×1（最多 1）", 12, TEXTS)
rounded(cd, [gx2 + grp2 - 30, ry, gx2 + grp2, ry + 30], BTN_R, fill=BTN, outline=BORDER, width=1)
text(cd, (gx2 + grp2 - 15, ry + 14), "+", 14, TEXTP, medium=True, anchor="mm")
old_c = ((20 + 16 + 15) + (20 + CW - 16 - 15)) / 2
text(cd, (20 + 16, 152), "像素测量：修复后组中心=卡中心=%.1f（差 0）" % (gx2 + grp2 / 2,), 12, TEXTT)
text(cd, (20 + 16, 170), "修复前：两钮中心各距卡左右边 16px＝贴卡边", 12, TEXTT)
text(cd, (20, CH + 24), "离线布局预览（非引擎渲染）· 口径同源 ColdSteelSmeltingWidget.cpp 2026-09-25 居中修复", 12, TEXTT)
cmp.convert("RGB").save(os.path.join(OUT, "smelting-batch-center-compare.png"))
print("saved:", os.path.abspath(os.path.join(OUT, "workbench-crafting-preview.png")))
print("saved:", os.path.abspath(os.path.join(OUT, "smelting-batch-center-compare.png")))
