"""Create three theme-only Chinese overlays for used Workshop PrintAtlas cells.

Read-only static FBX UV inspection confirms:
- DispatchElectronics: 2 RS_Screen faces use Monitor. RS_Display is unrelated
  Office_Display body material and must NOT receive this overlay.
- RackSpares_0: 4 RS_Labels faces use Tools.
- MotorService: 2 RS_Labels faces use Label.

Source manifest regions use [x,y,width,height], not corner coordinates. This
script reads that contract and MATERIALS.json, draws original Chinese artwork
on transparent RGBA, and preserves every original source pixel/file. No source
image pixels are sampled or copied. No scene renders, gameplay or tests run.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image,ImageChops,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
SUPPLEMENT=ROOT/'References/RevisionSupplement'
SOURCE=SUPPLEMENT/'SourceAssets/StationWorkshop20261003'
MANIFEST=SOURCE/'RefineV2/Authored/manifest.json'
MATERIALS=SUPPLEMENT/'MATERIALS.json'
SOURCE_IMAGE=SOURCE/'Authored/T_Workshop_PrintAtlas.png'
OUTPUT=ROOT/'Authored/Textures/T_Power_WorkshopChinese_Overlay.png'
REPORT=ROOT/'Authored/workshop_chinese_overlay.json'
FONT_ROOT=ROOT/'References/Fonts'
REGULAR=FONT_ROOT/'NotoSansCJK-Regular.ttc'
BOLD=FONT_ROOT/'NotoSansCJK-Bold.ttc'
FACE_INDEX=2
SIZE=(2048,2048)
IVORY=(197,199,179,255)
INK=(31,43,36,255)
GREEN=(60,78,64,255)
SCREEN=(12,26,28,255)
SCREEN_INK=(149,180,158,255)
SCREEN_DIM=(72,113,96,255)

REGIONS={
    'Monitor':dict(expected_xywh=[1240,16,784,441],
        text=['运行监测／02号终端','一号机组','二号机组','供能状态','母线参数','冷却回路','—','设备状态显示'],
        mesh='SM_SW_DispatchElectronics',slot='RS_Screen',faces=2,
        material='/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Screen'),
    'Tools':dict(expected_xywh=[820,1620,760,152],text=['备件','用后归还'],
        mesh='SM_SW_RackSpares_0',slot='RS_Labels',faces=4,
        material='/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Print'),
    'Label':dict(expected_xywh=[16,1620,760,152],text=['检修记录','04号机组'],
        mesh='SM_SW_MotorService',slot='RS_Labels',faces=2,
        material='/Game/Dungeons/StationWorkshop20261003/Materials/M_Workshop_Print'),
}


def font(size:int,bold:bool=False)->ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else REGULAR),size,index=FACE_INDEX)


def write(draw:ImageDraw.ImageDraw,text:str,box:tuple,size:int,bold:bool=False,
          color:tuple=INK,center:bool=False)->dict:
    x0,y0,x1,y1=box
    for fs in range(size,15,-1):
        f=font(fs,bold);l,t,r,b=f.getbbox(text)
        if r-l<=x1-x0 and b-t<=y1-y0:break
    else:raise ValueError(('text exceeds authored bounds',text,box))
    x=x0+((x1-x0-r+l)//2 if center else 0);y=y0+(y1-y0-b+t)//2
    draw.text((x-l,y-t),text,font=f,fill=color)
    bounds=[x,y,x+r-l,y+b-t]
    assert x0<=bounds[0]<bounds[2]<=x1 and y0<=bounds[1]<bounds[3]<=y1
    return dict(text=text,font_size_px=fs,bounds_local_px=bounds,bold=bold)


def panel(key:str,w:int,h:int,values:list)->tuple:
    is_screen=key=='Monitor'
    im=Image.new('RGBA',(w,h),SCREEN if is_screen else IVORY)
    d=ImageDraw.Draw(im);fields=[]
    d.rectangle((3,3,w-4,h-4),outline=SCREEN_DIM if is_screen else GREEN,width=3)
    if is_screen:
        fields.append(write(d,values[0],(25,17,w-25,65),39,True,SCREEN_INK))
        d.line((25,82,w-25,82),fill=SCREEN_DIM,width=2)
        # Static blank readouts communicate no alarm or asserted live condition.
        for j,label in enumerate(values[1:6]):
            y=101+j*53
            fields.append(write(d,label,(30,y,438,y+38),30,False,SCREEN_INK))
            fields.append(write(d,'—',(513,y,w-39,y+38),32,False,SCREEN_INK))
        d.rectangle((24,h-58,w-25,h-19),fill=(28,63,51,255))
        fields.append(write(d,values[-1],(36,h-55,w-38,h-21),23,False,SCREEN_INK))
    else:
        fields.append(write(d,values[0],(25,14,w-25,87),66,True,INK,True))
        fields.append(write(d,values[1],(25,99,w-25,h-15),35,False,INK,True))
    return im,fields


def main()->None:
    source_hash=hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest()
    with Image.open(SOURCE_IMAGE) as source:
        assert source.size==SIZE  # Header-only read; source pixels are not used.
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    materials=json.loads(MATERIALS.read_text(encoding='utf-8'))['asset_slot_maps']
    texts=[t for r in REGIONS.values() for t in r['text']]
    assert not any(re.search('[A-Za-z]',t) for t in texts)
    chars=set(''.join(texts))-{' '}
    for path in (REGULAR,BOLD):
        f=TTFont(str(path),fontNumber=FACE_INDEX)
        assert f['name'].getDebugName(1)=='Noto Sans CJK SC'
        cmap=f.getBestCmap();missing=sorted(ch for ch in chars if ord(ch) not in cmap)
        assert not missing,(path,missing)
        f.close()
    im=Image.new('RGBA',SIZE,(0,0,0,0));mask=Image.new('L',SIZE,0)
    md=ImageDraw.Draw(mask);records={}
    for key,spec in REGIONS.items():
        assert manifest['regions'][key]==spec['expected_xywh']
        assert materials[spec['mesh']][spec['slot']]==spec['material']
        x,y,w,h=manifest['regions'][key];rect=[x,y,x+w,y+h]
        art,fields=panel(key,w,h,spec['text']);im.paste(art,(x,y))
        md.rectangle((x,y,x+w-1,y+h-1),fill=255)
        records[key]=dict(rect_px=rect,source_xywh=[x,y,w,h],text=fields,
                           mesh=spec['mesh'],material_slot=spec['slot'],
                           original_material=spec['material'],static_uv_face_count=spec['faces'])
    alpha=im.getchannel('A')
    assert ImageChops.difference(alpha,mask).getbbox() is None
    assert {v for v,n in enumerate(alpha.histogram()) if n}=={0,255}
    report=dict(size=list(SIZE),mode='RGBA',output=OUTPUT.relative_to(ROOT).as_posix(),
        source_atlas=SOURCE_IMAGE.relative_to(ROOT).as_posix(),
        source_region_manifest=MANIFEST.relative_to(ROOT).as_posix(),
        source_materials=MATERIALS.relative_to(ROOT).as_posix(),
        source_sha256=source_hash,source_pixels_copied=False,source_unchanged=True,
        regions=records,alpha_bounds_px=list(alpha.getbbox()),alpha_values=[0,255],
        alpha_outside_declared_regions=0,text_bounds_checked=True,
        font='Noto Sans CJK SC',font_face_index=FACE_INDEX,
        unique_printed_characters=len(chars),missing_glyphs=[],
        visible_latin_characters_in_overlay=0,
        excluded_slot=dict(mesh='SM_SW_DispatchElectronics',slot='RS_Display',
            material=materials['SM_SW_DispatchElectronics']['RS_Display'],
            reason='Separate office display body material; does not use Monitor cell.'),
        screen_status_policy='Static blank readouts; no fabricated live status or alarm.',
        blend='lerp(original_print_atlas, overlay_rgb, overlay_alpha)',
        screen_integration='Apply the same overlaid color to the original screen emission path when present.',
        scene_rendered=False,gameplay_or_pie_run=False)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    im.save(OUTPUT,optimize=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert hashlib.sha256(SOURCE_IMAGE.read_bytes()).hexdigest()==source_hash
    print('WORKSHOP_CHINESE_OVERLAY_AUTHORED',json.dumps(dict(size=SIZE,regions=3,
        alpha_bounds=alpha.getbbox(),alpha_outside_declared_regions=0,
        source_unchanged=True,glyphs=len(chars),missing_glyphs=[],scene_rendered=False)))
    for key,spec in records.items():
        print(key,spec['rect_px'],spec['mesh'],spec['material_slot'],spec['original_material'])


if __name__=='__main__':
    main()
