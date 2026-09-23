"""Measure source connection surfaces and retain a private modular authoring scene."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVDCompletion20260923/SVD_Complete_Editable.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
r.animation_data.action=bpy.data.actions['A_SVD_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted();ob=bpy.data.objects['SM_SVD_Body']
pts=[inv@ob.matrix_world@v.co for v in ob.data.vertices]
parent=list(range(len(pts)))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for e in ob.data.edges:a,b=map(root,e.vertices);parent[a]=b
groups={}
for v in ob.data.vertices:groups.setdefault(root(v.index),[]).append(v.index)
def bounds(vs):return {'min':[min(v[k] for v in vs) for k in range(3)],'max':[max(v[k] for v in vs) for k in range(3)]}
islands=[dict(bounds([pts[i] for i in ids]),indices=ids) for ids in groups.values()]
sections={}
for y in [-.83,-.81,-.79,-.75,-.45,-.40,-.35,-.30,-.25,-.15,-.10,-.05,0]:
 values=[p for p in pts if abs(p.y-y)<.003]
 if values:sections[str(y)]=bounds(values)
report={'rig':r.name,'body_bounds':bounds(pts),'islands':islands,'sections':sections,
 'idle_root': [list(v) for v in r.pose.bones['WPN_root'].matrix],
 'idle_left_hand_root':[list(v) for v in (r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix)],
 'actions':{a.name:list(a.frame_range) for a in bpy.data.actions if a.name.startswith('A_SVD_')}}
(O/'geometry_inputs.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_Modular_Editable.blend'))
print('SVD_ATTACH_SURFACES',json.dumps(sections),flush=True)
print('SVD_ATTACH_FRONT_ISLANDS',json.dumps([{k:v for k,v in a.items() if k!='indices'}|{'vertices':len(a['indices'])} for a in islands if a['min'][1]<-.70]),flush=True)
