from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).resolve().parents[4]/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/HeadHair'

before=Image.open(out/'head_close_before.png').convert('RGB')
after=Image.open(out/'head_close_after.png').convert('RGB')
# Both panels use the same full-resolution crop and the same light rig.
frames=[]
for name,pic in [('修订前',before),('修订后',after)]:
    pic=pic.crop((222,38,677,625))
    panel=Image.new('RGB',(pic.width,pic.height+44),(36,39,42))
    panel.paste(pic,(0,44))
    draw=ImageDraw.Draw(panel)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
    draw.text((15,5),name,font=font,fill=(237,235,229))
    frames.append(panel)
comparison=Image.new('RGB',(frames[0].width*2+2,frames[0].height),(26,28,31))
comparison.paste(frames[0],(0,0));comparison.paste(frames[1],(frames[0].width+2,0))
comparison.save(out/'head_close_comparison.jpg',quality=95,subsampling=0)
