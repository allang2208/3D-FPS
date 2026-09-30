"""Scoped, user-requested inspection of the final UE-exported lid and pouch UVs."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/SK_LMG201_R36_Installed.fbx'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted();ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');group=ob.vertex_groups.get('LMG201_Cover');v=np.array([inv@ob.matrix_world@x.co for x in ob.data.vertices]);ids=[x.index for x in ob.data.vertices if any(g.group==group.index and g.weight>.999 for g in x.groups)];q=v[ids];which=set(ids)
edges=[e.vertices[:] for e in ob.data.edges if all(vi in which for vi in e.vertices)];edges=np.array(edges);max_edge=float(np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1).max())
bad=(abs(q[:,0]-.0008)>.045)|(q[:,1]<-.25)|(q[:,1]>-.08)|(q[:,2]<.05)|(q[:,2]>.095)
cloth=[]
for i,m in enumerate(ob.data.materials):
 if 'R36_Cloth' not in m.name:continue
 faces=[p for p in ob.data.polygons if p.material_index==i];loops=[li for p in faces for li in p.loop_indices];uv=np.array([ob.data.uv_layers.active.data[li].uv[:] for li in loops]);cloth.append({'material':m.name,'faces':len(faces),'finite_uv':bool(np.isfinite(uv).all()),'uv_min':uv.min(0).tolist(),'uv_max':uv.max(0).tolist()})
report={'source':'final saved UE assembly exported after install','lid_bounds_m':np.stack([q.min(0),q.max(0)]).tolist(),'lid_vertices':len(ids),'lid_outlier_vertices':int(bad.sum()),'lid_max_edge_m':max_edge,'cloth':cloth,'animation_tracks_changed':False,'game_started':False}
(O/'saved_geometry_check.json').write_text(json.dumps(report,indent=2));print('R36_SAVED_GEOMETRY',json.dumps(report),flush=True)
if bad.any() or max_edge>.15:raise RuntimeError('Saved cover still contains an oversized spike')
if not cloth or not all(x['finite_uv'] and x['faces']>0 for x in cloth):raise RuntimeError('Pouch surface or UVs missing')
