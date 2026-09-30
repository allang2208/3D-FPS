"""User-requested spike/open-shell diagnosis on the actual UE assembly export."""
import bpy,numpy as np,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Exports/SK_LMG201_R38_Installed.fbx'),use_anim=False)
rig=next(ob for ob in bpy.data.objects if ob.type=='ARMATURE');inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
pieces={'receiver':[],'cover':[]};bindings=set()
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles();xf=inv@ob.matrix_world;verts=np.array([(xf@v.co)[:] for v in me.vertices]);groups={g.index:g.name for g in ob.vertex_groups}
 for label,prefix in [('receiver','M_LMG201_F37_Receiver'),('cover','M_LMG201_R38_')]:
  faces=np.array([t.vertices[:] for t in me.loop_triangles if me.materials[t.material_index] and me.materials[t.material_index].name.startswith(prefix)])
  if not len(faces):continue
  pieces[label].append(verts[faces])
  if label=='cover':
   for vi in np.unique(faces):bindings.update(groups[g.group] for g in me.vertices[int(vi)].groups if g.weight>.0001)
report={}
for label,items in pieces.items():
 if not items:raise RuntimeError('Missing saved '+label)
 tri=np.concatenate(items);v,inverse=np.unique(np.round(tri.reshape(-1,3),6),return_inverse=True,axis=0);f=inverse.reshape(-1,3);f=f[(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,2]!=f[:,0])]
 e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);edges,counts=np.unique(e,return_counts=True,axis=0)
 report[label]={'root_local_bounds':np.stack([v.min(0),v.max(0)]).tolist(),'triangles':len(f),'welded_boundary_edges':int((counts==1).sum()),'lateral_outliers_over_90mm':int((abs(v[:,0])>.09).sum()),'max_edge':float(np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1).max())}
report['cover_weight_bones']=sorted(bindings);report['game_tested']=False;report['one_to_one_accepted']=False
(O/'saved_geometry.json').write_text(json.dumps(report,indent=2));print('R38_SAVED_GEOMETRY',json.dumps(report),flush=True)
if any(x['lateral_outliers_over_90mm'] for x in [report['receiver'],report['cover']]):raise RuntimeError('Saved lateral spike remains')
if report['cover']['welded_boundary_edges']:raise RuntimeError('Saved cover contains open shell edges')
if bindings!={'LMG201_Cover'}:raise RuntimeError('Wrong cover ownership '+str(bindings))
