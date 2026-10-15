"""Arrange the requested actual renders and PNG icons; no generative retouching."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
OUT=ROOT/'Previews/ReviewV2'
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
SPEC=json.loads((ROOT/'presentation.json').read_text(encoding='utf8'))
ORDER=['Multimeter','ToolKit','ImpactWrench']
NAMES={'Multimeter':'工业数字万用表','ToolKit':'精密检修工具组','ImpactWrench':'充电式冲击扳手'}
def font(n):return ImageFont.truetype(str(FONT),n)
def load(p):
    with Image.open(p) as im:return Image.fromarray(np.array(im.convert('RGBA')))
def halve(im):
    a=np.array(im,dtype=np.float32)/255
    a[:,:,:3]*=a[:,:,3:4]
    h,w=a.shape[:2];a=a.reshape(h//2,2,w//2,2,4).mean(axis=(1,3))
    a[:,:,:3]/=np.maximum(a[:,:,3:4],1e-8)
    return Image.fromarray(np.uint8(np.clip(a*255,0,255)))
boards=[]
for label,title in [('front','模型展示'),('rear','另一侧细节')]:
    board=Image.new('RGBA',(1920,650),(22,27,33,255));d=ImageDraw.Draw(board)
    for i,key in enumerate(ORDER):
        d.text((i*640+25,20),NAMES[key],font=font(30),fill=(238,239,233))
        source=next(x['file'] for x in SPEC['views'] if x['key']==key and x['label']==label)
        board.alpha_composite(halve(load(source)),(i*640,68))
    d.text((25,610),'货运区 · '+title+'  |  实际 GLB 模型的 Blender 离线渲染',font=font(21),fill=(159,169,177))
    path=OUT/('models_overview.png' if label=='front' else 'models_reverse.png')
    board.convert('RGB').save(path);boards.append(str(path))
board=Image.new('RGBA',(1200,540),(19,23,29,255));d=ImageDraw.Draw(board)
d.text((28,18),'背包图标 · 占格示意',font=font(30),fill=(237,236,229))
for i,key in enumerate(ORDER):
    entry=next(x for x in SPEC['icons'] if x['key']==key);gw,gh=entry['grid_w'],entry['grid_h']
    d.text((i*400+40,80),NAMES[key],font=font(25),fill=(232,234,230))
    x=i*400+40+(2-gw)*80;y=142+(2-gh)*80;w=gw*160;h=gh*160
    d.rectangle((x,y,x+w,y+h),fill=(29,34,41),outline=(148,139,106),width=2)
    for k in range(1,gw):d.line((x+k*160,y,x+k*160,y+h),fill=(72,76,78),width=1)
    for k in range(1,gh):d.line((x,y+k*160,x+w,y+k*160),fill=(72,76,78),width=1)
    icon=load(entry['file']).resize((w,h),Image.Resampling.LANCZOS)
    board.alpha_composite(icon,(x,y))
    d.text((x,480),f'{gw}×{gh} 格   ·   {entry["pixel_size"][0]}×{entry["pixel_size"][1]} PNG',font=font(20),fill=(172,180,184))
path=OUT/'inventory_icons_overview.png';board.convert('RGB').save(path);boards.append(str(path))
SPEC['boards']=boards
(ROOT/'presentation.json').write_text(json.dumps(SPEC,ensure_ascii=False,indent=2),encoding='utf8')
for path in boards:print(path)
