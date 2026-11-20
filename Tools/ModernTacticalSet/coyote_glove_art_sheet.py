"""Pair the MG-72 reference photographs with TS01 game assets at the same image scale."""
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/CoyoteGlovesR2"


def product(path,height):
    src=Image.open(path)
    if "A" in src.getbands():
        mask=src.getchannel("A")
        bounds=mask.point(lambda a:255 if a>30 else 0).getbbox()
        pic=Image.new("RGB",src.size,"white");pic.paste(src.convert("RGB"),mask=mask)
    else:
        pic=src.convert("RGB");pixel=np.asarray(pic)
        mask=np.min(pixel,axis=2)<220
        y,x=np.nonzero(mask)
        bounds=(int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1))
    pic=pic.crop(bounds)
    pic.thumbnail((375,height),Image.Resampling.LANCZOS)
    return pic


def main():
    images=[("手背",ROOT/"Reference/mg72-1.jpg",ROOT/"Review/back.png"),
            ("掌心",ROOT/"Reference/mg72-2.jpg",ROOT/"Review/palm.png")]
    width,height=880,1056
    board=Image.new("RGB",(width,height),(243,242,237))
    draw=ImageDraw.Draw(board)
    title=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",24)
    caption=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",17)
    for i,label in enumerate(("实物参考 · Mechanix MG-72","游戏模型 · TS01")):
        draw.text((27+i*430,18),label,font=title,fill=(52,49,41))
    for i,(label,ref,current) in enumerate(images):
        y=64+492*i
        for k,path in enumerate((ref,current)):
            x=12+430*k
            draw.rectangle((x,y,x+422,y+481),fill="white")
            draw.text((x+13,y+7),label,font=caption,fill=(92,85,73))
            photo=product(path,432)
            board.paste(photo,(x+(422-photo.width)//2,y+35+(432-photo.height)//2))
    board.save(ROOT/"Review/reference-comparison.jpg",quality=95,optimize=True)


if __name__=="__main__":main()
