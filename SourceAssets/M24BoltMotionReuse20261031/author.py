"""Reuse the saved fire bolt-cycle weapon motion, with native hand contacts."""
from pathlib import Path
exec(compile((Path(__file__).parent/'motion.py').read_text().split("if __name__=='__main__':")[0],'motion','exec'))

# Carry the complete viewmodel arm chains with the receiver. This preserves
# every current local elbow, wrist, twist and finger channel exactly, including
# the distinct empty-reload and skeleton-grip contacts.
owned={'WPN_root','clavicle_l','clavicle_r'}
owned.update(n for n in names if n.startswith('ik_hand') and n!='ik_hand_root')
# Read from the current saved bolt-handle trajectories: equip is exactly three
# source frames behind fire; empty reload is 55 frames behind fire.
offsets={'equip':3,'reload_empty':55};patch={};report={}
for family in D['profiles']:
 fire=entry(family,'fire');idle=compose(entry(family,'idle'),0.)[0]['WPN_root']
 patch[family]=[]
 for role,offset in offsets.items():
  original=entry(family,role);data=D['clips'][original['base']]
  start,end=(10+offset)/30,(50+offset)/30
  times=sorted({start,end,*[i/120 for i in range(round(start*120),round(end*120)+1)]})
  tracks={n:{'bone':n,'times':times,'values':[]} for n in names if n in owned};last={}
  for time in times:
   row,_=compose(original,time);fixed=row
   if start+1e-7<time<end-1e-7:
    donor=compose(fire,time-offset/30)[0]
    delta=idle.inverted()@donor['WPN_root']
    gun=row['WPN_root']@delta;carry=gun@row['WPN_root'].inverted()
    fixed={n:m.copy() for n,m in row.items()}
    for n in names:
     if under(n,'WPN_root') or under(n,'clavicle_l') or under(n,'clavicle_r') or (n.startswith('ik_hand') and n!='ik_hand_root'):fixed[n]=carry@row[n]
   for n,track in tracks.items():
    loc=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n];p,q,s=(K@loc@K).decompose();v=raw(data,time,n)
    dq=q@Quaternion((v[6],*v[3:6])).inverted()
    if n in last and dq.dot(last[n])<0:dq=-dq
    last[n]=dq.copy();track['values'].extend([*(p-Vector(v[:3])),dq.x,dq.y,dq.z,dq.w,*(s-Vector(v[7:10]))])
  patch[family].append({'base':original['base'],'duration':original['duration'],'window':[start,end],'tracks':list(tracks.values())})
  report[family+'/'+role]={'source':fire['base'],'source_frames':[10,50],'target_frames':[10+offset,50+offset],'mechanical_frame_offset':offset,'motion_scale':1.,'sample_rate':120}
  print('BOLT_MOTION_AUTHORED',family,role,flush=True)
with gzip.open(O/'bolt_motion_patch.json.gz','wt') as f:json.dump(patch,f)
(O/'authoring.json').write_text(json.dumps({'clips':report,'owned_bones':sorted(owned),'finger_tracks':'retained','mechanical_tracks':'retained','runtime_tested':False},indent=2))
print('M24_BOLT_MOTION_REUSED',flush=True)
