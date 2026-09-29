"""Import Attack D and save the existing zombie BP. No PIE, render or tests."""
import unreal as u
import ast, json, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PROJECT = BASE.parents[1]
DEST = '/Game/Monsters/SpitterZombie'
LIB = u.EditorAssetLibrary
entry = json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))['attack']
entry.update(poison=True, poison_stacks_per_hit=1)
bp_path = DEST+'/BP_SpitterZombie'
clip_path = DEST+'/Animations/'+entry['asset_name']
if os.environ.get('SPITTER_HEADLESS') != '1':
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('PIE is active; preserving the current session')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & {bp_path, clip_path}:
    raise RuntimeError('Preserving unsaved target edits: '+str(dirty & {bp_path, clip_path}))
bp = u.load_asset(bp_path)
if bp is None:
    raise RuntimeError('Existing Spitter BP is missing')
cdo = u.get_default_object(bp.generated_class())
mesh = cdo.get_editor_property('visual_mesh')
old_attack = cdo.get_editor_property('attack_clip')
expected = json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))['animations']['Attack']
if old_attack.get_path_name() not in [expected, clip_path+'.'+entry['asset_name']]:
    raise RuntimeError('Attack was changed outside the recorded revision; preserving that binding')
backup = PROJECT/'trash/spitter-zombie-rollbacks'/ROOT.name/'Before'
backup.mkdir(parents=True, exist_ok=True)
for file in [PROJECT/'Content/Monsters/SpitterZombie/BP_SpitterZombie.uasset',
             BASE/'animation_contract.json', BASE/'ue_installation.json', BASE/'production_status.json']:
    if file.exists() and not (backup/file.name).exists():
        shutil.copy2(file, backup/file.name)
settings = {'contact_time': entry['contact_seconds'], 'contact_end': entry['contact_end_seconds'],
            'recovery_time': entry['recovery_seconds']}
report = dict(revision=entry['revision'], state='importing', saved=[],
    previous_attack=old_attack.get_path_name(),
    previous_settings={k: cdo.get_editor_property(k) for k in settings},
    movements=[c.get_path_name() if c else None for c in cdo.get_editor_property('movement_clips')],
    movement_reference_speeds=list(cdo.get_editor_property('movement_reference_speeds')),
    mesh_or_skin_modified=False, movement_assets_modified=False, native_changed=False,
    runtime_tested=False, preview_rendered=False)

def record():
    (ROOT/'installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# This function is part of import unit conversion, not an added validation run.
helper = BASE/'LocomotionV10/install_locomotion.py'
tree = ast.parse(helper.read_text(encoding='utf-8'))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fit_container_units')
exec(compile(ast.Module(body=[function], type_ignores=[]), str(helper), 'exec'), globals())
cvar = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None, cvar+' 0')
try:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    imp = options.anim_sequence_import_data
    imp.set_editor_property('use_default_sample_rate', False)
    imp.set_editor_property('custom_sample_rate', entry['fps'])
    imp.set_editor_property('convert_scene_unit', True)
    imp.set_editor_property('remove_redundant_keys', False)
    imp.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    task.filename, task.destination_name, task.destination_path = entry['file'], entry['asset_name'], DEST+'/Animations'
    task.automated, task.save = True, False
    task.replace_existing, task.replace_existing_settings = True, True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(clip_path)
    if clip is None:
        raise RuntimeError('Attack D import did not produce an animation')
    fit_container_units(clip)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('loop', False)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    LIB.set_metadata_tag(clip, 'Spitter.Revision', entry['revision'])
    LIB.set_metadata_tag(clip, 'Source', entry['source'])
    if not LIB.save_loaded_asset(clip, False):
        raise RuntimeError('Attack D save failed')
    report['saved'].append(clip.get_path_name())
    record()
finally:
    u.SystemLibrary.execute_console_command(None, cvar+' '+str(previous))

cdo.set_editor_property('attack_clip', clip)
for name, value in settings.items():
    cdo.set_editor_property(name, value)
LIB.set_metadata_tag(bp, 'Spitter.AttackRevision', entry['revision'])
LIB.set_metadata_tag(bp, 'Spitter.AttackMode', entry['attack_mode'])
if not LIB.save_loaded_asset(bp, False):
    raise RuntimeError('Spitter blueprint save failed')
report['saved'].append(bp.get_path_name())
report.update(state='attack_d_and_blueprint_saved', attack=clip.get_path_name(), blueprint=bp.get_path_name(),
    attack_seconds=clip.get_play_length(), settings=settings,
    attack_damage=cdo.get_editor_property('attack_damage'), attack_range_base_cm=cdo.get_editor_property('attack_range'))
record()

# Update only the active attack entries, preserving locomotion and reactions.
entry['attack_damage'] = report['attack_damage']
entry['attack_range_base_cm'] = report['attack_range_base_cm']
contract = json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
contract['Attack'] = entry
(BASE/'animation_contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
delivery = json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))
delivery['animations']['Attack'] = clip.get_path_name()
delivery.update(attack_revision=entry['revision'], attack_mode=entry['attack_mode'],
    melee_settings=dict(values={**settings, 'attack_damage': report['attack_damage'],
        'attack_range': report['attack_range_base_cm']}, legacy_projectile_gate=False))
delivery['saved'] = list(dict.fromkeys(delivery['saved']+report['saved']))
(BASE/'ue_installation.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
status = json.loads((BASE/'production_status.json').read_text(encoding='utf-8'))
status.update(attack_revision=entry['revision'], attack_mode=entry['attack_mode'],
    attack_d_assets_saved=True, attack_d_delivery_scope='ue_assets_installed',
    attack_runtime_tested=False, attack_preview_rendered=False, tested=False)
(BASE/'production_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('SPITTER_ATTACK_D_V12_INSTALLED '+json.dumps(report, ensure_ascii=False))
