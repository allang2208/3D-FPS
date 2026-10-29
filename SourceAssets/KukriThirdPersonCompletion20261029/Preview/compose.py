from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
labels={'Kukri.FullBody.Equip':'单持拔刀抛接','Kukri.FullBody.Dual.Equip':'双持拔刀抛接','Pistol.KukriUppercut':'手枪＋副手刀上挑（此候选图未显示手枪）','Kukri.FullBody.Dual.Pommel':'双持快速近战','Kukri.FullBody.Dual.Run':'双持奔跑换握（上身过渡）','Kukri.FullBody.Dual.Recover1':'双持第一段收势','Kukri.FullBody.Dual.Recover2':'双持第二段收势'}
for key,data in json.loads((OUT/'index.json').read_text()).items():
    frames=[]
    for k,time in enumerate(data['times']):
        im=Image.new('RGB',(960,612),(17,23,32));draw=ImageDraw.Draw(im)
        draw.text((16,8),labels[data['role']]+(' · 作者候选' if data['author_candidate'] else ' · 已保存资产'),font=font,fill=(240,240,245))
        draw.text((16,36),f'正面偏侧 / 侧面    主手蓝色 / 副手橙色    {time:.2f} 秒',font=small,fill=(190,204,220))
        for x,v in [(0,'front'),(480,'side')]:
            with Image.open(OUT/'Frames'/f'{key}-{v}-{k:03d}.png') as f:im.paste(f.convert('RGB'),(x,68))
        frames.append(im)
    palette=frames[0].quantize(colors=128);idx=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    dt=[max(10,round(data['duration']*1000/(len(frames)-1)/10)*10)]*len(frames);dt[0]=200;dt[-1]=400
    idx[0].save(OUT/(key+'.gif'),save_all=True,append_images=idx[1:],duration=dt,loop=0,optimize=False,disposal=2)
    times=[0,.15,.30,.43,.65,data['duration']] if 'Uppercut' in key else [0,data['duration']*.18,data['duration']*.35,data['duration']*.50,data['duration']*.7,data['duration']]
    sheet=Image.new('RGB',(1440,3*459),(17,23,32))
    for i,t in enumerate(times):
        k=min(range(len(frames)),key=lambda k:abs(data['times'][k]-t));sheet.paste(frames[k].resize((720,459)),((i%2)*720,(i//2)*459))
    sheet.save(OUT/(key+'-sheet.jpg'),quality=90)
