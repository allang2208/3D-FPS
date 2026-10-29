from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
catalog=json.loads((ROOT/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
def definition(data):
    if isinstance(data,dict):
        if data.get('id')=='ue_kukri':return data
        if 'ue_kukri' in data:return data['ue_kukri']
        for value in data.values():
            result=definition(value)
            if result:return result
    if isinstance(data,list):
        for value in data:
            result=definition(value)
            if result:return result
rate=(38/30)/float(definition(catalog)['attack_seconds'])
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
labels={'Kukri.FullBody.Dual.Thrust':'双持第三段突刺'}
for key,data in json.loads((OUT/'index.json').read_text(encoding='utf-8')).items():
    frames=[]
    for k,time in enumerate(data['times']):
        im=Image.new('RGB',(960,612),(17,23,32));draw=ImageDraw.Draw(im)
        draw.text((16,8),labels[data['role']]+(' · 作者候选' if data['author_candidate'] else ' · 已保存资产')+' · 目录基础攻速',font=font,fill=(240,240,245))
        draw.text((16,36),f'正面偏侧 / 侧面    主手蓝色 / 副手橙色    实际 {time/rate:.2f} 秒 / 作者 {time:.2f} 秒',font=small,fill=(190,204,220))
        for x,v in [(0,'front'),(480,'side')]:
            with Image.open(OUT/'Frames'/f'{key}-{v}-{k:03d}.png') as f:im.paste(f.convert('RGB'),(x,68))
        frames.append(im)
    palette=frames[0].quantize(colors=128);idx=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    # GIF stores centiseconds: distribute rounding so high speed clips do not
    # silently become much slower or faster after per-frame quantization.
    frame_ms=data['duration']*1000/(len(frames)-1)/rate
    dt=[max(10,(round((i+1)*frame_ms/10)-round(i*frame_ms/10))*10) for i in range(len(frames))];dt[0]=150;dt[-1]=250
    idx[0].save(OUT/(key+'.gif'),save_all=True,append_images=idx[1:],duration=dt,loop=0,optimize=False,disposal=2)
    times=[.24,.4,.54,.6,.72,.9]
    sheet=Image.new('RGB',(1440,3*459),(17,23,32))
    for i,t in enumerate(times):
        k=min(range(len(frames)),key=lambda k:abs(data['times'][k]-t));sheet.paste(frames[k].resize((720,459)),((i%2)*720,(i//2)*459))
    sheet.save(OUT/(key+'-sheet.jpg'),quality=90)
