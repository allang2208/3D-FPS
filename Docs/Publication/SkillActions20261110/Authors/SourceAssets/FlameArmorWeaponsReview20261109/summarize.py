"""Build review contact sheets from unmodified runtime screenshots and sample data."""
import json,sys,math
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
run=ROOT/sys.argv[1]
data=json.loads((run/'runtime.json').read_bytes())
summary=[]
for case in data['cases']:
 effects=[e for s in case['samples'] for e in s['effects']]
 summary.append(dict(id=case['id'],reason=case['reason'],images=len(case['samples']),
  missing_effect_frames=sum(not s['effects'] for s in case['samples']),
  sections=sorted({a['section'] for s in case['samples'] for a in s['attachments']}),
  meshes=sorted({a['mesh'] for s in case['samples'] for a in s['attachments']}),
  maximum_anchor_error_cm=max([e['anchor_error_cm'] for e in effects if 'anchor_error_cm' in e] or [0]),
  invalid_particle_values=sum(r['invalid'] for e in effects for r in e.get('particle_samples',[])),
  live_particles=[sum(e['particles']) for e in effects]))
(run/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for shot in ['02','03','06','09']:
 for offset in range(0,len(data['cases']),6):
  group=data['cases'][offset:offset+6];sheet=Image.new('RGB',(1280,3*388),(24,24,24));draw=ImageDraw.Draw(sheet)
  for index,case in enumerate(group):
   x=(index%2)*640;y=(index//2)*388;path=run/case['id']/(shot+'.png')
   if path.exists():
    with Image.open(path) as frame:sheet.paste(frame.resize((640,360)),(x,y+28))
   draw.text((x+8,y+6),case['id']+' / '+shot,fill='white')
  sheet.save(run/('sheet-'+shot+'-'+str(offset//6+1)+'.jpg'),quality=93)
print(json.dumps([{k:v for k,v in r.items() if k not in ['meshes','live_particles']} for r in summary],ensure_ascii=False,indent=2))
