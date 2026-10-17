"""Prepare the original M870 held pose and native V7 contact geometry."""
import bpy, json, gzip, numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;R=O.parent/'M870ReloadSource20261016'
ns={'__file__':str(R/'author_source_reload.py')}
exec(compile((R/'author_source_reload.py').read_text(encoding='utf-8').split('tree=ast.parse')[0],str(R/'author_source_reload.py'),'exec'),ns)
bpy.ops.wm.open_mainfile(filepath=str(R/'M870_ReloadSource_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
manifest={}
for folder in ('M870AKMArmSupport20261016','M870Super90Sprint20261016','M870ReloadSource20261016'):
 d=json.loads((O.parent/folder/'authoring.json').read_text(encoding='utf-8'))
 for role,entry in d['clips'].items():manifest[role]={**entry,'sample_rate':120 if role.startswith('sprint_') else 60}
a=bpy.data.actions[manifest['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in r.data.bones};idle={b.name:b.matrix.copy() for b in r.pose.bones}
p=ns['sp']['Idle'][0];C=ns['C'];hand=ns['mapped_hand'](p,C)
dep=bpy.context.evaluated_depsgraph_get();geometry={}
for n in ('M870_body','M870_trigger'):
 ob=bpy.data.objects[n];ev=ob.evaluated_get(dep);me=ev.to_mesh()
 geometry[n]={'points':[list(ev.matrix_world@v.co) for v in me.vertices],'faces':[list(f.vertices) for f in me.polygons]};ev.to_mesh_clear()
with gzip.open(O.parent/'M870ReloadWrist20261016/native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
verts=np.array([(x/100,-y/100,z/100,1) for x,y,z in skin['vertices']]);selected=[i for i,w in enumerate(skin['weights']) if sum(v for n,v in w.items() if ns['under'](n,'hand_r'))>.98]
def surface(row):
 out=np.zeros((len(verts),4))
 for n in rest:
  ids=[i for i in selected if skin['weights'][i].get(n,0)>0]
  if not ids:continue
  m=np.array(row.get(n,idle[n])@rest[n].inverted());w=np.array([skin['weights'][i][n] for i in ids])
  out[ids]+=(verts[ids]@m.T)*w[:,None]
 return out[:,:3]
source_trigger=C@p['870_trigger'].translation if '870_trigger' in p else None
print('REFERENCE_TRIGGER',list(source_trigger) if source_trigger else None,flush=True)
print('TARGET_TRIGGER_BOUNDS',np.min(geometry['M870_trigger']['points'],axis=0).tolist(),np.max(geometry['M870_trigger']['points'],axis=0).tolist(),flush=True)
print('OLD_HAND',list(idle['hand_r'].translation),'SOURCE_HAND',list(hand['hand_r'].translation),flush=True)
data={'manifest':manifest,'rest':{n:[list(v) for v in m] for n,m in rest.items()},'parents':ns['parents'],'idle':{n:[list(v) for v in m] for n,m in idle.items()},'reference_hand':{n:[list(v) for v in m] for n,m in hand.items()},'registration':[list(v) for v in C],'source_trigger':list(source_trigger) if source_trigger else None,'geometry':geometry,'native_points':verts[:,:3].tolist(),'weights':skin['weights'],'faces':skin['faces'],'hand_ids':selected,'old_points':surface(idle).tolist(),'reference_points':surface(hand).tolist()}
(O/'grip_input.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('M870_GRIP_INPUT_READY',len(selected),flush=True)
