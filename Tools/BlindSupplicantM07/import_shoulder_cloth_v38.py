"""Import and save the shoulder-fixed V38 capture and proxy attachment masks."""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'ShoulderClothV38';REPORT=OUT/'ue_shoulder_cloth_delivery_v38.json'
DEST='/Game/Monsters/BlindSupplicantM07'
MESH=DEST+'/SK_M07_BodyMotionV18';BP=DEST+'/BP_BlindSupplicantM07'
PROXY=DEST+'/Working/SK_M07_ClothProxyV38'
LIB=u.EditorAssetLibrary
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V38 belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('M07_V38_PIE_PRESERVED')
    if any(p.get_path_name() in (MESH,BP,PROXY) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 target packages preserved.')
# Resolve the native entry point before changing loaded assets.
build=u.BlindSupplicantAuthoring.build_witch_style_membrane
mesh=u.load_asset(MESH);bp=u.load_asset(BP)
witch=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
template=next((c for c in witch.get_editor_property('mesh_clothing_assets') if c.get_name().startswith('WitchRebuilt_LowerDrape07')),None)
if not template:raise RuntimeError('Installed Witch lower-drape reference is absent.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
skeleton=mesh.get_editor_property('skeleton');physics=mesh.get_editor_property('physics_asset')
materials={str(s.get_editor_property('imported_material_slot_name')):s.material_interface for s in mesh.materials}
# V38 also binds the body material's fold strips to cloth. Every bound material
# needs a clothing shader permutation, including mostly skinned body sections.
for material in materials.values():
    if not u.MaterialEditingLibrary.has_material_usage(material,u.MaterialUsage.MATUSAGE_CLOTHING):
        if any(p.get_path_name()==material.get_path_name().split('.')[0]
               for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Unsaved M07 cloth material preserved: '+material.get_path_name())
        u.MaterialEditingLibrary.set_base_material_usage(material,u.MaterialUsage.MATUSAGE_CLOTHING,True)
        errors=u.MaterialEditingLibrary.recompile_material(material)
        if errors:raise RuntimeError('M07 cloth material compilation failed: '+str(errors))
        if not LIB.save_loaded_asset(material,False):raise RuntimeError('M07 cloth material save failed.')
for asset in (MESH,BP):
    source=PROJECT/'Content'/Path(asset.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/source.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
report=dict(revision='ShoulderClothV38',saved=False,assets=[],reference_cloth=template.get_path_name(),
    prior_cloth_assets=[c.get_path_name() for c in mesh.get_editor_property('mesh_clothing_assets')],
    retained_settings={p:defaults.get_editor_property(p) for p in ('walk_speed','chase_speed','source_walk_speed','source_chase_speed',
        'attack_damage','attack_range','magic_attack','fireball_damage_multiplier','ice_column_damage_multiplier','lightning_damage_multiplier')},
    retained_clips={p:defaults.get_editor_property(p).get_path_name() for p in ('idle_clip','slow_walk_clip','chase_clip',
        'melee_left_clip','melee_right_clip','magic_gather_clip','magic_release_clip','death_clip')},
    geometry_modified=False,v35_weights_retained=True,vertex_alpha_authored=True,hidden_proxy_rebuilt=True,shoulder_original_skin_anchored=True,
    runtime_tested=False,rendered=False,performance_measured=False,user_review_pending=True)
def receipt():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    path=asset.get_path_name()
    if path.split('.')[0] not in (MESH,BP,PROXY):raise RuntimeError('V38 save outside scope: '+path)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('V38 save failed: '+path)
    report['assets'].append(path);receipt()
def import_mesh(filename,target):
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=options.import_mesh=True
    options.import_animations=options.import_materials=options.import_textures=options.create_physics_asset=False
    options.skeleton=skeleton
    data=options.skeletal_mesh_import_data
    data.convert_scene=data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    task=u.AssetImportTask();task.filename=str(OUT/filename)
    task.destination_path,task.destination_name=target.rsplit('/',1)
    task.automated=True;task.save=False;task.replace_existing=task.replace_existing_settings=True
    task.options=options;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=u.load_asset(target)
    if not task.imported_object_paths or not asset or asset.get_editor_property('skeleton')!=skeleton:
        raise RuntimeError('V38 import did not retain the original skeleton: '+target)
    return asset
receipt()
proxy=import_mesh('SK_M07_ClothProxyV38.fbx',PROXY)
slots=list(proxy.materials)
for slot in slots:slot.material_interface=materials['M07_Gills']
proxy.set_editor_property('materials',slots);proxy.set_editor_property('physics_asset',physics)
save(proxy)
if mesh.get_editor_property('mesh_clothing_assets'):
    detached=json.loads(u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(mesh))
    if not detached.get('success'):raise RuntimeError(str(detached))
mesh=import_mesh('SK_M07_Display_ShoulderV38.fbx',MESH)
slots=list(mesh.materials)
for slot in slots:
    name=str(slot.get_editor_property('imported_material_slot_name'))
    if name not in materials:raise RuntimeError('Unexpected V38 material: '+name)
    slot.material_interface=materials[name]
mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
report['cloth']=json.loads(build(mesh,proxy,template,str(OUT/'cloth_manifest_v38.json')))
receipt()
if not report['cloth'].get('success'):raise RuntimeError('V38 cloth authoring failed: '+json.dumps(report['cloth']))
LIB.set_metadata_tag(mesh,'MembraneRevision','ShoulderClothV38: shoulder and upper-arm skin anchored, graded cloth release, retained V35 skin')
LIB.set_metadata_tag(mesh,'MembraneClothSource',str(OUT/'cloth_manifest_v38.json'))
save(mesh)
report.update(shoulder_mesh_checkpoint_saved=True,stage='Shoulder mesh saved; final distance LOD generation and Blueprint save pending')
receipt()
print('M07_V38_SHOULDER_MESH_CHECKPOINT_SAVED')
if not u.BlindSupplicantAuthoring.configure_distance_lods(mesh):raise RuntimeError('M07 LOD settings failed.')
mesh_editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not mesh_editor.regenerate_lod(mesh,3,False,False):raise RuntimeError('M07 distance LOD generation failed.')
if not LIB.save_loaded_asset(mesh,False):raise RuntimeError('V38 final LOD save failed.')
defaults.set_editor_property('visual_mesh',mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
defaults.set_editor_property('use_coherent_gill_motion',False)
defaults.set_editor_property('cloth_resume_distance',1200.)
defaults.set_editor_property('cloth_suspend_distance',1600.)
LIB.set_metadata_tag(bp,'MembraneRevision','ShoulderClothV38: active Chaos drapes, 12m/16m distance hysteresis, 0.35s blend')
save(bp)
report.update(saved=True,stage='Shoulder-fixed cloth, distance LODs and original AI/F6 Blueprint saved',
    cloth_asset_count=len(mesh.get_editor_property('mesh_clothing_assets')),near_physics_enabled=True,
    cloth_resume_distance_cm=1200.,cloth_suspend_distance_cm=1600.,cloth_fade_seconds=.35,
    generated_lods=[dict(lod=i,vertices=mesh_editor.get_num_verts(mesh,i)) for i in range(mesh_editor.get_lod_count(mesh))])
receipt()
for name in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/name;record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(membrane_revision='ShoulderClothV38',membrane_delivery=str(REPORT),
        membrane_driver='Shoulder and upper-arm original skin anchored; continuous Witch cloth retained below graded roots',
        membrane_proxy_asset=PROXY,membrane_particle_simulation=True,runtime_tested=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V38_SHOULDER_CLOTH_SAVED '+str(REPORT))
