"""Save the V09 local gill repair while retaining the V08 rig and gameplay.

This production entry imports only the new display and hidden cloth meshes.
It reuses the saved V08 reference skeleton, twelve animation clips, V07 PBR
materials and existing AI/F6 character. No animation, navigation, reference
pose, hand/leg authoring or gameplay settings are changed. No PIE or preview
is started.
"""
import json
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
SOURCE = ROOT/'RecoveryOriginalV09'
DEST = '/Game/Monsters/BlindSupplicantM07'
REPORT = SOURCE/'ue_gill_delivery_v09.json'
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
SKELETON_PATH = DEST+'/SK_M07_ReferenceOriginalV08'
MESH_PATH = DEST+'/SK_M07_OriginalV09'
SIMULATION_PATH = DEST+'/Working/SK_M07_ClothBuildSource_OriginalV09'
PHYSICS_PATH = DEST+'/PA_M07_OriginalV09'
BP_PATH = DEST+'/BP_BlindSupplicantM07'
SAVE_PATHS = {MESH_PATH, SIMULATION_PATH, PHYSICS_PATH, BP_PATH}

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V09 gill production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving the M07 local gill repair.')

report = {
    'revision': 'original_gills_v09',
    'scope': 'Local original-source gill geometry, skin and cloth repair only',
    'saved': False,
    'assets': [],
    'tested': False,
    'runtime_tested': False,
    'visual_tested': False,
    'user_accepted_model': False,
    'user_review_pending': True,
    'feedback': 'V08 overall improves, but back organic membranes contain triangular spikes and rough unresolved regions.',
    'feedback_image': 'C:/Users/allan/AppData/Local/Temp/codex-clipboard-c2057cf9-1093-470d-9548-6b36ef6815b2.png',
    'original_model': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
    'reference_skeleton_reused': SKELETON_PATH,
    'reference_pose_update_requested': False,
    'animations_reimported': False,
    'navigation_modified': False,
    'hand_and_leg_authoring_modified': False,
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def package_path(asset):
    return asset.get_path_name().split('.', 1)[0]


def save(asset):
    # Saving the reused skeleton/materials/animations is outside this revision.
    if asset is None or package_path(asset) not in SAVE_PATHS:
        raise RuntimeError('M07 V09 gill production cannot save an asset outside its local repair ownership.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V09 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()


def mesh_options(skeleton):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('vertex_color_import_option', u.VertexColorImportOption.REPLACE)
    data.set_editor_property('use_t0_as_ref_pose', False)
    data.set_editor_property('update_skeleton_reference_pose', False)
    return options


def import_mesh(filename, name, destination, skeleton):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = destination
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = mesh_options(skeleton)
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+name)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('M07 V09 local source did not import: '+str(filename))
    if asset.skeleton != skeleton:
        raise RuntimeError('M07 V09 mesh must reuse the saved V08 reference skeleton.')
    return asset


def existing_clip_references(defaults):
    """Record the existing authored references without replacing any of them."""
    clips = {}
    for prop in ('idle_clip', 'walk_clip', 'attack_clip', 'slow_walk_clip',
                 'chase_clip', 'melee_left_clip', 'melee_right_clip',
                 'death_clip', 'wall_listen_clip'):
        asset = defaults.get_editor_property(prop)
        clips[prop] = asset.get_path_name() if asset else None
    combat = defaults.get_editor_property('combat')
    for prop in ('hit_clip', 'dizzy_clip'):
        asset = combat.get_editor_property(prop)
        clips['combat.'+prop] = asset.get_path_name() if asset else None
    knockdown = defaults.get_editor_property('knockdown')
    for prop in ('fall_clip', 'get_up_clip', 'prone_get_up_clip'):
        asset = knockdown.get_editor_property(prop)
        clips['knockdown.'+prop] = asset.get_path_name() if asset else None
    return clips


display_file = SOURCE/'SK_M07_Display_OriginalV09.fbx'
simulation_file = SOURCE/'SK_M07_ClothBuildSource_OriginalV09.fbx'
cloth_file = SOURCE/'cloth_ue_manifest_original_v09.json'
delivery_file = SOURCE/'gill_delivery_v09.json'
for filename in (display_file, simulation_file, cloth_file, delivery_file):
    if not filename.is_file():
        raise RuntimeError('Complete the local V09 gill export before UE import: '+str(filename))

skeleton = u.load_asset(SKELETON_PATH)
bp = u.load_asset(BP_PATH)
materials = {
    'M07_Body': u.load_asset(DEST+'/Materials/M07_Body_OriginalV07'),
    'M07_Gills': u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07'),
}
if not skeleton or not bp or not all(materials.values()):
    raise RuntimeError('The saved V08 reference skeleton, M07 Blueprint and original-UV V07 materials are required; V09 does not recreate them.')

report['source_delivery'] = str(delivery_file)
report['source_authoring'] = json.loads(delivery_file.read_text(encoding='utf-8-sig'))
report['materials_reused'] = {name: asset.get_path_name() for name, asset in materials.items()}
receipt()

existing_mesh = u.load_asset(MESH_PATH)
if existing_mesh:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing_mesh)
mesh = import_mesh(display_file, 'SK_M07_OriginalV09', DEST, skeleton)
simulation = import_mesh(simulation_file, 'SK_M07_ClothBuildSource_OriginalV09', DEST+'/Working', skeleton)

slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    material_name = 'M07_Body' if name == 'M07_Identity' else name
    if material_name not in materials:
        raise RuntimeError('OriginalV09 display contains an unassigned material slot: '+name)
    slot.material_interface = materials[material_name]
mesh.set_editor_property('materials', slots)

physics = json.loads(u.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
if not physics.get('success'):
    raise RuntimeError('OriginalV09 body collision authoring failed: '+json.dumps(physics))
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(
    mesh, simulation, str(cloth_file)))
if not cloth.get('success'):
    raise RuntimeError('OriginalV09 local gill binding failed: '+json.dumps(cloth))

LIB.set_metadata_tag(mesh, 'SourceRevision', 'M07 OriginalV09: local original-source gill repair; V08 reference rig and gameplay retained; user review pending')
LIB.set_metadata_tag(mesh, 'SourceModel', report['original_model'])
LIB.set_metadata_tag(mesh, 'GillRepairSource', str(delivery_file))
LIB.set_metadata_tag(mesh, 'Cloth', 'Local repaired original gill display, independent hidden six-island simulation proxy, V08 reference skeleton')
save(mesh)
save(simulation)
save(u.load_asset(PHYSICS_PATH))
physics.update({'saved': True, 'caller_must_save_packages': False})
cloth.update({'saved': True, 'caller_must_save_package': False, 'tested': False})
report.update({
    'stage': 'M07 OriginalV09 local gill display, cloth source and matching collision saved; Blueprint update pending',
    'mesh': mesh.get_path_name(),
    'simulation_mesh': simulation.get_path_name(),
    'skeleton': skeleton.get_path_name(),
    'body_physics': physics,
    'cloth': cloth,
    'display_source': str(display_file),
    'simulation_source': str(simulation_file),
    'cloth_manifest': str(cloth_file),
})
receipt()

u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
old_mesh = defaults.get_editor_property('visual_mesh')
report['previous_visual_mesh'] = old_mesh.get_path_name() if old_mesh else None
report['preserved_clip_references'] = existing_clip_references(defaults)
defaults.set_editor_property('visual_mesh', mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
LIB.set_metadata_tag(bp, 'SourceRevision', 'M07 OriginalV09 local gill repair; existing V08 twelve actions, reference skeleton, AI/F6 and gameplay settings retained; user review pending')
save(bp)

report.update({
    'stage': 'M07 OriginalV09 local gill repair saved into existing AI/F6 Blueprint; V08 actions and navigation retained; user review pending',
    'saved': True,
    'blueprint': bp.get_path_name(),
    'ai_and_f6_preserved': True,
    'animation_revision_retained': 'original_v08',
})
receipt()

for filename in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/filename
    # Read the latest record now: this local repair leaves existing motion,
    # navigation, audio, contact timing and independent production intact.
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({
        'stage': report['stage'],
        'mesh': report['mesh'],
        'gill_revision': 'original_gills_v09',
        'original_gills_v09_saved': True,
        'gill_repair_receipt': str(REPORT),
        'gill_repair_source': str(delivery_file),
        'gill_repair_scope': report['scope'],
        'user_reported_back_gill_spikes': True,
        'user_review_pending': True,
        'user_accepted_model': False,
        'runtime_tested': False,
        'visual_tested': False,
        'tested': False,
        'interacting_gills': cloth,
        'body_physics': physics,
    })
    if filename == 'gameplay_delivery.json':
        record.setdefault('character_blueprint', {})['mesh'] = report['mesh']
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

print('M07 ORIGINALV09 LOCAL GILL MESH, CLOTH AND AI/F6 VISUAL REFERENCE SAVED; V08 ACTIONS RETAINED; USER REVIEW PENDING', flush=True)
