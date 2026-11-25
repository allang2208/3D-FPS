"""Assemble matched UE photographs and measure two-view landmark drift on the unlit readback."""
from pathlib import Path
import os,json
from PIL import Image,ImageDraw,ImageFont
import cv2,numpy as np
root=Path(__file__).resolve().parents[5]
src=root/'SourceAssets/HillsVillageStable/StablemasterLikenessR6'
out=Path(os.environ['STABLEMASTER_REVIEW'])
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
def read(p):return np.asarray(Image.open(p).convert('RGB'))
def framed(stage,view):
    pixels=read(out/(stage+'-'+view+'-lit.png')).copy()
    diffuse=read(out/(stage+'-'+view+'-albedo.png'))
    solid=(diffuse.max(2)>2).astype('uint8')
    pixels[solid==0]=110
    return Image.fromarray(pixels)
sheet=Image.new('RGB',(3*600+4,2*(625+42)+2),(38,39,40));draw=ImageDraw.Draw(sheet)
measure={}
for i,view in enumerate(('front','side')):
    name=('正面','侧面')[i];y=i*(625+44);ref=read(src/(view+'.png'))
    for j,(title,im) in enumerate([('参考图',Image.fromarray(ref)),('修改前 · UE',framed('before',view)),('当前 · UE',framed('after',view))]):
        x=j*602;draw.text((x+14,y+4),name+'   /   '+title,font=font,fill=(234,231,220))
        sheet.paste(im,(x,y+42))
    albedo=read(out/('after-'+view+'-albedo.png'))
    marks={'front':{'left_brow':(231,256),'right_brow':(370,256),'left_eye':(245,282),'right_eye':(364,282),'nose_tip':(305,353),'lip_line':(302,405)},'side':{'ear':(337,310),'eye':(145,282),'nose_tip':(84,348),'lips':(118,403),'chin':(150,478),'bun':(551,397)}}[view]
    measure[view]={}
    for label,(x,y0) in marks.items():
        def feature(arr):
            return cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY).astype('f')
        target=feature(ref[y0-12:y0+13,x-12:x+13])
        area=albedo[y0-20:y0+21,x-20:x+21].copy()
        # Match the reference's studio background at outline landmarks.
        area[area.max(2)<=2]=110
        corr=cv2.matchTemplate(feature(area),target,cv2.TM_CCOEFF_NORMED)
        _,conf,_,(dx,dy)=cv2.minMaxLoc(corr)
        measure[view][label]=dict(dx=dx-8,dy=dy-8,correlation=round(conf,3))
sheet.save(out/'front-profile-comparison.jpg',quality=95,subsampling=0)
(out/'landmark-readback.json').write_text(json.dumps(measure,indent=2))
