"""Lay out matched front and rear product plates at the same garment height."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/FieldTrousersR2"


def cut_photo(path):
    source=Image.open(path)
    if "A" in source.getbands():
        src=source.convert("RGBA")
        mask=src.getchannel("A")
    else:
        src=source.convert("RGB")
        pixels=np.asarray(src,dtype=np.int16)
        background=np.median(pixels[:8,:,:],axis=(0,1))
        distance=np.max(np.abs(pixels-background),axis=2)
        mask=Image.fromarray(np.uint8(np.clip((distance-4.)/13.,0,1)*255))
        src.putalpha(mask)
    bounds=mask.point(lambda v:255 if v>70 else 0).getbbox()
    return src.crop(bounds)


def main():
    refs=ROOT/"Reference"
    gallery=json.loads((refs/"reference.json").read_bytes())
    paths={item["role"]:refs/item["filename"] for item in gallery["photographs"]}
    width,height=982,1294
    board=Image.new("RGB",(width,height),(244,243,239));draw=ImageDraw.Draw(board)
    family="C:/Windows/Fonts/msyh.ttc"
    h=ImageFont.truetype(family,24);small=ImageFont.truetype(family,19)
    for i,title in enumerate(("实物参考 · Helikon-Tex MCDU","游戏模型 · TS01 战术裤")):
        draw.text((28+482*i,19),title,font=h,fill=(55,50,40))
    for row,(key,view,label) in enumerate((("front","front","正面"),("back","rear","背面"))):
        top=69+604*row
        for col,path in enumerate((paths[key],ROOT/"Review"/(view+".png"))):
            left=12+482*col;draw.rectangle((left,top,left+473,top+593),fill=(247,247,245))
            draw.text((left+16,top+11),label,font=small,fill=(99,91,77))
            pic=cut_photo(path)
            factor=min(437/pic.width,531/pic.height)
            pic=pic.resize((round(pic.width*factor),round(pic.height*factor)),Image.Resampling.LANCZOS)
            board.paste(pic,(left+(474-pic.width)//2,top+47+(531-pic.height)//2),pic)
    board.save(ROOT/"Review/reference-comparison.jpg",quality=94,optimize=True)


if __name__=="__main__":main()
