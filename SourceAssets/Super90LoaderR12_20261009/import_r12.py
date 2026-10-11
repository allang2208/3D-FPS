"""Save R12 loader guide, props, 15 loader clips and the loader entries of the grip profiles.

Unreal Python (commandlet or MCP bridge). The idle, quick-melee, sprint and all
other profile entries and retained overrides are preserved. No PIE, render or
validation test is run here.
"""
import json, shutil, hashlib
from pathlib import Path
import unreal as u

subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if subsystem and subsystem.get_game_world():
    raise RuntimeError('Exit PIE before replacing Super90 loader assets; no assets changed.')

O = Path(__file__).parent; P = O.parents[1]
ROOT = '/Game/Weapons/Super90/Speedloader20261007'; ANIM = ROOT + '/Animations'
E = u.EditorAssetLibrary; A = u.AssetToolsHelpers.get_asset_tools(); L = u.MaterialEditingLibrary
manifest = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
if manifest['revision'] != 'LoaderR12-20261009': raise RuntimeError('Run author_r12.py before this import.')
receipt = {'completed': False, 'revision': manifest['revision'], 'saved': [], 'profiles': {}, 'package_sha256': {}, 'runtime_tested': False}
def record(): (O / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing ' + path)
    return obj
def backup(path):
    rel = path.split('.')[0].removeprefix('/Game/') + '.uasset'
    src = P / 'Content' / rel; dst = O / 'Before' / 'Content' / rel
    if src.exists() and not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
    receipt['package_sha256'].setdefault(path.split('.')[0], {})['before'] = hashlib.sha256(src.read_bytes()).hexdigest() if src.exists() else None
def save(obj):
    if not E.save_loaded_asset(obj, False): raise RuntimeError('Save failed ' + obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']: receipt['saved'].append(obj.get_path_name())
    package = obj.get_path_name().split('.')[0]
    file = P / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    receipt['package_sha256'].setdefault(package, {})['after'] = hashlib.sha256(file.read_bytes()).hexdigest()
    record(); return obj
def tag(obj, file):
    E.set_metadata_tag(obj, 'Super90SpeedloaderSource', manifest['revision'] + '; Delta Force M1014 phases; contoured port funnel, slotted tube and grip post; native V7 arm solve')
    E.set_metadata_tag(obj, 'Super90SourceSHA256', hashlib.sha256(Path(file).read_bytes()).hexdigest())

families = ('vertical', 'canted', 'prism', 'angled')
profile_paths = {f: '/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_' + f for f in families}
targets = {ANIM + '/' + c['name'] for c in manifest['clips']}
targets.update(profile_paths.values())
targets.update([ROOT + '/SK_Super90_LoaderProps', ROOT + '/SM_Super90_LoaderGuide'])
targets.update(ROOT + '/Materials/MI_S90Loader_' + n for n in ('Steel', 'Polymer', 'Anodized'))
# An existing editor may have unsaved manual work. Refuse only an actual overlap;
# the shared bridge owns the import batch, and other packages stay untouched.
conflicts = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_path_name() in targets]
if conflicts:
    raise RuntimeError('Unsaved target packages; preserving current work: ' + ', '.join(conflicts))
for clip in manifest['clips']: backup(ANIM + '/' + clip['name'])
for path in list(profile_paths.values()) + [ROOT + '/SK_Super90_LoaderProps', ROOT + '/SM_Super90_LoaderGuide'] + \
        [ROOT + '/Materials/MI_S90Loader_' + n for n in ('Steel', 'Polymer', 'Rod', 'Anodized')]:
    backup(path)

def material(name, metal, rough, color):
    path = ROOT + '/Materials/MI_' + name
    obj = load(path) if E.does_asset_exist(path) else A.create_asset('MI_' + name, ROOT + '/Materials', u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    obj.set_editor_property('parent', load('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanAnodized'))
    values = {'Metallic': metal, 'EdgeMetallic': metal, 'Roughness': rough, 'SourceColorWeight': 0., 'SourceRoughnessWeight': 0., 'MaskUVChannel': 0.,
              'GrainTileCm': 2., 'GrainRoughness': .012, 'MottleRoughness': .005, 'MottleColor': 0., 'ScratchAmount': 0., 'HandlingPolish': 0.,
              'Stipple': 0., 'EdgeWear': 0., 'EdgeHighlight': .06, 'CavityDarken': 0., 'CavityRoughness': 0., 'AOStrength': 0., 'WeaponWetness': 0.}
    for key, value in values.items(): L.set_material_instance_scalar_parameter_value(obj, key, value)
    L.set_material_instance_vector_parameter_value(obj, 'FinishColor', u.LinearColor(*color, 1))
    L.set_material_instance_texture_parameter_value(obj, 'SurfaceNormal', load('/Engine/EngineMaterials/DefaultNormal'))
    L.set_material_instance_texture_parameter_value(obj, 'SurfaceMask', load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral'))
    L.update_material_instance(obj); E.set_metadata_tag(obj, 'Super90SurfaceStandard', 'WS1 clean finish; dedicated UVs; flat structural normal; no original gun atlas')
    return save(obj)
materials = {'S90Loader_Anodized': material('S90Loader_Anodized', 1., .48, (.030, .032, .036)),
             'S90Loader_Polymer': material('S90Loader_Polymer', 0., .62, (.018, .018, .019)),
             'S90Loader_Steel': material('S90Loader_Steel', 1., .40, (.025, .026, .028))}
LEGACY_SLOTS = {'S90Loader_Rod': 'S90Loader_Steel'}      # slot kept by reimport from the R9 prop
def assign(slots, attr):
    out = list(slots); names = []
    for i, slot in enumerate(out):
        name = str(slot.get_editor_property('material_slot_name')); names.append(name)
        key = name if name in materials else LEGACY_SLOTS.get(name)
        if key is None: raise RuntimeError('Unexpected material slot ' + name)
        slot.set_editor_property('material_interface', materials[key]); out[i] = slot
    receipt.setdefault('material_slots', {})[attr] = names
    return out

skeleton = load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7').skeleton
compression = load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag = 'Interchange.FeatureFlags.Import.FBX'; previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
def task_for(file, name, dest, opt):
    t = u.AssetImportTask(); t.filename = str(file); t.destination_name = name; t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.replace_existing_settings = True; t.save = False
    t.factory = u.FbxFactory(); t.options = opt; A.import_asset_tasks([t])
    if not t.imported_object_paths: raise RuntimeError('FBX import failed ' + name)
try:
    opt = u.FbxImportUI(); opt.automated_import_should_detect_type = False; opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh = True; opt.import_as_skeletal = False; opt.import_animations = False; opt.import_materials = False; opt.import_textures = False
    opt.static_mesh_import_data.combine_meshes = True; opt.static_mesh_import_data.auto_generate_collision = False
    opt.static_mesh_import_data.generate_lightmap_u_vs = False
    opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task_for(manifest['meshes']['guide'], 'SM_Super90_LoaderGuide', ROOT, opt)
    guide = load(ROOT + '/SM_Super90_LoaderGuide')
    guide.set_editor_property('static_materials', assign(guide.get_editor_property('static_materials'), 'static'))
    try: u.ASH12AttachmentAssetTools.disable_runtime_fast_build(guide)
    except Exception: pass
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    st = sm.get_lod_build_settings(guide, 0); st.use_full_precision_u_vs = True; st.use_high_precision_tangent_basis = True
    st.recompute_normals = False; st.recompute_tangents = False; sm.set_lod_build_settings(guide, 0, st)
    tag(guide, manifest['meshes']['guide']); save(guide)

    # Reimport keeps existing slots and matches by name: retire the R9 'Rod' slot
    # name first so the tube sections land on the anodized slot.
    if E.does_asset_exist(ROOT + '/SK_Super90_LoaderProps'):
        old = load(ROOT + '/SK_Super90_LoaderProps'); slots = list(old.get_editor_property('materials')); changed = False
        for i, slot in enumerate(slots):
            if str(slot.get_editor_property('material_slot_name')) == 'S90Loader_Rod':
                slot.set_editor_property('material_slot_name', 'S90Loader_Anodized')
                try: slot.set_editor_property('imported_material_slot_name', 'S90Loader_Anodized')
                except Exception: pass
                slots[i] = slot; changed = True
        if changed: old.set_editor_property('materials', slots)
    opt = u.FbxImportUI(); opt.automated_import_should_detect_type = False; opt.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_mesh = True; opt.import_as_skeletal = True; opt.import_animations = False; opt.import_materials = False; opt.import_textures = False
    opt.create_physics_asset = False; opt.skeleton = skeleton
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
    opt.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task_for(manifest['meshes']['props'], 'SK_Super90_LoaderProps', ROOT, opt)
    props = load(ROOT + '/SK_Super90_LoaderProps')
    props.set_editor_property('materials', assign(props.get_editor_property('materials'), 'skeletal'))
    props.set_editor_property('physics_asset', None)
    ske = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem); st = ske.get_lod_build_settings(props, 0)
    st.use_full_precision_u_vs = True; st.use_high_precision_tangent_basis = True; st.recompute_normals = False; st.recompute_tangents = False
    ske.set_lod_build_settings(props, 0, st)
    tag(props, manifest['meshes']['props']); save(props)

    for clip in manifest['clips']:
        opt = u.FbxImportUI(); opt.automated_import_should_detect_type = False; opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False; opt.import_as_skeletal = False; opt.import_animations = True; opt.import_materials = False; opt.import_textures = False
        opt.create_physics_asset = False; opt.skeleton = skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', 60)
        task_for(clip['file'], clip['name'], ANIM, opt)
        obj = load(ANIM + '/' + clip['name']); obj.set_editor_property('bone_compression_settings', compression)
        tag(obj, clip['file']); save(obj)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))

def snapshot_other_clips(asset, family):
    payload = {'family': family, 'clips': []}; retained = {}
    for clip in asset.get_editor_property('clips'):
        base = clip.get_editor_property('base').get_path_name()
        if base.startswith(ANIM + '/'): continue          # only the loader entries are replaced
        payload['clips'].append({'base': base, 'duration': float(clip.get_editor_property('duration')), 'tracks': [
            {'bone': str(t.get_editor_property('bone')), 'times': list(t.get_editor_property('times')), 'values': list(t.get_editor_property('values'))}
            for t in clip.get_editor_property('tracks')]})
        original = clip.get_editor_property('retained')
        if original: retained[base] = original.get_path_name()
    return payload, retained

for family, path in profile_paths.items():
    asset = load(path); combined, retained = snapshot_other_clips(asset, family)
    kept = len(combined['clips'])
    combined['clips'].extend(json.loads((O / (family + '_profiles.json')).read_text(encoding='utf-8'))['clips'])
    if not asset.set_shared_clips_from_json(json.dumps(combined)): raise RuntimeError('Grip extension failed ' + family)
    if retained:
        rows = list(asset.get_editor_property('clips'))
        for i, row in enumerate(rows):
            base = row.get_editor_property('base').get_path_name()
            if base in retained: row.set_editor_property('retained', load(retained[base])); rows[i] = row
        asset.set_editor_property('clips', rows)
    E.set_metadata_tag(asset, 'Super90SpeedloaderGrip', manifest['revision'] + '; loader entries replaced; idle, melee, sprint and other entries retained')
    save(asset); receipt['profiles'][family] = {'path': path, 'kept_clips': kept, 'clip_count': len(combined['clips'])}; record()
receipt['completed'] = True; record()
print('SUPER90_LOADER_R12_SAVED', len(receipt['saved']), 'assets; no gameplay test', flush=True)
