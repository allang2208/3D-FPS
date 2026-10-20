"""Review the requested charging contact and reload-to-idle boundary."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;P=O.parents[2]
run=P/'Saved/SVCHPoseAudit'/sys.argv[1]
read=lambda f:[json.loads(s) for s in f.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
samples=read(run/'handoff.jsonl');frames=read(run/'frames.jsonl')
result=json.loads((run/'result.json').read_text(encoding='utf-8-sig'));assert result['completed'] and result['process_exit']==0
report={'runtime':str(run),'stages':{}}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for stage,end in [('normal',400/120),('empty',515/120)]:
 rows=[s for s in samples if s['stage']==stage]
 boundaries=[i for i in range(1,len(rows)) if rows[i-1]['reloading'] and not rows[i]['reloading']]
 assert len(boundaries)==1,(stage,boundaries)
 i=boundaries[0];a,b=rows[i-1:i+1]
 def delta(a,b,key):return float(np.linalg.norm(np.asarray(b[key])-a[key]))
 def rotation(a,b,key):return float(np.linalg.norm((np.asarray(b[key])-a[key]+180)%360-180))
 tail=[s for s in rows if s['reloading'] and s['source_time']>=end-.15]+rows[i:i+3]
 stats={'samples':len(rows),'last_source_time':a['source_time'],'last_action_alpha':a['action_alpha'],
  'boundary_component_step_mm':delta(a,b,'component_location')*10,
  'boundary_component_rotation_deg':rotation(a,b,'component_rotation'),
  'boundary_gun_root_step_mm':delta(a,b,'root_location')*10,
  'boundary_gun_root_rotation_deg':rotation(a,b,'root_rotation'),
  'tail_component_max_step_mm':max(delta(x,y,'component_location')*10 for x,y in zip(tail,tail[1:])),
  'tail_root_max_step_mm':max(delta(x,y,'root_location')*10 for x,y in zip(tail,tail[1:]))}
 report['stages'][stage]=stats
 role='reload_'+stage;shots=[f for f in frames if f['stage']==role];active=[f for f in shots if f['action_alpha']>.01]
 assert active and all(f['native_v9_ready'] for f in active)
 selected=[f for f in shots if active[0]['time']<=f['time']<=active[-1]['time']+1.1]
 images=[]
 for f in selected:
  im=Image.open(run/'Frames'/f['image']).convert('RGB').resize((960,540),Image.Resampling.LANCZOS)
  draw=ImageDraw.Draw(im);draw.rectangle((0,0,960,28),fill=(24,24,26))
  text=('普通换弹' if stage=='normal' else '空仓换弹')+(' · 待机' if f['action_alpha']<.01 else f" · 源时间 {f['action_time']:.2f}s")
  draw.text((10,3),text,font=font,fill='white');images.append(im)
 images[0].save(O/(role+'_handoff.gif'),save_all=True,append_images=images[1:],duration=133,loop=0,optimize=True)
 if stage=='empty':
  targets=[2.35,2.55,2.7,2.9,3.1,3.5,3.9,4.12,4.27]
  picks=[min(active,key=lambda f:abs(f['action_time']-t)) for t in targets]
  picks.append(next(f for f in shots if f['time']>active[-1]['time'] and f['action_alpha']<.01))
  sheet=Image.new('RGB',(1280,5*385),(24,24,26));draw=ImageDraw.Draw(sheet)
  for j,f in enumerate(picks):
   im=Image.open(run/'Frames'/f['image']).convert('RGB').resize((640,360),Image.Resampling.LANCZOS)
   x=j%2*640;y=j//2*385;sheet.paste(im,(x,y+25))
   draw.text((x+8,y+3),f"{f['image']} | source {f['action_time']:.3f}s | alpha {f['action_alpha']:.3f}",fill='white')
  sheet.save(O/'empty_charge_handoff.jpg',quality=94)
held=[s for s in samples if s['stage']=='empty' and s['reloading'] and 310/120<=s['source_time']<=344/120]
rel=[]
for s in held:
 bolt=s['bolt'];hand=s['hand_r'];q=R.from_quat(bolt['q'])
 rel.append(q.inv().apply(np.asarray(hand['p'])-bolt['p']))
report['held_charge_samples']=len(held)
report['held_hand_bolt_position_drift_mm']=float(max(np.linalg.norm(p-rel[0])*10 for p in rel))
(O/'runtime_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
