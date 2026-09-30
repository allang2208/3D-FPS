"""Read the currently installed, user-accepted PKM reload donor for 201 authoring."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/BeltFeed08')
M='/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular'
mesh=u.load_asset(M);dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
def tr(t):
 p=t.translation;q=t.rotation;s=t.scale3d
 return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
parents={b.index:str(b.name) for b in bones}
info={'asset':mesh.get_path_name(),'bones':{str(b.name):dict(tr(b.world_transform),parent=parents.get(b.parent_index)) for b in bones},'clips':{}}
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
for key in ['idle','reload','reload_empty']:
 a=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_'+key)
 count=1 if key=='idle' else round(a.get_play_length()*120)+1
 poses=[]
 for i in range(count):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(i/120,a.get_play_length()),opts)
  poses.append({str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bones})
 info['clips'][key]={'asset':a.get_path_name(),'duration':a.get_play_length(),'fps':120,'poses':poses}
 print('201_PKM_DONOR_READ',key,count,flush=True)
(O/'pkm_installed_donor.json').write_text(json.dumps(info,separators=(',',':')),encoding='utf8')
# Export the installed mechanical surface as an authoring source; preserve its UVs.
t=u.AssetExportTask();t.object=mesh;t.filename=str(O/'PKM_Installed_Donor.fbx');t.automated=True;t.prompt=False;t.replace_identical=True;t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.export_morph_targets=False
if not u.Exporter.run_asset_export_task(t):raise RuntimeError('PKM mesh authoring export failed')
print('201_PKM_DONOR_READY')