"""Save the pressure clip and a versioned action set, then bind the existing BP."""
from pathlib import Path

helpers = Path('D:/FPS3D/FPSGAME/Tools/BellowSacLobber/import_assets.py').read_text(encoding='utf-8')
exec(compile(helpers.split('previous_fbx=')[0], 'bellow_import_helpers', 'exec'))
SOURCE = ROOT / 'NozzleV03'
pressure = json.loads((SOURCE / 'nozzle_manifest_v03.json').read_text(encoding='utf-8'))
VERSION3 = DEST + '/V03'
REPORT = ROOT / 'Records/ue_nozzle_v03.json'
report = {'saved': [], 'runtime_tested': False, 'rendered': False}
bp = u.load_asset(DEST + '/BP_BellowSacLobber')
cdo = u.get_default_object(bp.generated_class())
current_set = cdo.get_editor_property('animation_set')
report['previous_animation_set'] = current_set.get_path_name()
previous_fbx = u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
try:
    mesh = u.load_asset(VERSION + '/SK_BellowSacLobber')
    name = 'A_BellowSacLobber_Lob_Pressure'
    options = fbx(True, mesh.skeleton)
    options.anim_sequence_import_data.set_editor_property('preserve_local_transform', True)
    clip = import_file(pressure['fbx'], name, VERSION3 + '/Animations', options, u.FbxFactory())
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('loop', False)
    clip.set_preview_skeletal_mesh(mesh)
    report['root_units'] = import_root_units(clip, mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Animation compilation failed: ' + name)
    save(clip)
    save(mesh.skeleton)
    actions = {str(key): value for key, value in current_set.get_editor_property('actions').items()}
    entry = actions['AttackLob']
    entry.set_editor_property('sequence', clip)
    actions['AttackLob'] = entry
    path = VERSION3 + '/DA_BellowSacLobber_CombatPressure'
    dataset = u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(current_set.get_path_name(), path)
    dataset.set_editor_property('actions', actions)
    save(dataset)
    cdo.set_editor_property('animation_set', dataset)
    LIB.set_metadata_tag(bp, 'BellowSacLobber.Stage', 'Combat V02 with V03 nozzle pressure animation')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report.update({'clip': clip.get_path_name(), 'animation_set': dataset.get_path_name(),
                   'blueprint': bp.get_path_name(), 'release_seconds': pressure['release_seconds'],
                   'stage': 'saved_and_bound'})
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('BELLOW_NOZZLE_V03_SAVED ' + json.dumps(report, ensure_ascii=False))
finally:
    u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX ' + str(previous_fbx))
