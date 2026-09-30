"""Capture the installed 201 and its authored aim pose for the reported ADS issue."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')
clip=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_aim')
dm,res=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
out={'mesh':mesh.get_path_name(),'clip':clip.get_path_name(),'aim':{},'rest':{},'materials':[]}
for b in bones:
 name=str(b.name);out['rest'][name]=tr(b.world_transform)
 out['aim'][name]=tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD))
out['materials']=[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]
(O/'aim.json').write_text(json.dumps(out,indent=2))
t=u.AssetExportTask();t.object=mesh;t.filename=str(O/'SK_LMG201_ADS31_Before.fbx');t.automated=True;t.prompt=False;t.replace_identical=True
t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.export_morph_targets=False;t.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Current surface source export failed')
print('ADS31_SOURCE_READY',out['clip'],len(out['rest']),flush=True)
