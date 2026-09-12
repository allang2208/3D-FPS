import bpy,json,sys
from pathlib import Path
O=Path(__file__).parent/'Final';sys.path.insert(0,str(O))
build=json.loads((O/'build.json').read_text());results={}
def curves(action):
 return {(fc.data_path,fc.array_index):[(p.co.x,p.co.y) for p in fc.keyframe_points] for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
def preserve_interval(weapon,clip,meta):
 if 'reload' not in clip:return None
 return [28 if clip.startswith('drum') else 16,meta['frames']-24] if weapon=='m4' else [42,380 if 'empty' in clip else 270]
for key,meta in build.items():
 weapon,clip=key.split(':')
 bpy.ops.wm.open_mainfile(filepath=meta['previous_editable']);r=bpy.data.objects['SK_M4_Infima'];old=curves(r.animation_data.action)
 source_rest={b.name:[list(row) for row in b.matrix_local] for b in r.data.bones}
 bpy.ops.wm.open_mainfile(filepath=str(Path(meta['output']).with_suffix('.blend')));r=bpy.data.objects['SK_M4_Infima'];new=curves(r.animation_data.action)
 assert old.keys()==new.keys();assert source_rest=={b.name:[list(row) for row in b.matrix_local] for b in r.data.bones}
 unchanged=contacts=scale_location=0.;interval=preserve_interval(weapon,clip,meta)
 for track,values in old.items():
  other=new[track];assert len(values)==len(other)
  assert [x[0] for x in values]==[x[0] for x in other]
  path=track[0];left='_l"]' in path
  for (time,x),(_,y) in zip(values,other):
   error=abs(x-y)
   if not left:unchanged=max(unchanged,error)
   if '.scale' in path or ('.location' in path and 'clavicle_l' not in path):scale_location=max(scale_location,error)
   if interval and interval[0]<=time<=interval[1]:contacts=max(contacts,error)
 assert unchanged==0 and scale_location==0 and contacts<.00001,(key,unchanged,scale_location,contacts)
 results[key]={'unchanged_nonleft_tracks':unchanged,'unchanged_joint_locations_and_scale':scale_location,'reload_contact_track_error':contacts,'frames_and_rest_preserved':True}
 (O/'source_validation.json').write_text(json.dumps(results,indent=2));print('SOURCE_CONTRACT_PASS',key,flush=True)
assert len(results)==18
print('SOURCE_ALL_PASS 18',flush=True)
