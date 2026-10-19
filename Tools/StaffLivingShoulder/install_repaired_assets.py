"""Import employee-only shoulder revisions and save the two existing employee Blueprints."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/StaffLivingShoulder20261017';DEST='/Game/Monsters/StaffLiving';LIB=u.EditorAssetLibrary
source=json.loads((OUT/'Diagnosis/current_assets.json').read_text(encoding='utf-8'))
report=json.loads((OUT/'ue_delivery.json').read_text(encoding='utf-8')) if (OUT/'ue_delivery.json').exists() else {'saved':[],'variants':{}}
report.update(stage='importing',runtime_tested=False,editor_gui_started=False)
def record():(OUT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
 record()
def path(obj):return obj.get_path_name() if obj else None
def contract(cdo):
 result={}
 for key in ['idle_clip','walk_clip','attack_clip']:result[key]=path(cdo.get_editor_property(key))
 for group,keys in [('combat',['hit_clip','dizzy_clip']),('knockdown',['fall_clip','get_up_clip','prone_get_up_clip'])]:
  component=cdo.get_editor_property(group)
  for key in keys:result[group+'.'+key]=path(component.get_editor_property(key))
 for key in ['max_health','attack_damage','walk_speed','level','experience_reward']:result[key]=cdo.get_editor_property(key)
 result['tags']=[str(t) for t in cdo.get_editor_property('tags')]
 mesh=cdo.get_editor_property('mesh')
 for key,prop in [('mesh_location','relative_location'),('mesh_scale','relative_scale3d')]:
  value=mesh.get_editor_property(prop);result[key]=[float(value.x),float(value.y),float(value.z)]
 return result
for role in ['FemaleA','FemaleB']:
 target=DEST+'/SK_LivingStaff'+role+'_ShoulderV02'
 if LIB.does_asset_exist(target):
  existing=u.load_asset(target)
  if existing.get_path_name() not in report['saved'] or LIB.get_metadata_tag(existing,'ProductionSource')!='StaffLivingShoulder20261017; original topology and UV; locally continuous shoulder skinning':raise RuntimeError('Preserve unowned destination mesh '+role)
 bp=u.load_asset(source[role]['bp']);cdo=u.get_default_object(bp.generated_class())
 if path(cdo.get_editor_property('visual_mesh'))!=source[role]['mesh']:raise RuntimeError('Employee mesh changed since source read: '+role)
 backup=OUT/'Before';backup.mkdir(exist_ok=True)
 package=ROOT/'Content/Monsters/StaffLiving'/('BP_LivingStaff'+role+'.uasset')
 if not (backup/package.name).exists():shutil.copy2(package,backup/package.name)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
record()
for role in ['FemaleA','FemaleB']:
 row=source[role];bp=u.load_asset(row['bp']);cdo=u.get_default_object(bp.generated_class());before=contract(cdo)
 skeleton=u.load_asset(row['skeleton']);physics=u.load_asset(row['physics']);old_mesh=u.load_asset(row['mesh'])
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
 options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
 options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
 data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
 data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.set_editor_property('import_morph_targets',False)
 name='SK_LivingStaff'+role+'_ShoulderV02';fbx=OUT/'Delivery'/(name+'.fbx')
 task=u.AssetImportTask();task.filename=str(fbx);task.destination_path=DEST;task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=False;task.options=options;task.factory=u.FbxFactory()
 if not LIB.does_asset_exist(DEST+'/'+name):u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 mesh=u.load_asset(DEST+'/'+name)
 if not isinstance(mesh,u.SkeletalMesh):raise RuntimeError('Missing imported skeletal mesh '+name)
 slots=list(mesh.get_editor_property('materials'));oldslots=list(old_mesh.get_editor_property('materials'))
 if len(slots)!=len(oldslots):raise RuntimeError('Unexpected body material slot count '+name)
 for slot,oldslot in zip(slots,oldslots):slot.material_interface=oldslot.material_interface
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
 LIB.set_metadata_tag(mesh,'ProductionSource','StaffLivingShoulder20261017; original topology and UV; locally continuous shoulder skinning')
 LIB.set_metadata_tag(mesh,'OriginalBody',row['mesh']);save(mesh)
 cdo.set_editor_property('visual_mesh',mesh);component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
 LIB.set_metadata_tag(bp,'ShoulderRepair','StaffLivingShoulder20261017; employee-only mesh revision V02')
 u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class());after=contract(cdo)
 if before!=after:
  (OUT/('contract_difference_'+role+'.json')).write_text(json.dumps({'before':before,'after':after},indent=2),encoding='utf-8')
  raise RuntimeError('Unexpected employee gameplay/animation change '+role)
 if path(cdo.get_editor_property('visual_mesh'))!=mesh.get_path_name():raise RuntimeError('VisualMesh not retained by Blueprint '+role)
 save(bp)
 report['variants'][role]={'blueprint':bp.get_path_name(),'old_mesh':row['mesh'],'new_mesh':mesh.get_path_name(),'skeleton':path(mesh.get_editor_property('skeleton')),'physics':path(mesh.get_editor_property('physics_asset')),'contract':after,'animation_and_stats_preserved':before==after,'fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest()};record()
 print('EMPLOYEE_SHOULDER_SAVED',role,mesh.get_path_name(),flush=True)
report['stage']='saved';record();print('STAFF_SHOULDERS_SAVED',len(report['saved']),flush=True)
