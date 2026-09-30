"""Read installed PKM animation donors and 201 native interfaces; no play changes."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;(O/'Inputs').mkdir(parents=True,exist_ok=True);P=O.parents[2]
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
result={'meshes':{},'clips':{}}
for family,path in [('pkm','/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular'),('201','/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')]:
 mesh=u.load_asset(path);dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);rows=sorted(rows,key=lambda b:b.index);names=[str(b.name) for b in rows]
 result['meshes'][family]={'asset':path,'sha256':sha(path),'names':names,'parents':[b.parent_index for b in rows],'rest':[tr(b.world_transform) for b in rows],'materials':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
 ex=u.AssetExportTask();ex.object=mesh;ex.filename=str(O/'Inputs'/(family+'_current.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Source export failed '+family)
 clips={'idle':'/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle','reload':'/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload','reload_empty':'/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload_empty'} if family=='pkm' else {'idle':'/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle'}
 if family=='201':
  for variant in ['vertical','canted','prism','angled']:clips[variant+'_idle']='/Game/Weapons/LMG201/Accessories22/Animations/'+variant+'/A_LMG201_'+variant+'_idle'
 for key,asset in clips.items():
  clip=u.load_asset(asset);model=clip.get_editor_property('data_model_interface');seconds=clip.get_play_length();count=model.get_number_of_keys() if 'reload' in key else 1
  opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE;poses=[]
  for i in range(count):
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,seconds*i/max(1,count-1),opts);poses.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
  data={'asset':asset,'sha256':sha(asset),'seconds':seconds,'frames':count,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator],'metadata':{str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(clip).items()},'poses':poses}
  file=O/'Inputs'/(family+'_'+key+'.json');file.write_text(json.dumps(data,separators=(',',':')));result['clips'][family+'_'+key]={'file':str(file),'asset':asset,'sha256':data['sha256'],'seconds':seconds,'frames':count,'metadata':data['metadata']};print('CLOTH33_READ',family,key,count,flush=True)
(O/'inputs.json').write_text(json.dumps(result,indent=2));print('CLOTH33_INPUTS_SAVED',flush=True)
