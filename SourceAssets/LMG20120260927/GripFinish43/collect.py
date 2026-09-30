import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent;P=O.parents[2];E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;(O/'Exports').mkdir(exist_ok=True)
manifest=json.loads((S/'Material21/bindings.json').read_text());targets=list(manifest['meshes']);extra={'Body':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','stable':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_stable_antislip_reargrip','balanced':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_balanced_reargrip','phantom':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_phantom_reargrip'}
targets=list(dict.fromkeys([p.split('.')[0] for p in targets]+list(extra.values())))
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=sub.get_game_world() if sub else None;dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};out={'pie':bool(world),'meshes':{},'materials':{},'runtime':[]}
for path in targets:
 a=u.load_asset(path)
 if not a:continue
 slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 out['meshes'][path]={'dirty':path in dirty,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
for key,path in extra.items():
 a=u.load_asset(path);ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Exports'/('Before_'+key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Export '+key)
paths={s['material'] for r in out['meshes'].values() for s in r['slots'] if s['material'] and '/LMG201/' in s['material']};paths.add('/Game/UI/GunsmithWorkbench/M_WeaponPreviewResolved.M_WeaponPreviewResolved')
for path in sorted(paths):
 a=u.load_asset(path);base=a.get_base_material();r={'base':base.get_path_name(),'properties':{},'nodes':[]};out['materials'][path]=r
 for key in ['used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor','two_sided','material_domain','blend_mode','shading_model']:
  try:r['properties'][key]=str(base.get_editor_property(key))
  except Exception:pass
 r['outputs']={str(p):str(L.get_material_property_input_node(base,p)) for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_EMISSIVE_COLOR]}
 for n in L.get_material_expressions(base):
  d={'class':n.get_class().get_name(),'name':n.get_name()};r['nodes'].append(d)
  for key in ['parameter_name','default_value','constant','texture','code','description','coordinate_index']:
   try:
    v=n.get_editor_property(key);d[key]=v.get_path_name() if isinstance(v,u.Object) else str(v)
   except Exception:pass
 if isinstance(a,u.MaterialInstance):
  r['scalar']={str(k):L.get_material_instance_scalar_parameter_value(a,k) for k in L.get_scalar_parameter_names(base)}
  r['vector']={str(k):str(L.get_material_instance_vector_parameter_value(a,k)) for k in L.get_vector_parameter_names(base)}
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_editor_property('skeletal_mesh_asset')
   if mesh and mesh.get_path_name().startswith('/Game/Weapons/LMG201/'):
    r={'actor':a.get_name(),'component':c.get_name(),'mesh':mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]};out['runtime'].append(r)
wet='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials';out['wet']={'asset':wet,'sha256':hashlib.sha256((P/'Content'/(wet.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()}
(O/'capture.json').write_text(json.dumps(out,indent=2))
mesh=u.load_asset(extra['Body']);dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones={str(b.name):b.world_transform for b in rows};root=bones['WPN_root']
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
poses={'reference':{n:tr(u.MathLibrary.make_relative_transform(t,root)) for n,t in bones.items()},'clips':{}}
for key in ['idle','aim']:
 clip=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_'+key);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE));root=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
 poses['clips'][key]={'bones':{n:tr(u.MathLibrary.make_relative_transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD),root)) for n in bones}}
(O/'pose_inputs.json').write_text(json.dumps(poses,indent=2));print('G43_INPUTS',json.dumps({'pie':out['pie'],'meshes':len(out['meshes']),'materials':len(out['materials']),'runtime':len(out['runtime'])}),flush=True)
