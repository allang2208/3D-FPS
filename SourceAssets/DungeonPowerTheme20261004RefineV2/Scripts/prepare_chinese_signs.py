"""Author the Chinese-only PowerTheme sign and console atlas.

Run after prepare_design.py and before author_scene.py. This file only creates
Authored/Textures/T_Power_Labels_BaseColor.png and Authored/atlas.json. It never
edits configurations, imports UE assets, renders a scene, or runs gameplay.

The original twelve sign rectangles keep their exact 984:280 aspect ratio.
Noto's Simplified-Chinese face is explicitly selected from the installed TTC;
all printed characters and all painted text bounds are checked before saving.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = ROOT / 'Authored'
TEXTURES = AUTHORED / 'Textures'
FONT_ROOT = ROOT / 'References/Fonts'
if not FONT_ROOT.exists():FONT_ROOT = Path('/usr/share/fonts/opentype/noto')
FONT_REGULAR = FONT_ROOT / 'NotoSansCJK-Regular.ttc'
FONT_BOLD = FONT_ROOT / 'NotoSansCJK-Bold.ttc'
FONT_INDEX = 2  # Noto Sans CJK SC, not the TTC's default Japanese face.
ATLAS_SIZE = (4096, 4096)
LEGACY_SIZE = (1230, 350)  # Exact old 984/280 ratio, 1.25x linear resolution.

INK = (31, 43, 36)
IVORY = (197, 199, 179)
YELLOW = (190, 173, 112)
GREEN = (64, 81, 66)
LIGHT_INK = (207, 211, 191)
RUST = (91, 74, 53)
BARE_EDGE = (116, 121, 107)


@dataclass(frozen=True)
class Label:
    key: str
    title: str
    subtitle: str = ''
    style: str = 'ivory'
    icon: str = ''
    size: tuple[int, int] = LEGACY_SIZE


LABELS = [
    Label('Switchgear', '01 配电检修廊', '配电设备 · 检修通道'),
    Label('Generators', '02 双机发电厅', '主机组 · 检修平台'),
    Label('Accumulator', '03 蓄能调控厅', '储能核心 · 主控制室'),
    Label('Danger', '高压危险', '检修前必须切断电源', 'yellow', 'voltage'),
    Label('A', '一号发电机', '主供电机组 · 运行区'),
    Label('B', '二号发电机', '备用机组 · 运行区'),
    Label('Exit', '继续前行', '设备区域 · 授权进入', 'green', 'arrow'),
    Label('Gallery', '检修平台', '保持通道畅通'),
    Label('Warning', '旋转机械', '严禁拆除防护罩', 'yellow', 'warning'),
    Label('Core', '飞轮蓄能机组', '转子密封 · 内有储能'),
    Label('Route', '供能检修通道', '设备维护 · 保持畅通'),
    Label('Caution', '当心台阶', '上下平台 · 注意脚下', 'yellow', 'steps'),
    Label('ControlRoom', '主控制室', '配电监测 · 机组调控'),
    Label('Emergency', '紧急停机', '异常工况 · 切断供能', 'yellow', 'warning'),
    Label('MainBus', '主母线', '带电区域 · 严禁触碰', 'yellow', 'voltage'),
    Label('Cooling', '冷却循环', '供水 · 回水 · 保持畅通'),
    # Short equipment labels occupy custom-ratio cells and contain no filler.
    Label('console_title', '机组控制台', style='ivory', size=(960, 240)),
    Label('console_meter_v', '母线电压', style='ivory', size=(960, 240)),
    Label('console_meter_a', '充放电流', style='ivory', size=(960, 240)),
    Label('console_status', '机组状态', style='green', size=(960, 240)),
    Label('console_select', '就地／远程', style='ivory', size=(960, 240)),
    Label('console_service', '检修前切断电源', style='yellow', size=(960, 240)),
    Label('console_emergency', '紧急停机', style='yellow', size=(960, 240)),
    Label('console_id', '控制柜 02', style='ivory', size=(960, 240)),
]
ALIASES = {
    'ConsoleHeader': 'console_title',
    'ConsoleGauge': 'console_meter_v',
    'ConsoleStatus': 'console_status',
    'ConsoleKeys': 'console_select',
}


def face(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size,
                              index=FONT_INDEX)


def verify_glyphs() -> dict:
    chars = set(''.join(item.title + item.subtitle for item in LABELS)) - {' '}
    assert not any(re.search('[A-Za-z]', item.title + item.subtitle) for item in LABELS)
    names = []
    for path in (FONT_REGULAR, FONT_BOLD):
        font = TTFont(str(path), fontNumber=FONT_INDEX)
        cmap = font.getBestCmap()
        missing = sorted(ch for ch in chars if ord(ch) not in cmap)
        assert not missing, f'{path.name} missing Chinese glyphs: {missing}'
        names.append(font['name'].getDebugName(1))
        assert names[-1] == 'Noto Sans CJK SC'
        font.close()
    return dict(font_family=names[0], face_index=FONT_INDEX,
                fonts=[str(FONT_REGULAR), str(FONT_BOLD)],
                unique_printed_characters=len(chars), missing_glyphs=[],
                visible_latin_characters=0)


def fit_text(text: str, width: int, height: int, preferred: int,
             bold: bool) -> tuple[ImageFont.FreeTypeFont, int]:
    for size in range(preferred, 19, -1):
        f = face(size, bold)
        l, t, r, b = f.getbbox(text)
        if r-l <= width and b-t <= height:
            return f, size
    raise ValueError(f'Could not safely fit text: {text}')


def paint_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int],
               color: tuple, preferred: int, bold: bool, centered: bool = False) -> dict:
    x0, y0, x1, y1 = box
    f, size = fit_text(text, x1-x0, y1-y0, preferred, bold)
    l, t, r, b = f.getbbox(text)
    w, h = r-l, b-t
    x = x0 + (x1-x0-w)//2 if centered else x0
    y = y0 + (y1-y0-h)//2
    draw.text((x-l, y-t), text, font=f, fill=color)
    bounds = [x, y, x+w, y+h]
    assert x0 <= bounds[0] < bounds[2] <= x1
    assert y0 <= bounds[1] < bounds[3] <= y1
    return dict(text=text, font_size_px=size, bounds_local_px=bounds,
                bold=bold, glyphs_verified=True)


def edge_wear(draw: ImageDraw.ImageDraw, size: tuple[int, int], key: str,
              background: tuple) -> None:
    """Localized paint chips, fastener contact marks and a few rim scratches.

    The large text field is never dithered, dirt-sprayed, or scratched. Wear is
    deterministic and confined to the outer 2.6% of a plate and bolt corners.
    """
    w, h = size
    rng = random.Random('power-zh-20261004-' + key)
    band = max(5, int(h*.026))
    for _ in range(38):
        side = rng.randrange(4)
        if side < 2:
            x = rng.randint(4, w-16)
            y = rng.randint(1, band) if side == 0 else rng.randint(h-band-1, h-2)
            length = rng.randint(3, 18)
            draw.line((x, y, min(w-3, x+length), y+rng.choice([-1, 0, 1])),
                      fill=rng.choice([BARE_EDGE, RUST]), width=rng.randint(1, 3))
        else:
            x = rng.randint(1, band) if side == 2 else rng.randint(w-band-1, w-2)
            y = rng.randint(4, h-12)
            draw.line((x, y, x, min(h-3, y+rng.randint(3, 9))),
                      fill=rng.choice([BARE_EDGE, RUST]), width=2)
    # Small mounting marks complement physical bolt geometry, not fake deep holes.
    inset = max(16, int(h*.075))
    radius = max(3, int(h*.013))
    for x in (inset, w-inset):
        for y in (inset, h-inset):
            draw.ellipse((x-radius-2, y-radius-2, x+radius+2, y+radius+2),
                         outline=BARE_EDGE, width=2)
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=background)
            draw.arc((x-radius-4, y-radius-4, x+radius+4, y+radius+4),
                     35, 155, fill=RUST, width=2)


def paint_icon(draw: ImageDraw.ImageDraw, kind: str, box: tuple, ink: tuple,
               background: tuple) -> None:
    x0, y0, x1, y1 = box
    cx, cy = (x0+x1)/2, (y0+y1)/2
    w, h = x1-x0, y1-y0
    if kind == 'arrow':
        pts = [(x0, cy-h*.12), (x0+w*.57, cy-h*.12), (x0+w*.57, y0),
               (x1, cy), (x0+w*.57, y1), (x0+w*.57, cy+h*.12), (x0, cy+h*.12)]
        draw.polygon(pts, fill=ink)
        return
    draw.polygon([(cx, y0), (x1, y1), (x0, y1)], fill=ink)
    draw.polygon([(cx, y0+h*.15), (x1-w*.15, y1-h*.10),
                  (x0+w*.15, y1-h*.10)], fill=background)
    if kind == 'voltage':
        draw.polygon([(cx+w*.05, y0+h*.30), (cx-w*.16, y0+h*.62),
                      (cx-w*.015, y0+h*.62), (cx-w*.065, y0+h*.83),
                      (cx+w*.19, y0+h*.48), (cx+w*.035, y0+h*.48)], fill=ink)
    elif kind == 'steps':
        draw.line([(x0+w*.26, y0+h*.77), (x0+w*.42, y0+h*.77),
                   (x0+w*.42, y0+h*.63), (x0+w*.57, y0+h*.63),
                   (x0+w*.57, y0+h*.49), (x0+w*.67, y0+h*.49)],
                  fill=ink, width=12)
    else:
        draw.rounded_rectangle((cx-w*.035, y0+h*.33, cx+w*.035, y0+h*.65),
                               radius=3, fill=ink)
        r=w*.045
        draw.ellipse((cx-r, y0+h*.76-r, cx+r, y0+h*.76+r), fill=ink)


def paint_label(item: Label) -> tuple[Image.Image, list[dict]]:
    w, h = item.size
    bg = YELLOW if item.style == 'yellow' else GREEN if item.style == 'green' else IVORY
    ink = LIGHT_INK if item.style == 'green' else INK
    im = Image.new('RGB', item.size, bg)
    d = ImageDraw.Draw(im)
    rim = max(9, int(h*.035))
    d.rectangle((rim, rim, w-rim, h-rim), outline=ink, width=4)
    fields = []
    if item.subtitle:
        left, right = 68, w-68
        if item.icon == 'arrow':
            paint_icon(d, 'arrow', (w-214, 91, w-65, 226), ink, bg)
            right = w-242
        elif item.icon:
            paint_icon(d, item.icon, (64, 76, 240, 262), ink, bg)
            left = 294
        fields.append(paint_text(d, item.title, (left, 45, right, 213), ink, 151, True))
        fields.append(paint_text(d, item.subtitle, (left, 229, right, 291), ink, 59, False))
        d.rectangle((left, 314, right, 319), fill=ink)
    else:
        inset = max(44, int(h*.18))
        fields.append(paint_text(d, item.title, (inset, int(h*.21), w-inset, int(h*.79)),
                                 ink, int(h*.61), True, centered=True))
    edge_wear(d, item.size, item.key, bg)
    for field in fields:
        x0,y0,x1,y1=field['bounds_local_px']
        assert rim+8 < x0 < x1 < w-rim-8
        assert rim+8 < y0 < y1 < h-rim-8
    return im, fields


def main() -> None:
    glyph_report = verify_glyphs()
    TEXTURES.mkdir(parents=True, exist_ok=True)
    canvas = Image.new('RGB', ATLAS_SIZE, INK)
    rects, metadata = {}, {}
    all_bounds = []
    for i, item in enumerate(LABELS):
        if i < 16:
            x, y = 40+(i%3)*1344, 40+(i//3)*408
        else:
            j = i-16
            x, y = 40+(j%4)*1016, 2540+(j//4)*612
        w,h = item.size
        rect = [x,y,x+w,y+h]
        assert 0 <= x < x+w <= ATLAS_SIZE[0]
        assert 0 <= y < y+h <= ATLAS_SIZE[1]
        for other in all_bounds:
            assert (rect[2]+16 <= other[0] or other[2]+16 <= rect[0]
                    or rect[3]+16 <= other[1] or other[3]+16 <= rect[1]), item.key
        artwork, fields = paint_label(item)
        # Extend edge texels into a 12px gutter to reduce lower-mip seam bleed.
        for g in range(12, 0, -1):
            ImageDraw.Draw(canvas).rectangle((x-g,y-g,x+w+g,y+h+g), fill=artwork.getpixel((0,0)))
        canvas.paste(artwork, (x,y))
        all_bounds.append(rect)
        rects[item.key] = rect
        metadata[item.key] = dict(title=item.title, subtitle=item.subtitle,
                                  pixel_dimensions=[w,h], aspect_ratio=w/h,
                                  text=fields, style=item.style,
                                  wear='edge_and_mounting_contact_only')
    for alias,key in ALIASES.items():
        rects[alias] = rects[key].copy()
        metadata[alias] = dict(alias_of=key, title=metadata[key]['title'],
                               pixel_dimensions=metadata[key]['pixel_dimensions'],
                               aspect_ratio=metadata[key]['aspect_ratio'])
    for item in LABELS[:12]:
        assert item.size[0]*280 == item.size[1]*984
    atlas = dict(size=list(ATLAS_SIZE), rects=rects, labels=metadata,
                 language='zh-CN', printed_text_language='Simplified Chinese',
                 glyph_checks=glyph_report, text_bounds_checked=True,
                 texture_gutter_px=12, unique_artwork_count=len(LABELS),
                 legacy_sign_aspect_ratio_preserved=True,
                 generation='original Chinese typography and vector safety artwork',
                 scene_rendered=False, gameplay_or_pie_run=False)
    canvas.save(TEXTURES/'T_Power_Labels_BaseColor.png', optimize=True)
    (AUTHORED/'atlas.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('CHINESE_SIGN_ATLAS_AUTHORED', json.dumps(dict(size=ATLAS_SIZE,
          artwork=len(LABELS), keys=len(rects), glyphs=glyph_report['unique_printed_characters'],
          missing_glyphs=[], text_bounds_checked=True, scene_rendered=False,
          gameplay_or_pie_run=False), ensure_ascii=False))
    for item in LABELS:
        print(item.key, f'{item.size[0]}x{item.size[1]}', item.title, ' / '+item.subtitle if item.subtitle else '')


if __name__ == '__main__':
    main()
