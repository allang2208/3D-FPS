import sys
from pathlib import Path
exec(compile((Path(__file__).parent/'audit.py').read_text().split("\nif __name__=='__main__':")[0],'audit','exec'))
e0=entry('skeleton_base','idle');r0=compose(e0,0)[0];g0=(r0['WPN_root']@rest['WPN_root'].inverted()).inverted()
rh0=g0@r0['hand_r'];ref={n:g0@r0[n] for n in names if under(n,'hand_r')}
report={'families':{},'surface_frames':{},'note':'Saved data-model poses plus saved profile tracks; held windows only. Bolt/melee release intentionally excluded.'}
frames=[]
for family in ('skeleton_base','skeleton_mag10'):
 report['families'][family]={}
 for e in D['profiles'][family]['clips']:
  role=e['base'].split('.')[-1].removeprefix('A_M24_');count=0;held=0;worst=0;maxbone=0;heldtimes=[]
  for time in np.linspace(0,e['duration'],max(3,math.ceil(e['duration']*30)+1)):
   row,_=compose(e,float(time));inv=(row['WPN_root']@rest['WPN_root'].inverted()).inverted();h=inv@row['hand_r'];count+=1
   offset=(h.translation-rh0.translation).length;angle=h.to_quaternion().rotation_difference(rh0.to_quaternion()).angle
   if offset>.002 or angle>math.radians(3):continue
   held+=1;heldtimes.append(float(time));worst=max(worst,offset*1000)
   maxbone=max(maxbone,max(((inv@row[n]).translation-ref[n].translation).length*1000 for n in ref))
  report['families'][family][role]={'sample_count':count,'held_samples':held,'hand_anchor_max_change_mm':worst,'finger_bone_max_change_mm':maxbone,'held_times':heldtimes}
  if heldtimes and family=='skeleton_base':frames.append((role,heldtimes[len(heldtimes)//2]))
  print('HOLD_SCAN',family,role,held,count,round(worst,4),round(maxbone,4),flush=True)
# Inspect representative held surfaces and return frames; invariant hand poses
# share the baseline result while wrist-weighted thumb-web vertices can still move.
selected=[(r,t) for r,t in frames if r in ('idle','aim','sprint_enter','sprint_loop','sprint_exit','reload','inspect','fire','equip','reload_empty')]
for role,time in selected:
 X,row=source_pose('skeleton_base',role,time)
 report['surface_frames'][role]={'time':time,'Default':metric(X,'Default'),'receiver':metric(X,'receiver')}
 print('SURFACE',role,report['surface_frames'][role]['Default']['max_penetration_mm'],report['surface_frames'][role]['receiver']['max_penetration_mm'],flush=True)
 if role=='sprint_loop':render(X,'sprint_hold_back',view='back')
(O/'motion_review.json').write_text(json.dumps(report,indent=2));print('RIGHT_GRIP_SWEEP_DONE',flush=True)
