"""Author a theme-only Chinese container-label atlas without changing sources.

The portable bundle does not include the original atlas generator. The source
Config/design.json nevertheless records label_panel_pixels=[800,400], an exact
2:1 panel ratio, and native font drawing/no resize. Its original 800x2000 PNG
contains five 400px rows, and its manifest assigns those rows to the ToolBox,
PPELocker, HeatCabinet, RecordsDrawer and FilterCase families. This replacement
uses the same full image dimensions, row ordering, panel borders, and UV layout.
It is intended only for PowerTheme component-level material overrides.

Only Authored/Textures/T_Power_ContainerLabels_BaseColor.png is written. No UE
imports, source material edits, scene renders, gameplay, or tests are executed.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT/'References/ReuseBundle/SourceAssets/IncineratorContainers20261003'
SOURCE_IMAGE = SOURCE_ROOT/'Authored/T_Treatment_Labels.png'
SOURCE_DESIGN = SOURCE_ROOT/'Config/design.json'
OUTPUT = ROOT/'Authored/Textures/T_Power_ContainerLabels_BaseColor.png'
FONT_ROOT = ROOT / 'References/Fonts'
if not FONT_ROOT.exists():FONT_ROOT = Path('/usr/share/fonts/opentype/noto')
REGULAR = FONT_ROOT/'NotoSansCJK-Regular.ttc'
BOLD = FONT_ROOT/'NotoSansCJK-Bold.ttc'
FONT_INDEX = 2
SIZE = (800, 2000)
ROW_HEIGHT = 400
BACKGROUND = (197, 199, 179)
INK = (31, 43, 36)
STRIPE = (54, 70, 58)
EDGE = (116, 121, 107)

# Ordering is the existing shared mesh UV contract; do not reorder these rows.
ROWS = [
    ('ToolBox', '检修工具', '设备维护', '供能站工具储备'),
    ('PPELocker', '防护用品', '检修防护', '供能站备用物资'),
    ('HeatCabinet', '耐热器材', '高温防护', '机组检修备用器材'),
    ('RecordsDrawer', '设备档案', '检修记录', '总控资料'),
    ('FilterCase', '滤芯备件', '冷却过滤', '供能站维护备件'),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else REGULAR), size, index=FONT_INDEX)


def text(draw: ImageDraw.ImageDraw, value: str, box: tuple[int, int, int, int],
         size: int, bold: bool = False) -> dict:
    x0,y0,x1,y1=box
    f=font(size,bold)
    l,t,r,b=f.getbbox(value)
    assert r-l <= x1-x0 and b-t <= y1-y0, (value,box,size)
    x=x0
    y=y0+(y1-y0-(b-t))//2
    draw.text((x-l,y-t),value,font=f,fill=INK)
    bounds=[x,y,x+r-l,y+b-t]
    assert x0 <= bounds[0] < bounds[2] <= x1
    assert y0 <= bounds[1] < bounds[3] <= y1
    return dict(text=value,font_size_px=size,bounds_px=bounds,bold=bold)


def main() -> None:
    # Read-only source verification establishes compatibility and preservation.
    original_hash=hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest()
    with Image.open(SOURCE_IMAGE) as source:
        assert source.size == SIZE, f'Source atlas dimensions changed: {source.size}'
    design=json.loads(SOURCE_DESIGN.read_text(encoding='utf-8'))
    assert design['label_panel_pixels'] == [800,400]
    assert design['label_width_height_ratio'] == 2
    printed=''.join(''.join(row[1:]) for row in ROWS)
    assert not re.search('[A-Za-z]',printed)
    characters=set(printed)
    for path in (REGULAR,BOLD):
        f=TTFont(str(path),fontNumber=FONT_INDEX)
        assert f['name'].getDebugName(1) == 'Noto Sans CJK SC'
        cmap=f.getBestCmap()
        missing=sorted(ch for ch in characters if ord(ch) not in cmap)
        assert not missing, (path,missing)
        f.close()
    im=Image.new('RGB',SIZE,BACKGROUND)
    d=ImageDraw.Draw(im)
    mapping=[]
    for i,(family,title,subtitle,footer) in enumerate(ROWS):
        y=i*ROW_HEIGHT
        # Same border at x18..782, y18..382 and upper stripe y18..78 as source.
        d.rectangle((18,y+18,782,y+382),outline=STRIPE,width=5)
        d.rectangle((18,y+18,782,y+78),fill=STRIPE)
        fields=[text(d,title,(52,y+105,748,y+211),94,True),
                text(d,subtitle,(54,y+223,746,y+272),44),
                text(d,footer,(54,y+304,746,y+358),37)]
        d.rectangle((52,y+282,748,y+284),fill=(83,94,79))
        # Sparse rim-only paint wear. The text and UV boundaries remain clean.
        rng=random.Random('power-container-label-'+family)
        for _ in range(16):
            x=rng.randint(24,768)
            yy=y+rng.choice([20,21,379,380])
            d.line((x,yy,min(777,x+rng.randint(3,14)),yy),fill=EDGE,width=1)
        for yy in (y+31,y+369):
            for x in (31,769):
                d.ellipse((x-3,yy-3,x+3,yy+3),outline=EDGE,width=1)
        mapping.append(dict(row=i+1,family=family,
                            row_rect_px=[0,y,800,y+ROW_HEIGHT],
                            panel_border_px=[18,y+18,782,y+382],
                            title=title,subtitle=subtitle,footer=footer,text=fields))
    assert im.size == SIZE
    assert hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest() == original_hash
    report=dict(size=list(SIZE),row_height_px=ROW_HEIGHT,row_count=len(ROWS),
                language='zh-CN',visible_latin_characters=0,
                font='Noto Sans CJK SC',font_face_index=FONT_INDEX,
                unique_printed_characters=len(characters),missing_glyphs=[],
                text_bounds_checked=True,source_unchanged=True,
                source_sha256=original_hash,row_mapping=mapping,
                source_uv_layout_preserved=True,scene_rendered=False,
                gameplay_or_pie_run=False)
    metadata=PngImagePlugin.PngInfo()
    metadata.add_itxt('PowerTheme Chinese container atlas',json.dumps(report,ensure_ascii=False))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    im.save(OUTPUT,optimize=True,pnginfo=metadata)
    # Source preservation is checked again after the only write.
    assert hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest() == original_hash
    print('POWER_CHINESE_CONTAINER_LABELS_AUTHORED',json.dumps(report,ensure_ascii=False))
    print('OUTPUT',OUTPUT.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
