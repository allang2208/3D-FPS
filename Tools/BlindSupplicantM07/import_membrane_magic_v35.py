"""Save repaired M07 display weights and the authored spell damage profile.

Uses the existing native damage snapshot/elemental defence path. Monster
attribute contribution is baked into the final MagicAttack, matching the
project's direct-stat monster design; player attributes are never sampled.
"""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'MembraneSkinV35'
MANIFEST=OUT/'membrane_skin_manifest_v35.json'
REPORT=OUT/'ue_membrane_magic_delivery_v35.json'
DEST='/Game/Monsters/BlindSupplicantM07'
MESH=DEST+'/SK_M07_BodyMotionV18'
BP=DEST+'/BP_BlindSupplicantM07'
LIB=u.EditorAssetLibrary
PROFILE={'magic_attack':60.,'fireball_damage_multiplier':2.4,
         'ice_column_damage_multiplier':2.,'lightning_damage_multiplier':2.2}

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V35 belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('M07_V35_PIE_PRESERVED')
    if any(p.get_path_name() in (MESH,BP) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 mesh/Blueprint edits preserved.')
manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
filename=Path(manifest['display_fbx'])
if not filename.is_file() or not filename.resolve().is_relative_to(OUT.resolve()):
    raise RuntimeError('M07 V35 exported display mesh required.')
mesh=u.load_asset(MESH);bp=u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
skeleton=mesh.get_editor_property('skeleton');physics=mesh.get_editor_property('physics_asset')
materials={str(s.get_editor_property('imported_material_slot_name')):s.material_interface for s in mesh.materials}
before={p:defaults.get_editor_property(p) for p in PROFILE}
intake=json.loads((OUT/'current_ue_source.json').read_text(encoding='utf-8'))['settings']
for prop in PROFILE:
    if min(abs(before[prop]-intake[prop]),abs(before[prop]-PROFILE[prop]))>.001:
        raise RuntimeError('M07 spell configuration changed since intake: '+prop)
for asset in (MESH,BP):
    original=PROJECT/'Content'/Path(asset.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/original.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(original,backup)
report=dict(revision='MembraneSkinMagicV35',saved=False,assets=[],source_manifest=str(MANIFEST),
    previous_magic=before,magic_profile=PROFILE,magic_attack_semantics='Final monster magic attack including baked attribute contribution',
    spell_damage_before_defence={'fireball':144.,'ice_column':120.,'lightning':132.},
    retained_clips={p:defaults.get_editor_property(p).get_path_name() for p in (
        'idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip','magic_gather_clip','magic_release_clip','death_clip','wall_listen_clip')},
    retained_combat={p:defaults.get_editor_property(p) for p in ('walk_speed','chase_speed','source_walk_speed','source_chase_speed',
        'attack_damage','attack_range','left_contact_time','right_contact_time','contact_window_seconds','melee_playback_rate',
        'fireball_cooldown','ice_column_cooldown','lightning_cooldown','use_player_skill_cooldowns')},
    mesh_geometry_modified=False,mesh_weights_modified=True,reference_pose_modified=False,
    new_runtime_simulation=False,native_code_modified=False,runtime_tested=False,rendered=False,user_review_pending=True)
def receipt():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    name=asset.get_path_name()
    if name.split('.')[0] not in (MESH,BP):raise RuntimeError('M07 V35 save outside scope: '+name)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('M07 V35 save failed: '+name)
    report['assets'].append(name);receipt()
receipt()
if mesh.get_editor_property('mesh_clothing_assets'):
    raise RuntimeError('Expected V34 continuous skin. A later cloth edit was preserved.')
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
data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
data.set_editor_property('use_t0_as_ref_pose',False)
data.set_editor_property('update_skeleton_reference_pose',False)
task=u.AssetImportTask()
task.filename=str(filename);task.destination_name='SK_M07_BodyMotionV18';task.destination_path=DEST
task.automated=True;task.save=False
task.replace_existing=task.replace_existing_settings=True
task.options=options;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset(MESH)
if not mesh or not task.imported_object_paths or mesh.get_editor_property('skeleton')!=skeleton:
    raise RuntimeError('M07 V35 import did not preserve the original skeleton.')
slots=list(mesh.materials)
for slot in slots:
    name=str(slot.get_editor_property('imported_material_slot_name'))
    if name not in materials:raise RuntimeError('M07 V35 unexpected material slot: '+name)
    slot.material_interface=materials[name]
mesh.set_editor_property('materials',slots)
mesh.set_editor_property('physics_asset',physics)
if not u.BlindSupplicantAuthoring.configure_distance_lods(mesh):
    raise RuntimeError('M07 original distance LOD settings could not apply.')
mesh_editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not mesh_editor.regenerate_lod(mesh,3,False,False):
    raise RuntimeError('M07 corrected skin distance LOD build did not complete.')
LIB.set_metadata_tag(mesh,'MembraneRevision','V35 repaired lower folded skin: thorax support, common lower leaf weights and unified seams')
LIB.set_metadata_tag(mesh,'MembraneSkinSource',str(MANIFEST))
save(mesh)
defaults.set_editor_property('visual_mesh',mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
for prop,value in PROFILE.items():defaults.set_editor_property(prop,value)
LIB.set_metadata_tag(bp,'MembraneRevision','MembraneSkinV35')
LIB.set_metadata_tag(bp,'MagicDamageRevision','V35 final MATK 60; fire x2.4, ice x2.0, lightning x2.2; normal elemental mitigation')
save(bp)
report.update(saved=True,stage='Repaired mesh, regenerated distance LODs and original AI/F6 spell profile saved',
    mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics_asset=physics.get_path_name(),
    cloth_assets=len(mesh.get_editor_property('mesh_clothing_assets')),
    generated_lods=[{'lod':i,'vertices':mesh_editor.get_num_verts(mesh,i)} for i in range(mesh_editor.get_lod_count(mesh))])
receipt()
manifest.update(ue_imported=True,ue_saved=True,ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/name;record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(membrane_revision='MembraneSkinV35',membrane_delivery=str(REPORT),
        membrane_driver='Thorax-supported common lower skin with bounded existing leaf motion',
        magic_damage_revision='FinalMagicAttackV35',magic_damage_profile=PROFILE,magic_damage_delivery=str(REPORT),
        runtime_tested=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V35_MEMBRANE_MAGIC_SAVED '+str(REPORT))
