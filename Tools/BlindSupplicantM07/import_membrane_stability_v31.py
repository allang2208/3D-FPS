"""Rebind the retained visible M07 mesh to its repaired, bounded cloth proxy."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'MembraneStabilityV31'
MANIFEST=OUT/'Proxy/proxy_manifest_v31.json'
REPORT=OUT/'ue_membrane_delivery_v31.json'
DEST='/Game/Monsters/BlindSupplicantM07'
MESH=DEST+'/SK_M07_BodyMotionV18'
SIM=DEST+'/Working/SK_M07_ClothBuildSource_MembraneV31'
BP=DEST+'/BP_BlindSupplicantM07'
LIB=u.EditorAssetLibrary
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 membrane belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('M07_V31_PIE_PRESERVED')
    if any(p.get_path_name() in (MESH,SIM,BP) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 mesh/proxy/Blueprint edits preserved.')
manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
for asset in (MESH,BP):
    source=PROJECT/'Content'/Path(asset.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/source.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
mesh=u.load_asset(MESH)
bp=u.load_asset(BP)
defaults=u.get_default_object(bp.generated_class())
skeleton=mesh.get_editor_property('skeleton')
report=dict(revision='MembraneStabilityV31',saved=False,assets=[],mesh=MESH,
    source_manifest=str(MANIFEST),source_inspection=str(OUT/'source_membrane_diagnosis_v31.json'),
    previous_clearance_degrees=defaults.get_editor_property('gill_clearance_angle_degrees'),
    retained_actions={p:defaults.get_editor_property(p).get_path_name() for p in (
        'idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip',
        'magic_gather_clip','magic_release_clip','death_clip','wall_listen_clip')},
    display_geometry_modified=False,display_weights_modified=False,uv_modified=False,
    reference_pose_modified=False,native_code_modified=False,requested_source_inspection=True,
    runtime_tested=False,rendered=False,user_review_pending=True)


def receipt():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def save(asset):
    name=asset.get_path_name()
    if name.split('.')[0] not in (MESH,SIM,BP):raise RuntimeError('V31 save outside scope: '+name)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('V31 save failed: '+name)
    report['assets'].append(name);receipt()


receipt()
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=options.import_mesh=True
options.import_animations=options.import_materials=options.import_textures=options.create_physics_asset=False
options.skeleton=skeleton
data=options.skeletal_mesh_import_data
data.convert_scene=data.convert_scene_unit=True
data.import_uniform_scale=1.
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.set_editor_property('use_t0_as_ref_pose',False)
data.set_editor_property('update_skeleton_reference_pose',False)
task=u.AssetImportTask()
task.filename=manifest['simulation_fbx']
task.destination_path=DEST+'/Working'
task.destination_name=SIM.split('/')[-1]
task.automated=task.replace_existing=task.replace_existing_settings=True
task.save=False
task.options,task.factory=options,u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
simulation=u.load_asset(SIM)
if not simulation or not task.imported_object_paths or simulation.get_editor_property('skeleton')!=skeleton:
    raise RuntimeError('V31 proxy import failed.')
slots=list(simulation.materials)
for slot in slots:slot.material_interface=u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07')
simulation.set_editor_property('materials',slots)
simulation.set_editor_property('physics_asset',mesh.get_editor_property('physics_asset'))
save(simulation)
report['cloth']=json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(
    mesh,simulation,manifest['cloth_manifest']))
if not report['cloth'].get('success'):raise RuntimeError('V31 cloth bind failed: '+json.dumps(report['cloth']))
receipt()
for cloth in mesh.get_editor_property('mesh_clothing_assets'):
    for key,raw in cloth.get_editor_property('cloth_configs').items():
        if str(key)!='ChaosClothConfig':continue
        # These engine objects use a base Python wrapper. Native reflected
        # names remain available even when generated snake-case aliases do not.
        config=raw
        before={}
        # Local settings only; keep the same solver, collision shapes and CCD.
        for prop,amount in (('AnimDriveStiffness',.20),('AnimDriveDamping',.35),
                            ('BendingStiffnessWeighted',.20),('BucklingStiffnessWeighted',.15)):
            weighted=config.get_editor_property(prop)
            before[prop]=[weighted.get_editor_property('Low'),weighted.get_editor_property('High')]
            weighted.set_editor_property('Low',amount);weighted.set_editor_property('High',amount)
            config.set_editor_property(prop,weighted)
        for prop,amount in (('DampingCoefficient',.06),('LocalDampingCoefficient',.28),('AngularVelocityScale',.25)):
            before[prop]=config.get_editor_property(prop)
            config.set_editor_property(prop,amount)
        config.set_editor_property('LinearVelocityScale',u.Vector(.35,.35,.35))
        report['previous_config']=before
        report['config']=dict(anim_drive_stiffness=.20,anim_drive_damping=.35,bending_stiffness=.20,
            buckling_stiffness=.15,damping_coefficient=.06,local_damping_coefficient=.28,
            angular_velocity_scale=.25,linear_velocity_scale=.35)
if 'config' not in report:raise RuntimeError('V31 Chaos config was not updated.')
LIB.set_metadata_tag(mesh,'MembraneRevision','MembraneStabilityV31: stable hidden proxy, unsupported fragments skinned, bounded travel and damping')
save(mesh)
defaults.set_editor_property('gill_clearance_angle_degrees',6.)
LIB.set_metadata_tag(bp,'MembraneRevision','MembraneStabilityV31')
save(bp)
report.update(saved=True,stage='Repaired hidden proxy, retained visible mesh cloth binding/config and original AI/F6 Blueprint saved',
    clearance_degrees=6.,cloth_saved_with_display_package=True,
    source_proxy_vertices=manifest['simulation_vertices'],source_proxy_triangles=manifest['simulation_triangles'])
receipt()
manifest.update(ue_imported=True,ue_saved=True,ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
for filename in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/filename
    record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(membrane_revision='MembraneStabilityV31',membrane_delivery=str(REPORT),
        membrane_proxy_asset=SIM,runtime_tested=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V31_MEMBRANE_SAVED '+str(REPORT))
