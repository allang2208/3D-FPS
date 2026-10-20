import unreal as u,json,copy,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit';MESH=ROOT+'/SK_SVCH_SightsR2_ElbowFit';PROFILE=ROOT+'/DA_SVCH_ElbowFitGrip'
donor=u.load_asset('/Game/Weapons/SVCH/Replacement20261018/SightsR2/SK_SVCH_SightsR2')
if E.does_asset_exist(MESH):raise RuntimeError('Preserve existing revision; resume after the failed stage instead')
materials={str(s.material_slot_name):s.material_interface for s in donor.materials}
receipt={'complete':False,'saved':[]}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
 receipt['saved'].append(a.get_path_name());(O/'elbow_install_receipt.json').write_text(json.dumps(receipt,indent=2))
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.skeleton=donor.skeleton;options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O/'SK_SVCH_SightsR2_ElbowFit.fbx');task.destination_path=ROOT;task.destination_name='SK_SVCH_SightsR2_ElbowFit';task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(MESH);slots=list(mesh.materials)
for i,s in enumerate(slots):
 name=str(s.material_slot_name)
 if name=='SVCH_New_FactorySights_001':name='SVCH_New_FactorySights';s.material_slot_name=name
 s.material_interface=materials[name];slots[i]=s
mesh.set_editor_property('materials',slots);editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);editor.set_lod_build_settings(mesh,0,editor.get_lod_build_settings(donor,0));save(mesh)
arm_materials={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('MI_Manny_')}
helper=P/'SourceAssets/SVCHRefinement20261018/install_arm_correctives.py';code=helper.read_text().replace('if s>=9','if s in arm_materials');exec(compile(code,str(helper),'exec'),{'__file__':str(helper),'TARGET_MESH':MESH,'RECEIPT_PATH':O/'elbow_arm_correctives_receipt.json','arm_materials':arm_materials})
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile);profile=A.create_asset('DA_SVCH_ElbowFitGrip',ROOT,u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json((O/'profile_elbow_clearance.json').read_text()):raise RuntimeError('Cannot save fitted contact profile')
save(profile)
source=json.loads((O/'authoring_receipt.json').read_text())['landmarks_component_cm'];source['RearSight']=[a+b for a,b in zip(source['RearSight'],json.loads((O/'elbow_clearance_receipt.json').read_text())['rear_shift_component_cm'])]
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);ref=mod.get_bone_transform('WPN_root',True);cal={}
for key,p in source.items():
 v=u.MathLibrary.inverse_transform_direction(ref,u.Vector(*p)) if key=='SightUp' else u.MathLibrary.inverse_transform_location(ref,u.Vector(*p));cal[key]=[v.x,v.y,v.z]
(O/'elbow_calibration.json').write_text(json.dumps(cal,indent=2));del mod
table=P/'Content/ColdSteelData/modular_outfits.json';text=table.read_text(encoding='utf-8-sig');data=json.loads(text);entry=copy.deepcopy(data['profiles'][donor.get_path_name()]);entry['hide_source_materials']=sorted(arm_materials);data['profiles'][mesh.get_path_name()]=entry
if table.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent outfit update')
table.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,mesh=mesh.get_path_name(),profile=profile.get_path_name(),fbx_sha256=hashlib.sha256((O/'SK_SVCH_SightsR2_ElbowFit.fbx').read_bytes()).hexdigest(),source_animations_changed=False,V9_changed=False,magazine_binding_changed=False)
(O/'elbow_install_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_BOLT_FIT_SAVED',mesh.get_path_name(),flush=True)
