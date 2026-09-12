import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from case import *
build=read(OUT/'build.json');report={}
def curves(a):return {(f.data_path,f.array_index):[(p.co.x,p.co.y) for p in f.keyframe_points] for la in a.layers for st in la.strips for bag in st.channelbags for f in bag.fcurves}
for key,meta in build.items():
 w,v,clip=key.split(':');interval=contact_interval(w,clip,meta['frames'])
 bpy.ops.wm.open_mainfile(filepath=meta['previous_editable']);r=bpy.data.objects['SK_M4_Infima'];old=curves(r.animation_data.action);rest={b.name:[list(x) for x in b.matrix_local] for b in r.data.bones}
 bpy.ops.wm.open_mainfile(filepath=str(Path(meta['output']).with_suffix('.blend')));r=bpy.data.objects['SK_M4_Infima'];new=curves(r.animation_data.action)
 assert rest=={b.name:[list(x) for x in b.matrix_local] for b in r.data.bones} and old.keys()==new.keys()
 nonleft=position_scale=contact=0.
 for track,values in old.items():
  other=new[track];assert [x[0] for x in values]==[x[0] for x in other];path=track[0]
  for (f,x),(_,y) in zip(values,other):
   error=abs(x-y)
   if '_l"]' not in path:nonleft=max(nonleft,error)
   if '.scale' in path or ('.location' in path and 'clavicle_l' not in path):position_scale=max(position_scale,error)
   if interval and interval[0]<=f<=interval[1] and '.rotation_quaternion' not in path:contact=max(contact,error)
  if interval and '.rotation_quaternion' in path and track[1]==0:
   # q and -q are the same rotation. Sign continuity after a changed entry
   # can choose the other representation for the untouched contact section.
   for i,(f,unused) in enumerate(values):
    if not interval[0]<=f<=interval[1]:continue
    q=[old[(path,j)][i][1] for j in range(4)];r=[new[(path,j)][i][1] for j in range(4)]
    contact=max(contact,min(max(abs(x-y) for x,y in zip(q,r)),max(abs(x+y) for x,y in zip(q,r))))
 assert nonleft==0 and position_scale==0 and contact<.00001,(key,nonleft,position_scale,contact)
 report[key]={'unchanged_nonleft':nonleft,'unchanged_joint_position_scale':position_scale,'preserved_contact_error':contact,'rest_and_key_times_preserved':True}
 (OUT/'source_validation.json').write_text(json.dumps(report,indent=2));print('SOURCE_CONTRACT_PASS',key,flush=True)
assert len(report)==36
print('SOURCE_ALL_PASS 36',flush=True)
