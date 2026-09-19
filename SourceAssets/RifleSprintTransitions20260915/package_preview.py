"""Contact sheet and real-time GIF from the isolated rendered runtime frames."""
import json,sys,csv,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
root=O.parent.parent/'Saved/RifleSprintAudit'/sys.argv[1]
out=root/'Preview';out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14)
cases=[f'{w}_{g}' for w in ('M4','AKM','QBZ191') for g in ('Base','Drum','Angled','Vertical','Canted','Prism')]
times=[(.35,'Walk'),(1.15,'Sprint'),(1.95,'Return'),(2.20,'Walk recovered'),(2.70,'Interrupted'),(3.50,'Walk recovered')]
sheet=Image.new('RGB',(6*320,18*204),(20,23,28));d=ImageDraw.Draw(sheet)
report={}
for row,case in enumerate(cases):
    files={int(p.stem.split('_')[1]):p for p in (root/case).glob('Frame_*.png')}
    if not files:raise RuntimeError('No frames '+case)
    def read(frame):
        # Preserve elapsed time when a screenshot was skipped; never shorten gaps.
        before=[i for i in files if i<=frame];return Image.open(files[max(before) if before else min(files)]).convert('RGB')
    for col,(t,title) in enumerate(times):
        im=read(round(t*20)).resize((320,180),Image.Resampling.LANCZOS)
        sheet.paste(im,(col*320,row*204+24));d.text((col*320+6,row*204+3),case+' / '+title,font=small,fill='white')
    samples=list(csv.DictReader((root/case/'poses.csv').open()))
    def step(prefix):
        points=[[float(r[prefix+'_'+c]) for c in 'xyz'] for r in samples]
        return max(math.dist(a,b) for a,b in zip(points,points[1:]))
    report[case]={'screenshots':len(files),'held_missing_frames':[i for i in range(max(files)+1) if i not in files],
        'max_frame_displacement_cm':{p:step(p) for p in ('left','right','gun')}}
sheet.save(out/'all-grips-transitions.jpg',quality=92)
for i,weapon in enumerate(('M4','AKM','QBZ191')):
    sheet.crop((0,i*6*204,1920,(i+1)*6*204)).save(out/(weapon+'-grips-transitions.jpg'),quality=94)
# Three actual game views together; 50 ms per frame matches 20 Hz capture time.
frames=[]
for frame in range(86):
    canvas=Image.new('RGB',(960,204),(20,23,28));draw=ImageDraw.Draw(canvas)
    for j,w in enumerate(('M4','AKM','QBZ191')):
        folder=root/(w+'_Base');files={int(p.stem.split('_')[1]):p for p in folder.glob('Frame_*.png')}
        available=[i for i in files if i<=frame];chosen=max(available) if available else min(files)
        im=Image.open(files[chosen]).convert('RGB').resize((320,180),Image.Resampling.LANCZOS)
        canvas.paste(im,(j*320,24));draw.text((j*320+8,3),f'{w}  {frame/20:.2f}s',font=font,fill='white')
    frames.append(canvas)
frames[0].save(out/'rifle-walk-sprint.gif',save_all=True,append_images=frames[1:],duration=50,loop=0)
(out/'capture-report.json').write_text(json.dumps(report,indent=2))
print(out)
