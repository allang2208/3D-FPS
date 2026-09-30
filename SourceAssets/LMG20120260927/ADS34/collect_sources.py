"""Extract only meshes and poses relevant to the reported 201 ADS deformation."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
cfg=json.loads((O.parents[2]/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
profile=cfg['profiles'][body+'.SK_LMG201_Cover10']
paths={'201':body,'shirt':cfg['items']['ue_chainmail_shirt']['rig_meshes']['PKM'],'bare':profile['native_bare_skin'],'pkm':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular','pre32':'/Game/Weapons/LMG201/Surface32/Previous/SK_LMG201_Cover10_PreS32'}
for key in ['ue_field_gloves','ue_steel_gloves']:
 recipe=cfg['items'].get(key,{})
 if recipe.get('rig_meshes',{}).get('PKM'):paths[key]=recipe['rig_meshes']['PKM']
out={'meshes':{}}
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+key)
 _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
 d={'mesh':mesh.get_path_name(),'rest':{str(b.name):dict(tr(b.world_transform),index=b.index,parent=b.parent_index) for b in bones},'materials':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
 if key in ['201','pkm','pre32']:
  path=('/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_' if key=='pkm' else '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_')
  d['poses']={}
  for name in ['idle','aim']:
   clip=u.load_asset(path+name);opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
   d['poses'][name]={str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bones}
 out['meshes'][key]=d
 if key not in ['pkm','pre32']:
  ex=u.AssetExportTask();ex.object=mesh;ex.filename=str(O/(key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=False;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
  if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Export '+key)
 print('ADS34_SOURCE',key,len(bones),flush=True)
(O/'sources.json').write_text(json.dumps(out,indent=2))
print('ADS34_SOURCES_COMPLETE',flush=True)
