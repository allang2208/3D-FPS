"""Create new Chinese sign overlay only for the reused ServerRack_V1 UVs.

Read-only FBX inspection found source atlas cell usage: server_plate=4 faces,
 dial_volts=2, dial_amps=2. No archive-index, tape, keyboard, status-name, or
warning cells are sampled by this mesh; they remain completely transparent.
The original texture is never sampled, copied, composited or overwritten.
Only source metadata, dimensions and hashes are read. No scene rendering,
gameplay or tests are performed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image,ImageChops,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'References/RevisionSupplement/SourceAssets/DungeonDataArchive20260930/Equipment20260930/Authored'
ATLAS=SOURCE/'atlas.json'
BASECOLOR=SOURCE/'Textures/T_ArchiveEquipment_BaseColor.png'
OUTPUT=ROOT/'Authored/Textures/T_Power_ServerChinese_Overlay.png'
REPORT=ROOT/'Authored/server_chinese_overlay.json'
FONT_ROOT=ROOT/'References/Fonts'
REGULAR=FONT_ROOT/'NotoSansCJK-Regular.ttc'
BOLD=FONT_ROOT/'NotoSansCJK-Bold.ttc'
FONT_INDEX=2
BG=(197,199,179,255)
INK=(31,43,36,255)
BORDER=(68,82,66,255)
# Full source header cell plus strictly interior text-only dial rectangles.
REGIONS={
    'server_plate':dict(source_key='server_plate',rect=[16,3638,1008,3746],
                        text=['数据系统 · 04号机柜','检修前切断主电源']),
    'dial_volts_legend':dict(source_key='dial_volts',rect=[1174,3460,1386,3514],
                             text=['电压']),
    'dial_amps_legend':dict(source_key='dial_amps',rect=[1664,3460,1904,3514],
                            text=['线路电流']),
}


def font(size:int,bold:bool=False)->ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else REGULAR),size,index=FONT_INDEX)


def draw_text(draw:ImageDraw.ImageDraw,value:str,box:tuple,size:int,bold:bool)->dict:
    x0,y0,x1,y1=box
    for fs in range(size,15,-1):
        f=font(fs,bold);l,t,r,b=f.getbbox(value)
        if r-l<=x1-x0 and b-t<=y1-y0:break
    else:raise ValueError(('text exceeds panel bounds',value,box))
    x=x0+(x1-x0-r+l)//2;y=y0+(y1-y0-b+t)//2
    draw.text((x-l,y-t),value,font=f,fill=INK)
    bounds=[x,y,x+r-l,y+b-t]
    assert x0<=bounds[0]<bounds[2]<=x1 and y0<=bounds[1]<bounds[3]<=y1
    return dict(text=value,font_size_px=fs,bounds_local_px=bounds,bold=bold)


def main()->None:
    source_hash=hashlib.sha256(BASECOLOR.read_bytes()).hexdigest()
    atlas=json.loads(ATLAS.read_text(encoding='utf-8'))
    size=tuple(atlas['size']);assert size==(4096,4096)
    with Image.open(BASECOLOR) as source:
        assert source.size==size  # Header information only, no pixels copied.
    assert atlas['rects']['server_plate']==REGIONS['server_plate']['rect']
    strings=[s for r in REGIONS.values() for s in r['text']]
    assert not any(re.search('[A-Za-z]',s) for s in strings)
    chars=set(''.join(strings))-{' '}
    for path in (REGULAR,BOLD):
        f=TTFont(str(path),fontNumber=FONT_INDEX)
        assert f['name'].getDebugName(1)=='Noto Sans CJK SC'
        missing=sorted(ch for ch in chars if ord(ch) not in f.getBestCmap())
        assert not missing,(path,missing)
        f.close()
    im=Image.new('RGBA',size,(0,0,0,0));mask=Image.new('L',size,0)
    md=ImageDraw.Draw(mask);records={}
    for key,spec in REGIONS.items():
        x0,y0,x1,y1=spec['rect'];w,h=x1-x0,y1-y0
        a,b,c,d=atlas['rects'][spec['source_key']]
        assert a<=x0<x1<=c and b<=y0<y1<=d
        panel=Image.new('RGBA',(w,h),BG);pd=ImageDraw.Draw(panel)
        pd.rectangle((2,2,w-3,h-3),outline=BORDER,width=2)
        if key=='server_plate':
            fields=[draw_text(pd,spec['text'][0],(16,9,w-16,59),46,True),
                    draw_text(pd,spec['text'][1],(16,67,w-16,h-10),28,False)]
        else:
            fields=[draw_text(pd,spec['text'][0],(12,8,w-12,h-8),36,True)]
        im.paste(panel,(x0,y0));md.rectangle((x0,y0,x1-1,y1-1),fill=255)
        records[key]=dict(rect_px=spec['rect'],source_atlas_key=spec['source_key'],
                           source_atlas_cell_px=atlas['rects'][spec['source_key']],
                           text=fields)
    alpha=im.getchannel('A')
    assert ImageChops.difference(alpha,mask).getbbox() is None
    assert {v for v,n in enumerate(alpha.histogram()) if n}=={0,255}
    report=dict(size=list(size),mode='RGBA',output=OUTPUT.relative_to(ROOT).as_posix(),
                source_atlas=ATLAS.relative_to(ROOT).as_posix(),
                source_basecolor=BASECOLOR.relative_to(ROOT).as_posix(),
                source_basecolor_sha256=source_hash,source_pixels_copied=False,
                source_unchanged=True,mesh='SM_Archive_ServerRack_V1',
                mesh_material_slot='ArchiveEquipment_Atlas',
                original_material='/Game/Dungeons/DataArchive20260930/EquipmentV1/Materials/M_ArchiveEquipment_Atlas',
                static_mesh_uv_face_counts={'server_plate':4,'dial_volts':2,'dial_amps':2},
                regions=records,alpha_bounds_px=list(alpha.getbbox()),
                alpha_outside_declared_regions=0,alpha_values=[0,255],
                font='Noto Sans CJK SC',font_face_index=FONT_INDEX,
                unique_printed_characters=len(chars),missing_glyphs=[],
                text_bounds_checked=True,dial_scales_and_unit_letters_unchanged=True,
                unused_atlas_cells_unchanged=True,
                blend='lerp(original_basecolor, overlay_rgb, overlay_alpha)',
                retain_original_maps=['T_ArchiveEquipment_NormalDX.png','T_ArchiveEquipment_ORM.png'],
                scene_rendered=False,gameplay_or_pie_run=False)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    im.save(OUTPUT,optimize=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert hashlib.sha256(BASECOLOR.read_bytes()).hexdigest()==source_hash
    print('SERVER_CHINESE_OVERLAY_AUTHORED',json.dumps(dict(size=size,regions=3,
          alpha_bounds=alpha.getbbox(),alpha_outside_declared_regions=0,
          source_unchanged=True,glyphs=len(chars),missing_glyphs=[],scene_rendered=False)))
    for key,spec in REGIONS.items():print(key,spec['rect'],spec['text'])


if __name__=='__main__':
    main()
