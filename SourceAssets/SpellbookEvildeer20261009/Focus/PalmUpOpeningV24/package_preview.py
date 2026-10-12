"""Package the requested source-motion frames without altering game assets."""
import json,sys,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;stills='--stills' in sys.argv
meta=json.loads((P/('stills.json' if stills else 'render.json')).read_text())
events=json.loads((P/'candidate.json').read_text())['events']
folder=P/('stills' if stills else 'frames')
raw=[Image.open(folder/f'{i:03d}.png').convert('RGB') for i in range(meta['count'])]
# One fixed detail crop for the entire take; no per-frame camera or zoom change.
bounds=[]
for im in raw:
    pixels=np.asarray(im).astype(float);background=pixels[0,0]
    yy,xx=np.where(np.linalg.norm(pixels-background,axis=2)>48)
    bounds.append((int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())))
crop=(max(0,min(b[0] for b in bounds)-25),max(0,min(b[1] for b in bounds)-40),min(960,max(b[2] for b in bounds)+45),540)
width=800;height=round((crop[3]-crop[1])*width/(crop[2]-crop[0]))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
frames=[]
for im,t in zip(raw,meta['times']):
    frame=Image.new('RGB',(width,height+70),(25,29,34));frame.paste(im.crop(crop).resize((width,height),Image.Resampling.LANCZOS),(0,38));draw=ImageDraw.Draw(frame)
    stage=('待机握持' if t<.05 else '保留已认可的整体翻转' if t<events['turn_end'] else
           '转动到位 · 松开抓握' if t<events['open_start'] else
           '两侧封面沿书脊展开' if t<events['open_end'] else '悬浮阅读')
    draw.text((18,5),stage,font=font,fill=(239,232,214))
    draw.text((18,height+42),'V23 翻转段保留 · 转到位后松指并开书 · 未接入游戏',font=small,fill=(178,189,202))
    frames.append(frame)
indices=list(range(len(frames))) if stills else [min(range(len(frames)),key=lambda i:abs(meta['times'][i]-t)) for t in [0,.60,.90,1.08,1.25,1.48,1.72,2.20]]
thumb_height=round(frames[0].height*.5)
sheet=Image.new('RGB',(4*400,2*thumb_height),(25,29,34))
for j,i in enumerate(indices):sheet.paste(frames[i].resize((400,thumb_height),Image.Resampling.LANCZOS),((j%4)*400,(j//4)*thumb_height))
sheet.save(P/('stills-contact.jpg' if stills else 'contact.jpg'),quality=90)
if not stills:
    board=Image.new('RGB',(8*120,math.ceil(len(frames)/8)*76))
    for i,f in enumerate(frames):board.paste(f.resize((120,76)),((i%8)*120,(i//8)*76))
    palette=board.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[f.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
    delays=[round((i+1)*100/meta['fps'])*10-round(i*100/meta['fps'])*10 for i in range(len(frames))]
    delays[0]+=450;delays[-1]+=900
    dest=P/'spellbook-turn-release-open-preview.gif'
    indexed[0].save(dest,save_all=True,append_images=indexed[1:],duration=delays,loop=0,disposal=2,optimize=False)
    print(json.dumps({'gif':str(dest),'frames':len(frames),'bytes':dest.stat().st_size,'game_capture':False}))
else:print(str(P/'stills-contact.jpg'))
