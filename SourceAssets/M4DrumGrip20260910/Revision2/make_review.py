from PIL import Image,ImageDraw
from pathlib import Path
import re,sys,json
O=Path(__file__).resolve().parent;run=sys.argv[1];folder=Path('D:/FPS3D/FPSGAME/Saved/DrumGripAudit')/run
log=(O/f'runtime-{run}.log').read_text(encoding='utf-8',errors='replace');report={}
for clip in ['normal','empty']:
 entries=[(int(i),float(t)) for c,i,t in re.findall(r'DRUM_GRIP: FRAME clip=(\w+) index=(\d+) elapsed=([\d.]+)',log) if c==clip]
 frames=[];durations=[]
 for k,(i,t) in enumerate(entries):
  path=folder/f'{clip}_{i:03}.png'
  if not path.exists():continue
  im=Image.open(path).convert('RGB');im=im.resize((960,540),Image.Resampling.LANCZOS);frames.append(im)
  durations.append(max(20,round((entries[k+1][1]-t)*1000)) if k+1<len(entries) else 250)
 assert frames
 frames[0].save(O/f'{run}_{clip}.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False)
 for page in range(2):
  sheet=Image.new('RGB',(1600,1000),(25,28,32));draw=ImageDraw.Draw(sheet)
  for j in range(16):
   k=round((page*16+j)*(len(entries)-1)/31);i,t=entries[k];im=Image.open(folder/f'{clip}_{i:03}.png').convert('RGB').resize((400,225))
   x=(j%4)*400;y=(j//4)*250;sheet.paste(im,(x,y));draw.text((x+6,y+229),f'{clip}  {t:.3f}s  frame {i}',fill='white')
  sheet.save(O/f'{run}_{clip}_sheet{page}.jpg',quality=92)
 report[clip]={'captured_frames':len(frames),'first_elapsed':entries[0][1],'last_elapsed':entries[-1][1],'gif':str(O/f'{run}_{clip}.gif')}
(O/f'{run}_preview.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
