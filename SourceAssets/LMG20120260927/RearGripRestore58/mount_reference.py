"""Extract the retained F50 factory mounting surface from its saved source."""
import bpy,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
source=O.parent/'SurfaceFinish50/Exports/SK_LMG201_F50_Parts.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
vertices={};faces=[];slots=[];offset=0
for ob in [o for o in bpy.data.objects if o.type=='MESH']:
 xf=root.inverted()@ob.matrix_world;me=ob.data;me.calc_loop_triangles()
 for t in me.loop_triangles:
  name=me.materials[t.material_index].name
  if 'FactoryRearGrip' not in name:continue
  if name not in slots:slots.append(name)
  faces.append([*[offset+i for i in t.vertices],slots.index(name)])
  for i in t.vertices:vertices[offset+i]=list(xf@me.vertices[i].co)
 offset+=len(me.vertices)
if not faces:raise RuntimeError('Factory mount missing in saved source')
with gzip.open(O/'mount.json.gz','wt') as f:json.dump({'vertices':vertices,'faces':faces,'slots':slots,'source':str(source)},f)
cap={}
for key,var in {'stable':'stable_antislip_reargrip','balanced':'balanced_reargrip','phantom':'phantom_reargrip','Body':None}.items():
 path='/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+var if var else '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
 cap[key]={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()}
if cap['Body']['sha256']!='7c09398f80c16873ac990d73b4b94688a49d61d7e0cacdbfd3afd2d7957aa19a':raise RuntimeError('Body changed after retained F50 factory source; read current mesh before fitting')
cap['reference_provenance']='F50 factory source retained unchanged by B53/M55/H56/F57; current body SHA matched F57 saved receipt.'
(O/'capture.json').write_text(json.dumps(cap,indent=2));print('R58_MOUNT_SOURCE',len(faces),flush=True)
