import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Current201.fbx'),use_anim=False)
rig=next(a for a in bpy.data.objects if a.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
rows={};mag=[]
for a in list(bpy.data.objects):
 if a.type!='MESH':continue
 for mi,m in enumerate(a.data.materials):
  name=S['rigs']['201']['slots'][mi]['name'] if mi<len(S['rigs']['201']['slots']) else (m.name if m else str(mi))
  if not any(s in name for s in ['Magazine','Receiver','Handguard']):continue
  ids={i for f in a.data.polygons if f.material_index==mi for i in f.vertices}
  pts=np.array([tuple(root.inverted()@a.matrix_world@a.data.vertices[i].co) for i in ids]);
  if not len(pts):continue
  rows[name]={'bounds_root_m':[pts.min(0).tolist(),pts.max(0).tolist()],'count':len(pts)}
  if 'Magazine' in name:mag.extend(pts.tolist())
np.save(O/'Inputs/factory_mag_root.npy',np.array(mag))
rows['root_blender']=[list(r) for r in root];rows['mag_blender']=[list(r) for r in rig.matrix_world@rig.data.bones['WPN_SOCKET_Magazine'].matrix_local]
bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/DonorDrum.fbx'),use_anim=False)
donor=[a for a in bpy.context.selected_objects if a.type=='MESH']
for a in donor:
 pts=np.array([tuple(a.matrix_world@v.co) for v in a.data.vertices]);rows[a.name]={'bounds_export_m':[pts.min(0).tolist(),pts.max(0).tolist()],'verts':len(pts),'materials':[m.name if m else None for m in a.data.materials]}
 np.save(O/'Inputs/drum_export.npy',pts)
(O/'geometry_inputs.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
