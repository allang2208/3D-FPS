"""Layout unmodified fixed-camera UE captures; no exposure or colour edits."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
a=json.loads((R/'before-capture.json').read_text('utf8'));b=json.loads((R/(sys.argv[1]+'-capture.json')).read_text('utf8'))
labels={'PlatformWallAndFloor':'对侧站台','ConcourseFromBridge':'站厅全景','ConcourseDiagonal':'站厅斜向','REF_02_CartSurface':'推车固定机位'}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',36)
for x,y in zip(a,b):
    for k in ['eye','rotation','fov','frame_width','frame_height']:
        if x[k]!=y[k]:raise RuntimeError('Camera changed: '+k)
    one=Image.open(R/x['file']).convert('RGB');two=Image.open(R/y['file']).convert('RGB')
    key=x['file'][7:-4];w,h=one.size
    out=Image.new('RGB',(2*w+72,h+100),(33,33,32));d=ImageDraw.Draw(out)
    for i,(im,title) in enumerate([(one,'修改前'),(two,'修改后')]):
        left=24+i*(w+24);d.text((left,18),labels[key]+' · '+title,font=font,fill=(237,234,226));out.paste(im,(left,76))
    out.save(R/('Compare_'+key+'.jpg'),quality=95,subsampling=0)
    two.resize((960,600)).save(R/('After_'+key+'-view.jpg'),quality=95)
