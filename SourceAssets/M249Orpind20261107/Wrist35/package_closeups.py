from pathlib import Path
import json
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent
capture=root.parent/'Wrist34/visual_wrist_closeup';out=root/'review';out.mkdir(exist_ok=True)
for family in ('base','vertical','tactical_vertical','angled','canted','prism'):
    rows=[]
    for empty in (False,True):
        for view in ('wrist_left','wrist_palm'):
            folder=capture/f'box_{"empty" if empty else "normal"}_{family}_{view}'
            data=json.loads((folder/'review.json').read_text(encoding='utf-8-sig'))['frames']
            for time in ([0,.5,1.7,2.8,5.72,6.5] if not empty else [0,.5,1.7,2.6,5.1,6.6]):
                f=min(data,key=lambda x:abs(x['source']-time));rows.append((folder/f['file'],f'{"empty" if empty else "normal"} {view} source={f["source"]:.3f}'))
    canvas=Image.new('RGB',(1440,4*224),'#191919');draw=ImageDraw.Draw(canvas)
    for i,(path,label) in enumerate(rows):
        image=Image.open(path).convert('RGB');image.thumbnail((240,195));x=(i%6)*240;y=(i//6)*224;canvas.paste(image,(x,y+25));draw.text((x+3,y+5),label,fill='white')
    canvas.save(out/(family+'_native_wrist.jpg'),quality=91)
print('Native wrist sheets ready',out)
