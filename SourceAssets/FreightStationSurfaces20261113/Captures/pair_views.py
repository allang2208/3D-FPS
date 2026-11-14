"""Pair the full original reference with each full Unreal capture. Only the comparison copies are resized."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys
root=Path(__file__).resolve().parent
ref=root.parents[1]/'FreightCartBay20261113/reference.png'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',30)
def comparison(raw,title,out):
    with Image.open(ref) as a,Image.open(root/raw) as b:
        a=a.convert('RGB');b=b.convert('RGB')
        h=848
        panels=[im.resize((round(im.width*h/im.height),h),Image.Resampling.LANCZOS) for im in (a,b)]
        pad,gap,head=22,18,66
        x=pad+panels[0].width+gap
        board=Image.new('RGB',(x+panels[1].width+pad,h+head+pad),(32,32,31))
        draw=ImageDraw.Draw(board)
        for left,label,im in [(pad,'参考图',panels[0]),(x,title,panels[1])]:
            draw.text((left,13),label,font=font,fill=(235,234,228));board.paste(im,(left,head))
        board.save(root/out,quality=96,subsampling=0)
comparison('station_REF_02_CartSurface.png','UE 实景  ·  维修推车固定机位','01-cart-comparison.jpg')
comparison(sys.argv[1],'UE 实景  ·  站厅全景','02-concourse-comparison.jpg')
comparison(sys.argv[2],'UE 实景  ·  对侧站台','03-opposite-platform-comparison.jpg')
