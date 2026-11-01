"""Exact optical numerals; red channel ink, green channel contrast outline."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
O=Path(__file__).resolve().parent
atlas=Image.new('L',(1024,96))
draw=ImageDraw.Draw(atlas)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',68)
for i,c in enumerate('0123456789.MRAD '):
    box=draw.textbbox((0,0),c,font=font)
    draw.text((i*64+(64-(box[2]-box[0]))/2-box[0],(96-(box[3]-box[1]))/2-box[1]),c,font=font,fill=255)
halo=atlas.filter(ImageFilter.MaxFilter(9))
Image.merge('RGB',(atlas,halo,Image.new('L',atlas.size))).save(O/'T_OpticNumerals.png')
