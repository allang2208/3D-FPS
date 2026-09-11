from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,shutil
src=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
out=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911/reference')
cfg=json.loads((src/'data/enemy-config.json').read_text(encoding='utf-8'))['poisonMaggot']
(out/'source_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
records=[]
for state,key in [('idle','idle'),('walk','walking'),('spitting','spitting'),('death','death')]:
 p=src/cfg['textures'][key]; im=Image.open(p).convert('RGBA'); l=cfg['textures']['frameLayouts'][state]; w,h=l['frameWidth'],l['frameHeight']; n=l['frameCount']; dur=l.get('duration',n/l.get('frameRate',1)*1000)/1000
 indices=list(range(n)) if state=='spitting' else list(range(0,n,max(1,n//8)))
 board=Image.new('RGB',(960,180*((len(indices)+3)//4)),(42,43,44));draw=ImageDraw.Draw(board)
 for j,i in enumerate(indices):
  frame=im.crop(((i%8)*w,(i//8)*h,(i%8+1)*w,(i//8+1)*h)); frame.save(out/f'{state}_{i:02d}.png')
  frame.thumbnail((236,166)); xy=((j%4)*240,(j//4)*180);board.paste(frame,xy,frame);draw.text((xy[0]+5,xy[1]+160),f'{state} 0-based {i} / {i*dur/n:.3f}s',fill=(240,240,230))
 board.save(out/f'{state}_contact.jpg')
 if state=='idle':
  frame=im.crop((0,0,w,h));bbox=frame.getbbox();frame.crop(bbox).save(out/'identity.png')
 records.append({'state':state,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'layout':l,'seconds':dur})
shutil.copy2(src/'src/entities/enemy-types/poison-maggot.js',out/'poison-maggot.source.js')
(out/'sources.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=False))
