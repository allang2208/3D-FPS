"""Arrange unchanged runtime screenshots from the same inspection light rig."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent
P=O.parents[2]
before=P/'Saved/SVCHPoseAudit/svch-check-20261018-studio1/Frames'
after=P/'Saved/SVCHPoseAudit'/(sys.argv[1] if len(sys.argv)>1 else 'svch-check-20261018-r4-final')/'Frames'
sheet=Image.new('RGB',(1280,800),(27,29,33))
draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
for row,(filename,stage) in enumerate((('hip_00007.png','腰射'),('ads_00023.png','ADS'))):
    for col,(root,label) in enumerate(((before,'R3 修复前'),(after,'R4 修复后'))):
        image=Image.open(root/filename).convert('RGB').resize((640,360),Image.Resampling.LANCZOS)
        x,y=col*640,row*400
        sheet.paste(image,(x,y+36))
        draw.text((x+14,y+6),label+'  ·  '+stage,font=font,fill=(238,238,238))
sheet.save(O/'r3-r4-comparison.jpg',quality=92)
print(O/'r3-r4-comparison.jpg')
