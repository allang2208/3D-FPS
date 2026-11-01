import copy,struct,bpy
from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solve','exec'))
owned=('clavicle_l','upperarm_l','lowerarm_l');patch={};report={'method':'rotate shoulder around fixed elbow; retain clavicle/humerus native relation and every distal world transform','profiles':{},'owned':owned}
for family in ('skeleton_base','skeleton_mag10'):
 patch[family]=[];report['profiles'][family]={}
 for e in D['profiles'][family]['clips']:
  role=e['base'].split('.')[-1].removeprefix('A_M24_');duration=e['duration'];old={t['bone']:t for t in e['tracks']}
  # Continuous held state, with short matched entry/exit on actions that release
  # the support hand. This avoids a shoulder pop at idle -> reload/inspect.
  held=role in ('idle','aim','sprint_enter','sprint_loop','sprint_exit','fire','cycle','equip')
  def degrees(t):return 10. if held else 10.*max(1-smooth(t/.22),1-smooth((duration-t)/.22))
  times=sorted({struct.unpack('<f',struct.pack('<f',v))[0] for v in ([i/120 for i in range(round(duration*120)+1)]+[duration]+[v for n in owned if n in old for v in old[n]['times']])})
  tracks={n:{'bone':n,'times':times,'values':[]} for n in owned};last={}
  for t in times:
   row,loc=compose(e,t);fixed=rotate_root(row,degrees(t))
   for n,tr in tracks.items():
    base=raw(D['clips'][e['base']],t,n);bp,bq,bs=transform(base).decompose()
    local=fixed[parents[n]].inverted()@fixed[n];p,q,sc=(K@local@K).decompose();dq=q@bq.inverted()
    if n in last and dq.dot(last[n])<0:dq=-dq
    last[n]=dq;existing=sample(old[n],t,10,'values') if n in old else [0,0,0,0,0,0,1,0,0,0]
    dp=p-bp if n=='clavicle_l' else Vector(existing[:3]);tr['values'].extend([*dp,dq.x,dq.y,dq.z,dq.w,*existing[7:]])
  patch[family].append({'base':e['base'],'tracks':list(tracks.values())});report['profiles'][family][role]={'held':held,'degrees':10,'keys':len(times),'duration':duration}
with gzip.open(O/'arm_root_patch.json.gz','wt') as f:json.dump(patch,f)
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('M24_ARM_ROOT_AUTHORED',len(patch),flush=True)
