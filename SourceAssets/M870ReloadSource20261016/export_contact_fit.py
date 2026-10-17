import bpy,json,gzip,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;rest={b.name:b.matrix_local.copy() for b in r.data.bones}
with gzip.open(O.parent/'M870ReloadWrist20261016/native_arms.json.gz','rt',encoding='utf-8') as f:d=json.load(f)
auth=json.loads((O/'authoring.json').read_text());a=bpy.data.actions[auth['clips']['reload_continuous']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
shell=bpy.data.objects['M870_ReloadShell'];local_shell=[rest['WPN_Shell'].inverted()@shell.matrix_world@v.co for v in shell.data.vertices]
out={}
for f in (18,25,31,38,44):
 s.frame_set(f);p={b.name:b.matrix.copy() for b in r.pose.bones};hi=p['hand_r'].inverted();si=p['WPN_Shell'].inverted();groups={n:[] for n in ('thumb','index','middle','all')}
 for v,w in zip(d['vertices'],d['weights']):
  if sum(value for n,value in w.items() if n=='hand_r' or any(n.startswith(k+'_') and n.endswith('_r') for k in ('thumb','index','middle','ring','pinky')))<.999:continue
  vertex=Vector((v[0]/100,-v[1]/100,v[2]/100));point=hi@sum((p[n]@rest[n].inverted()@vertex*value for n,value in w.items()),Vector())
  groups['all'].append(list(point))
  for digit in ('thumb','index','middle'):
   if sum(value for n,value in w.items() if n in (digit+'_02_r',digit+'_03_r'))>.75:groups[digit].append(list(point))
 for name,points in groups.items():out[f'{f}_{name}']=np.array(points)
 out[f'{f}_hand_to_shell']=np.array(si@p['hand_r']);out[f'{f}_shell']=np.array([list(hi@p['WPN_Shell']@v) for v in local_shell])
out['triangles']=np.array([list(f.vertices) for f in shell.data.polygons]);np.savez_compressed(O/'fit_inputs.npz',**out)
print('M870_SOURCE_CONTACT_INPUTS',flush=True)
