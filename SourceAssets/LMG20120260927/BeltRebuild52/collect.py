"""Read-only snapshot of the current body, native reference/idle and feed enclosure."""
import unreal as u,json,gzip,hashlib,collections
from pathlib import Path
O=Path(__file__).parent
P=O.parents[2]
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
asset=u.load_asset(BODY)
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
assert status==u.GeometryScriptOutcomePins.SUCCESS
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
clip=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle')
pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,u.AnimPoseEvaluationOptions(optional_skeletal_mesh=asset,evaluation_type=u.AnimDataEvalType.SOURCE))
idle={b.index:u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD) for b in bones}
ref={b.index:b.world_transform for b in bones}
root=idle[next(b.index for b in bones if str(b.name)=='WPN_root')]
slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in asset.materials]
out={'body':BODY,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),
 'slots':slots,'bones':[{'name':str(b.name),'index':b.index,'rest':tr(b.world_transform),'idle':tr(idle[b.index])} for b in bones]}
_,tl,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
alltris=u.GeometryScript_List.convert_triangle_list_to_array(tl)
triangles=[];selected=set();counts=collections.Counter()
for ti,t in enumerate(alltris):
 m,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
 if not valid:continue
 n=slots[m]['name'];counts[n]+=1
 if not n.startswith('M_LMG201_') or any(a in n for a in ['__NewBox','__NewBelt','__OldBelt','M_LMG201_Feed__','Magazine']):continue
 triangles.append([t.x,t.y,t.z,m]);selected.update([t.x,t.y,t.z])
positions={}
for vi in sorted(selected):
 p,valid=u.GeometryScript_MeshQueries.get_vertex_position(dm,vi)
 _,weights,valid=u.GeometryScript_BoneWeights.get_vertex_bone_weights(dm,vi)
 posed=u.Vector()
 for w in weights:
  if w.weight>0:posed+=idle[w.bone_index].transform_location(ref[w.bone_index].inverse_transform_location(p))*w.weight
 positions[vi]=list(root.inverse_transform_location(posed).to_tuple())
out['triangles_by_slot']=dict(counts)
out['editor_game_world']=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
(O/'source.json').write_text(json.dumps(out,indent=2))
with gzip.open(O/'context.json.gz','wt') as f:json.dump({'positions_root_m':positions,'triangles':triangles,'slots':slots},f)
print('BELT52_SOURCE',out['sha256'],len(positions),len(triangles),'PIE',out['editor_game_world'],flush=True)
