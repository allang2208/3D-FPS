"""Show the old and new compiled Jason exit clips on the two actual chairs."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/ArmrestExit20261024'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
kinds={'Chair50':'会客椅','Chair52':'办公椅'}
paths={}
for version in ('BeforeSaved','ReviewSaved'):
    for kind in kinds:paths[version,kind]=sorted((OUT/version/'frames'/kind).glob('*.png'))
frames=[]
for i in range(len(paths['ReviewSaved','Chair50'])):
    im=Image.new('RGB',(960,1040),(29,35,42));draw=ImageDraw.Draw(im)
    for row,(kind,title) in enumerate(kinds.items()):
        for col,(version,label) in enumerate((('BeforeSaved','修复前'),('ReviewSaved','本版'))):
            image=Image.open(paths[version,kind][i]).convert('RGB').resize((480,480),Image.Resampling.LANCZOS)
            im.paste(image,(col*480,row*510+30))
            draw.text((col*480+12,row*510+3),title+' · '+label,font=font,fill='white')
    draw.text((12,1020),'实际保存压缩动作 · Jason 与项目家具 · 离线预览',font=small,fill=(204,211,222))
    frames.append(im)
palette=frames[len(frames)//2].quantize(colors=192)
encoded=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
encoded[0].save(OUT/'armrest_exit_before_after.gif',save_all=True,append_images=encoded[1:],
                duration=[90 if i%3==2 else 80 for i in range(len(encoded))],loop=0,disposal=2,optimize=True)
sheet=Image.new('RGB',(1500,1200),(29,35,42))
for row,(version,kind) in enumerate((('BeforeSaved','Chair50'),('ReviewSaved','Chair50'),('BeforeSaved','Chair52'),('ReviewSaved','Chair52'))):
    for col,i in enumerate((0,10,15,21,30)):
        panel=Image.open(paths[version,kind][i]).convert('RGB').resize((300,300))
        sheet.paste(panel,(col*300,row*300))
        ImageDraw.Draw(sheet).text((col*300+5,row*300+4),kinds[kind]+(' 旧' if version=='BeforeSaved' else ' 新')+f' {i/12:.2f}s',font=small,fill='white')
sheet.save(OUT/'saved_exit_comparison.jpg',quality=93)
print('ARMREST_EXIT_GIF',OUT/'armrest_exit_before_after.gif')
