from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys
p=Path(sys.argv[1])
ink='#1c302f';paper='#f5f4ef';font='C:/Windows/Fonts/msyh.ttc'
bold='C:/Windows/Fonts/msyhbd.ttc'
def f(s,heavy=False):return ImageFont.truetype(bold if heavy else font,s)
def sheet(rows,dest,title,w):
    pad=24;gap=9;header=105
    dims=[]
    for key,_ in rows:
        with Image.open(p/('brace_'+key+'.png')) as img:dims.append(round(w*img.height/img.width))
    height=header+sum(dims)+len(rows)*33+pad
    im=Image.new('RGB',(pad*2+3*w+2*gap,height),paper);d=ImageDraw.Draw(im)
    d.text((pad,12),title,font=f(32,True),fill=ink)
    for i,tag in enumerate(('松弦','半拉','满拉')):
        d.text((pad+i*(w+gap),65),tag,font=f(23,True),fill=ink)
    y=header
    for (key,text),h in zip(rows,dims):
        if text:
            d.text((pad,y),text,font=f(19,True),fill=ink);y+=30
        for i,tag in enumerate(('brace','half','full')):
            with Image.open(p/(tag+'_'+key+'.png')) as frame:
                im.paste(frame.convert('RGB').resize((w,h),Image.Resampling.LANCZOS),(pad+i*(w+gap),y))
        y+=h+4
    im.crop((0,0,im.width,y+pad-4)).save(p/dest,optimize=True)
sheet([('assembly','')],'边境复合弓_同机位三态.png','边境复合弓 · 同机位拉弓对照',530)
sheet([('upper','上轮与弦槽'),('lower','下轮与控制缆'),('rest','箭杆与左侧托槽')],'轮组弦缆与托槽_三态细节.png','边境复合弓 · 同机位细节',600)
