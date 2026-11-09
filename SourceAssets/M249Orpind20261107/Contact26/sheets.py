from pathlib import Path
import json,numpy as np,pickle
from PIL import Image,ImageOps,ImageDraw,ImageFont
r=Path(__file__).resolve().parent
import sys
label=sys.argv[1] if len(sys.argv)>1 else 'before'
root=r/label;out=r/'sheets';out.mkdir(exist_ok=True)
for d in sorted(root.iterdir()):
 if not (d/'review.json').is_file():continue
 data=json.loads((d/'review.json').read_text());f=data['frames']
 if not f:continue
 if d.name.endswith('player'):
  targets=([0,.25,.65,1.65,2.6,3.55,4.35,4.7,5.13,5.36,5.82,6.49] if d.name.startswith('box') else [0,.25,.72,.94,1.275,1.84,2.55,2.7,3.18,3.41,3.87,4.99])
  selected=[min(f,key=lambda x:abs(x['source']-t)) for t in targets]
 else:selected=f
 for page in range(0,len(selected),12):
  frames=selected[page:page+12];sheet=Image.new('RGB',(1380,288*((len(frames)+2)//3)),(24,28,34));draw=ImageDraw.Draw(sheet)
  for j,a in enumerate(frames):
   im=Image.open(d/a['file']).convert('RGB');im.thumbnail((460,259));x=(j%3)*460;y=(j//3)*288
   sheet.paste(im,(x,y));draw.text((x+6,y+261),f"{d.name} rt={a['runtime']:.3f} src={a['source']:.3f}",fill='white')
  sheet.save(out/f'{label}_{d.name}_{page//12}.jpg',quality=84)
 print(d.name,len(f),'frames')
