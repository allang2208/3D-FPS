"""Lay out the manufacturer's lateral and oblique photographs beside the game mesh."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from field_pants_art_sheet import cut_photo

ROOT = Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/RidgeBootsR2"


def comparison():
    review = ROOT/"Review"
    refs = ROOT/"Reference"
    paper = Image.new("RGB",(1250,1530),(243,241,236))
    draw = ImageDraw.Draw(paper)
    font_path="C:/Windows/Fonts/msyh.ttc"
    heading = ImageFont.truetype(font_path,30)
    label = ImageFont.truetype(font_path,22)
    draw.text((38,20),"实物参考 · LOWA ZEPHYR MK2 GTX HI",font=heading,fill=(52,47,40))
    draw.text((654,20),"游戏模型 · TS01 高帮战术靴",font=heading,fill=(52,47,40))
    for row,(left,right,caption) in enumerate((
        (refs/"side.jpg",review/"lateral.png","外侧"),(refs/"three_quarter.jpg",review/"three-quarter.png","前外侧"),
        (refs/"sole.jpg",review/"outsole.png","外底纹路"))):
        top = 84+550*row
        available = 250 if row==2 else 434
        for col,path in enumerate((left,right)):
            x = 24+612*col
            draw.rectangle((x,top,x+590,top+available+76),fill=(255,255,255))
            legend = "外底纹路 · 厂家黑色底模图" if row==2 and col==0 else caption
            draw.text((x+18,top+13),legend,font=label,fill=(102,94,80))
            photo = cut_photo(path)
            factor = min(498/photo.width,available/photo.height)
            photo = photo.resize((round(photo.width*factor),round(photo.height*factor)),Image.Resampling.LANCZOS)
            paper.paste(photo,(x+(590-photo.width)//2,top+60+(available-photo.height)//2),photo)
    paper.save(review/"reference-comparison.jpg",quality=94,optimize=True)


if __name__=="__main__":
    comparison()
