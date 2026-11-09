from pathlib import Path
import unreal as u,json
r=Path(__file__).resolve().parent;mesh=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular')
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index);names=[str(b.name) for b in bones]
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
profile=u.load_asset('/Game/Weapons/AnimationProfiles20261001/ue_pkm_lowpoly/DA_vertical')
layer=next(c for c in profile.get_editor_property('clips') if c.get_editor_property('base').get_name().endswith('_idle'))
clip=layer.get_editor_property('retained') or layer.get_editor_property('base')
tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in layer.get_editor_property('tracks')]
d=dict(names=names,parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones],local=[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,0.,False,mesh)],tracks=tracks,source=clip.get_path_name())
(r/'vertical_reference.json').write_text(json.dumps(d));print('VERTICAL_HOLD_CAPTURED',d['source'],len(tracks),flush=True)
