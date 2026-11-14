"""Place ungraded PNG captures alongside the approved concept, with identical display transforms."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys
r=Path(__file__).resolve().parent
art=Image.open(r.parent/'FreightStationDesign20261112/01-concept.png').convert('RGB')
cameras=['REF_01_PackingSurface','REF_02_CartSurface']
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if bold else 'msyh.ttc'),size)
def make(stage):
    box=780;pad=27;gutter=16
    for i,cam in enumerate(cameras):
        reference=art.crop((i*art.width//2,0,(i+1)*art.width//2,art.height))
        imgs=[reference,Image.open(r/('before_'+cam+'.png')).convert('RGB')]
        names=['概念参考','UE 实景 · 调整前']
        if stage!='before':
            imgs.append(Image.open(r/(stage+'_'+cam+'.png')).convert('RGB'))
            names.append('UE 实景 · 调整后' if stage=='after' else 'UE 实景 · 灯光阶段')
        w=2*pad+len(imgs)*box+(len(imgs)-1)*gutter
        out=Image.new('RGB',(w,box+166),'#191c1c');draw=ImageDraw.Draw(out)
        draw.text((pad,14),['01   货运仓库 · 包装区','02   车站 · 维修推车'][i],font=font(32,True),fill='#f2eee2')
        for col,img in enumerate(imgs):
            x=pad+col*(box+gutter)
            draw.text((x,71),names[col],font=font(21),fill='#d6c5a7')
            out.paste(img.resize((box,box),Image.Resampling.LANCZOS),(x,110))
        draw.text((pad,box+122),cam+'    /    '+['58°','55°'][i]+'    /    1:1     ·     实景沿用地图曝光，排版只等比缩放',font=font(17),fill='#c3c1b6')
        out.save(r/(stage+'-comparison-'+str(i+1)+'.jpg'),quality=95,subsampling=0)
if __name__=='__main__':make(sys.argv[1])
