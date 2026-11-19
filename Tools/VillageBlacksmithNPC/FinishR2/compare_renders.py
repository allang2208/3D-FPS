"""Place untouched same-camera R1 and R2 frames beside one another."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
folder=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/Review'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',32)
def pair(slug,prefix='',crop=None,filename=None):
    ims=[Image.open(folder/(prefix+stage+'_'+slug+'.png')).convert('RGB') for stage in ('before','after')]
    if crop:ims=[im.crop(crop) for im in ims]
    if ims[0].size!=ims[1].size:raise ValueError(slug)
    w,h=ims[0].size
    output=Image.new('RGB',(2*w+6,h+65),'#22282d')
    draw=ImageDraw.Draw(output)
    for i,(im,label) in enumerate(zip(ims,('修改前','修改后'))):
        x=i*(w+6);draw.text((x+23,10),label,font=font,fill='#f2f1ed')
        output.paste(im,(x,65))
    output.save(folder/((filename or prefix+slug+'_compare')+'.jpg'),quality=95,subsampling=0,optimize=True)
if __name__=='__main__':
    import sys
    prefix='ue_' if '--ue' in sys.argv else ''
    for slug in ('portrait','workwear'):pair(slug,prefix)
    if not prefix:pair('portrait',crop=(427,49,968,589),filename='hair_eyes_compare')
