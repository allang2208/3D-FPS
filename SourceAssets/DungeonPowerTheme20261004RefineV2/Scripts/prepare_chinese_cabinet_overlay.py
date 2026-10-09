"""Create new Chinese label artwork as an RGBA overlay for FacilityProp UVs.

No source basecolor, normal, ORM, meshes or configuration are modified. This
script does not copy, sample, composite, or repaint original basecolor pixels.
It only reads source atlas metadata and image dimensions; new opaque artwork
is drawn into declared label rectangles on an otherwise transparent canvas.

Use a PowerTheme-only material: lerp(original basecolor, overlay RGB, overlay
alpha), with the original NormalGL and ORM retained. All instrument tick
marks, numeric scales, needles and V/A unit letters remain untouched.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'References/ReuseBundle/SourceAssets/DungeonFacilityPropPolish20260928/Authored'
SOURCE_ATLAS=SOURCE/'atlas.json'
SOURCE_IMAGE=SOURCE/'Textures/T_FacilityProp_BaseColor.png'
OUTPUT=ROOT/'Authored/Textures/T_Power_CabinetChinese_Overlay.png'
REPORT=ROOT/'Authored/cabinet_chinese_overlay.json'
FONT_ROOT=ROOT/'References/Fonts'
REGULAR=FONT_ROOT/'NotoSansCJK-Regular.ttc'
BOLD=FONT_ROOT/'NotoSansCJK-Bold.ttc'
FACE_INDEX=2
IVORY=(197,199,179,255)
GREEN=(58,74,61,255)
INK=(31,43,36,255)
LIGHT=(213,215,196,255)
RIM=(117,124,108,255)

# Exact original atlas cells, including the logistics labels, contain all
# non-instrument English wording. The mesh already determines which are used.
CELL_TEXT={
    'cabinet_left':['供能站 · 配电系统','机组控制','01号配电柜 · 一区'],
    'cabinet_right':['供能站 · 配电系统','辅助供电','02号配电柜 · 二区'],
    'warning':['高压危险 · 380伏','检修前切断电源','仅限授权人员'],
    'rating':['供能站 · 配电设备','07号柜 · 三相交流','380伏 · 50赫兹 · 60安','编号04-2781 · 防护等级54'],
    'buttons':['启动','停止'],
    'service':['检修记录 · 07号柜','上次检查：14／09','已断电 · 禁止合闸'],
    'cargo_01':['供能站 · 设备备件','机组维修备件','编号07 · 批次28-41','保持干燥 · 总重84千克'],
    'cargo_02':['供能站 · 设备备件','电气备件','编号07 · 批次28-42','保持干燥 · 总重63千克'],
    'cargo_03':['供能站 · 设备备件','仪表组件','编号07 · 批次28-43','保持干燥 · 总重18千克'],
    'arrows':['此面向上'],
    'fragile':['小心轻放'],
}
# Read-only visual inspection of the original image establishes these interior
# legend boxes. They avoid every tick, scale number, and V/A unit letter.
DIAL_REGIONS={
    'dial_v_title':dict(rect=[1380,1412,1692,1486],text=['交流电压']),
    'dial_a_title':dict(rect=[2404,1412,2716,1486],text=['负载电流']),
    'dial_v_specs':dict(rect=[1374,1700,1700,1795],text=['精度1.5级','50赫兹 · 07号表']),
    'dial_a_specs':dict(rect=[2398,1700,2724,1795],text=['精度1.5级','50赫兹 · 07号表']),
}


def font(size:int,bold:bool=False)->ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else REGULAR),size,index=FACE_INDEX)


def write(draw:ImageDraw.ImageDraw,value:str,box:tuple,size:int,bold:bool=False,
          ink:tuple=INK,center:bool=False)->dict:
    x0,y0,x1,y1=box
    for px in range(size,15,-1):
        f=font(px,bold)
        l,t,r,b=f.getbbox(value)
        if r-l<=x1-x0 and b-t<=y1-y0:break
    else:raise ValueError(('label text cannot fit',value,box))
    x=x0+((x1-x0-(r-l))//2 if center else 0)
    y=y0+(y1-y0-(b-t))//2
    draw.text((x-l,y-t),value,font=f,fill=ink)
    bounds=[x,y,x+r-l,y+b-t]
    assert x0<=bounds[0]<bounds[2]<=x1
    assert y0<=bounds[1]<bounds[3]<=y1
    return dict(text=value,font_size_px=px,bounds_local_px=bounds,bold=bold)


def frame(w:int,h:int,key:str,green:bool=False)->tuple:
    bg=GREEN if green else IVORY
    im=Image.new('RGBA',(w,h),bg)
    d=ImageDraw.Draw(im)
    edge=LIGHT if green else GREEN
    d.rectangle((3,3,w-4,h-4),outline=edge,width=2)
    rng=random.Random('power-cabinet-zh-'+key)
    for _ in range(7):
        x=rng.randint(7,max(8,w-15));y=rng.choice([1,h-2])
        d.line((x,y,min(w-2,x+rng.randint(2,8)),y),fill=RIM,width=1)
    return im,d


def make_cell(key:str,size:tuple)->tuple:
    w,h=size
    green=key in ('service','buttons')
    im,d=frame(w,h,key,green)
    fg=LIGHT if green else INK
    s=CELL_TEXT[key]
    fields=[]
    if key.startswith('cabinet_'):
        fields.append(write(d,s[0],(15,9,w-15,36),23,False,fg,True))
        fields.append(write(d,s[1],(15,41,w-15,89),42,True,fg,True))
        fields.append(write(d,s[2],(15,95,w-15,h-9),21,False,fg,True))
    elif key=='warning':
        d.polygon([(52,17),(91,88),(13,88)],fill=GREEN)
        d.polygon([(52,31),(77,79),(27,79)],fill=IVORY)
        d.polygon([(55,42),(41,62),(51,62),(45,77),(65,54),(53,54)],fill=INK)
        fields.append(write(d,s[0],(103,21,w-15,76),35,True))
        d.line((20,101,w-20,101),fill=GREEN,width=2)
        fields.append(write(d,s[1],(20,112,w-20,149),34,True,INK,True))
        fields.append(write(d,s[2],(20,158,w-20,h-11),26,False,INK,True))
    elif key=='rating':
        boxes=[(18,11,w-18,45),(18,51,w-18,82),(18,91,w-18,124),(18,135,w-18,h-10)]
        for j,(value,box) in enumerate(zip(s,boxes)):
            fields.append(write(d,value,box,27 if j==0 else 24,j==0))
    elif key=='buttons':
        d.line((w//2,14,w//2,h-14),fill=RIM,width=2)
        fields.append(write(d,s[0],(15,16,w//2-15,h-16),34,True,fg,True))
        fields.append(write(d,s[1],(w//2+15,16,w-15,h-16),34,True,fg,True))
    elif key=='service':
        fields.append(write(d,s[0],(16,12,w-16,47),27,True,fg))
        fields.append(write(d,s[1],(16,57,w-16,90),26,False,fg))
        fields.append(write(d,s[2],(16,106,w-16,h-12),34,True,fg))
    elif key.startswith('cargo_'):
        fields.append(write(d,s[0],(17,10,w-17,41),24,True))
        fields.append(write(d,s[1],(17,45,w-17,88),34,True))
        fields.append(write(d,s[2],(17,94,w-17,124),24))
        # Newly authored inventory bars are purely an industrial graphic.
        x=18;rng=random.Random('inventory-bars-'+key)
        while x<w*.69:
            bar=rng.choice([1,2,3,4]);d.rectangle((x,137,x+bar,174),fill=INK)
            x+=bar+rng.choice([2,3,4])
        fields.append(write(d,s[3],(17,181,w-17,h-8),23))
    elif key=='arrows':
        for cx in (w*.30,w*.70):
            d.polygon([(cx,36),(cx-31,80),(cx-13,80),(cx-13,167),
                       (cx+13,167),(cx+13,80),(cx+31,80)],fill=GREEN)
        fields.append(write(d,s[0],(15,h-77,w-15,h-20),33,True,INK,True))
    elif key=='fragile':
        cx=w/2
        d.line([(cx-45,36),(cx-41,98),(cx,131),(cx+41,98),(cx+45,36)],fill=GREEN,width=7)
        d.line((cx,131,cx,175),fill=GREEN,width=7)
        d.line((cx-39,175,cx+39,175),fill=GREEN,width=7)
        fields.append(write(d,s[0],(10,h-64,w-10,h-19),30,True,INK,True))
    else:raise KeyError(key)
    return im,fields


def make_dial_region(key:str,size:tuple,values:list)->tuple:
    w,h=size
    # These are small new enamel legend plates, not sampled dial backgrounds.
    im,d=frame(w,h,key)
    if len(values)==1:
        fields=[write(d,values[0],(12,13,w-12,h-13),40,True,INK,True)]
    else:
        fields=[write(d,values[0],(10,9,w-10,43),27,False,INK,True),
                write(d,values[1],(10,53,w-10,h-10),24,False,INK,True)]
    return im,fields


def main()->None:
    source_hash=hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest()
    atlas=json.loads(SOURCE_ATLAS.read_text(encoding='utf-8'))
    size=tuple(atlas['size'])
    assert size==(4096,2048)
    with Image.open(SOURCE_IMAGE) as source:
        assert source.size==size  # Header-only: no source pixels used in output.
    strings=[s for values in CELL_TEXT.values() for s in values]
    strings += [s for region in DIAL_REGIONS.values() for s in region['text']]
    assert not any(re.search('[A-Za-z]',s) for s in strings)
    chars=set(''.join(strings))-{' '}
    for path in (REGULAR,BOLD):
        f=TTFont(str(path),fontNumber=FACE_INDEX)
        assert f['name'].getDebugName(1)=='Noto Sans CJK SC'
        cmap=f.getBestCmap();missing=sorted(ch for ch in chars if ord(ch) not in cmap)
        assert not missing,(path,missing)
        f.close()
    overlay=Image.new('RGBA',size,(0,0,0,0))
    allowed_alpha=Image.new('L',size,0);mask_draw=ImageDraw.Draw(allowed_alpha)
    regions={}
    for key in list(CELL_TEXT)+list(DIAL_REGIONS):
        rect=atlas['rects'][key] if key in CELL_TEXT else DIAL_REGIONS[key]['rect']
        x0,y0,x1,y1=rect;w,h=x1-x0,y1-y0
        assert 0<=x0<x1<=size[0] and 0<=y0<y1<=size[1]
        if key in CELL_TEXT:im,fields=make_cell(key,(w,h))
        else:im,fields=make_dial_region(key,(w,h),DIAL_REGIONS[key]['text'])
        assert im.getchannel('A').getextrema()==(255,255)
        overlay.paste(im,(x0,y0))
        mask_draw.rectangle((x0,y0,x1-1,y1-1),fill=255)
        regions[key]=dict(rect_px=rect,pixel_dimensions=[w,h],text=fields,
                          original_atlas_key=key if key in CELL_TEXT else 'dial_V' if '_v_' in key else 'dial_A')
    alpha=overlay.getchannel('A')
    # Exactly the declared rectangles are opaque; every other pixel is alpha 0.
    assert ImageChops.difference(alpha,allowed_alpha).getbbox() is None
    assert {value for value,count in enumerate(alpha.histogram()) if count}=={0,255}
    report=dict(size=list(size),mode='RGBA',output=OUTPUT.relative_to(ROOT).as_posix(),
                source_atlas=SOURCE_ATLAS.relative_to(ROOT).as_posix(),
                source_basecolor=SOURCE_IMAGE.relative_to(ROOT).as_posix(),
                source_basecolor_sha256=source_hash,source_pixels_copied=False,
                source_unchanged=True,regions=regions,opaque_region_count=len(regions),
                alpha_bounds_px=list(alpha.getbbox()),alpha_values=[0,255],
                alpha_outside_declared_regions=0,
                blending='lerp(original_basecolor, overlay_rgb, overlay_alpha)',
                retain_original_maps=['T_FacilityProp_NormalGL.png','T_FacilityProp_ORM.png'],
                language='zh-CN',visible_latin_characters_in_overlay=0,
                font='Noto Sans CJK SC',font_face_index=FACE_INDEX,
                unique_printed_characters=len(chars),missing_glyphs=[],
                text_bounds_checked=True,dial_scales_and_unit_letters_unchanged=True,
                scene_rendered=False,gameplay_or_pie_run=False)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    overlay.save(OUTPUT,optimize=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest()==source_hash
    print('CHINESE_CABINET_OVERLAY_AUTHORED',json.dumps(dict(size=size,regions=len(regions),
          alpha_bounds=alpha.getbbox(),alpha_outside_declared_regions=0,
          source_unchanged=True,glyphs=len(chars),missing_glyphs=[],scene_rendered=False)))
    for key,region in regions.items():
        print(key,region['rect_px'],[field['text'] for field in region['text']])


if __name__=='__main__':
    main()
