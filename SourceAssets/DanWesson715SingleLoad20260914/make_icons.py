"""Create neutral silver RGBA category/option pictograms, no text or frames."""
from pathlib import Path
from PIL import Image, ImageDraw
import math
O=Path(__file__).parent
D=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
(O/'Icons').mkdir(exist_ok=True)

def canvas():return Image.new('RGBA',(512,512),(0,0,0,0))
def cartridge(im,x,y,scale=1):
    d=ImageDraw.Draw(im)
    def box(coords):return tuple(round(v*scale+(x if i%2==0 else y)) for i,v in enumerate(coords))
    d.rounded_rectangle(box((-30,-55,30,95)),radius=round(9*scale),fill=(127,132,135,255),outline=(211,216,217,255),width=max(1,round(3*scale)))
    for offset in range(-24,25):
        value=round(104+85*math.exp(-((offset+12)/18)**2))
        d.line(box((offset,-48,offset,87)),fill=(value,value+3,value+5,255),width=max(1,round(scale)))
    d.polygon([box((-26,-57)),box((-22,-88)),box((-10,-110)),box((10,-110)),box((22,-88)),box((26,-57))],fill=(188,191,193,255))
    d.rounded_rectangle(box((-35,87,35,100)),radius=max(1,round(3*scale)),fill=(197,202,204,255))
    d.line(box((-23,81,23,81)),fill=(60,64,67,255),width=max(1,round(3*scale)))

def loader():
    im=canvas();d=ImageDraw.Draw(im)
    d.ellipse((70,95,420,440),fill=(45,48,51,255),outline=(167,174,178,255),width=9)
    d.ellipse((88,110,402,425),outline=(90,97,102,255),width=4)
    for i in range(6):
        a=math.tau*i/6-math.pi/2;x=245+111*math.cos(a);y=265+111*math.sin(a)
        d.ellipse((x-36,y-36,x+36,y+36),fill=(173,178,181,255),outline=(227,230,232,255),width=3)
        d.ellipse((x-24,y-24,x+24,y+24),fill=(85,90,94,255),outline=(126,132,136,255),width=4)
        d.ellipse((x-12,y-12,x+12,y+12),fill=(154,161,166,255))
    d.rounded_rectangle((204,204,286,300),radius=17,fill=(47,52,55,255),outline=(184,192,196,255),width=4)
    for x in range(215,283,11):d.line((x,219,x,286),fill=(103,112,117,255),width=4)
    return im

single=canvas();cartridge(single,210,256,1.52)
d=ImageDraw.Draw(single);d.line((315,285,377,285),fill=(194,204,208,255),width=10);d.polygon([(365,262),(394,285),(365,308)],fill=(194,204,208,255))
speed=loader()
for key,im in [('reload_device_false',single),('reload_device_dw715_speedloader',speed)]:
    im=im.resize((256,256),Image.Resampling.LANCZOS)
    im.save(O/'Icons'/f'{key}.png');im.save(D/f'{key}.png')
category=loader();cartridge(category,415,100,.64)
category.resize((256,256),Image.Resampling.LANCZOS).save(O/'Icons/T_Category_reload_device.png')
print('DW715_RELOAD_ICONS_CREATED')
