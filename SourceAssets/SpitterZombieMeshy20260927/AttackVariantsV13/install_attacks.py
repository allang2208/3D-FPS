"""Save two new clips and bind D/Fat/Nurse attack choices without starting PIE."""
import unreal as u
import ast, json, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PROJECT = BASE.parents[1]
DEST = '/Game/Monsters/SpitterZombie'
LIB = u.EditorAssetLibrary

def bind_variants(cdo, entries):
    choices = []
    for role, entry in entries.items():
        choice = u.SpitterAttackVariant()
        choice.set_editor_property('clip', u.load_asset(DEST+'/Animations/'+entry['asset_name']))
        choice.set_editor_property('contact_time', entry['contact_seconds'])
        choice.set_editor_property('contact_end', entry['contact_end_seconds'])
        choice.set_editor_property('recovery_time', entry['recovery_seconds'])
        choices.append(choice)
    cdo.set_editor_property('attack_variants', choices)

def main(bind_pool=True):
    if os.environ.get('SPITTER_HEADLESS') != '1':
        level = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():
            raise RuntimeError('PIE is active; preserving the current session')
    data = json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'))
    contract = json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
    entries = {'AttackD': json.loads((BASE/'AttackD_V12/authoring.json').read_text(encoding='utf-8'))['attack'],
               **data['attacks']}
    for entry in entries.values():
        entry.update(poison=True, poison_stacks_per_hit=1)
    bp_path = DEST+'/BP_SpitterZombie'
    targets = {DEST+'/Animations/'+e['asset_name'] for e in data['attacks'].values()}
    if bind_pool:
        targets.add(bp_path)
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty & targets:
        raise RuntimeError('Preserving unsaved asset edits: '+str(dirty & targets))
    bp = u.load_asset(bp_path)
    cdo = u.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property('visual_mesh')
    if bind_pool:
        if not hasattr(u, 'SpitterAttackVariant'):
            raise RuntimeError('The native random-attack build is not loaded; source and FBX are retained')
        cdo.get_editor_property('attack_variants')
    previous = cdo.get_editor_property('attack_clip')
    expected = json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))['animations']['Attack']
    if bind_pool and previous.get_path_name() != expected:
        raise RuntimeError('Attack binding changed outside the saved production record; preserving it')
    backup = ROOT/'Before'
    backup.mkdir(exist_ok=True)
    if bind_pool:
        for path in [PROJECT/'Content/Monsters/SpitterZombie/BP_SpitterZombie.uasset',
                     BASE/'animation_contract.json', BASE/'ue_installation.json', BASE/'production_status.json']:
            if path.exists() and not (backup/path.name).exists():
                shutil.copy2(path, backup/path.name)
    report = dict(revision=data['revision'], state='importing', saved=[], pool_bound=False,
        runtime_tested=False, preview_rendered=False, previous_attack=previous.get_path_name(),
        movements=[a.get_path_name() if a else None for a in cdo.get_editor_property('movement_clips')],
        movement_reference_speeds=list(cdo.get_editor_property('movement_reference_speeds')),
        donor_assets_modified=False, mesh_or_skin_modified=False)
    receipt = ROOT/('installation.json' if bind_pool else 'installation_clips.json')

    def record():
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    helper = BASE/'LocomotionV10/install_locomotion.py'
    tree = ast.parse(helper.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fit_container_units')
    units_scope = {'u': u, 'mesh': mesh}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(helper), 'exec'), units_scope)
    cvar = 'Interchange.FeatureFlags.Import.FBX'
    previous_cvar = u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None, cvar+' 0')
    try:
        for role, entry in data['attacks'].items():
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
            task.automated, task.save, task.replace_existing, task.replace_existing_settings = True, False, True, True
            task.options = options
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            clip = u.load_asset(DEST+'/Animations/'+entry['asset_name'])
            if clip is None:
                raise RuntimeError('Import failed: '+role)
            units_scope['fit_container_units'](clip)
            clip.set_preview_skeletal_mesh(mesh)
            clip.set_editor_property('loop', False)
            clip.set_editor_property('enable_root_motion', False)
            clip.set_editor_property('force_root_lock', True)
            LIB.set_metadata_tag(clip, 'Spitter.Revision', data['revision'])
            LIB.set_metadata_tag(clip, 'Source', entry['source'])
            if not LIB.save_loaded_asset(clip, False):
                raise RuntimeError('Save failed: '+role)
            report['saved'].append(clip.get_path_name())
            record()
    finally:
        u.SystemLibrary.execute_console_command(None, cvar+' '+str(previous_cvar))
    if not bind_pool:
        report['state'] = 'two_attack_clips_saved_native_pool_binding_pending'
        record()
        u.log('SPITTER_ATTACK_VARIANTS_CLIPS_SAVED '+json.dumps(report))
        return

    bind_variants(cdo, entries)
    default = entries['AttackD']
    cdo.set_editor_property('attack_clip', u.load_asset(DEST+'/Animations/'+default['asset_name']))
    for key, field in [('contact_time', 'contact_seconds'), ('contact_end', 'contact_end_seconds'), ('recovery_time', 'recovery_seconds')]:
        cdo.set_editor_property(key, default[field])
    LIB.set_metadata_tag(bp, 'Spitter.AttackRevision', data['revision'])
    LIB.set_metadata_tag(bp, 'Spitter.AttackMode', 'physical_melee_random_variants')
    if not LIB.save_loaded_asset(bp, False):
        raise RuntimeError('Saving the random attack configuration failed')
    report['saved'].append(bp.get_path_name())
    report.update(state='three_random_attacks_and_blueprint_saved', pool_bound=True,
        attack_variants={role: dict(asset=DEST+'/Animations/'+e['asset_name'], seconds=e['seconds'],
            contact_seconds=e['contact_seconds'], contact_end_seconds=e['contact_end_seconds'],
            recovery_seconds=e['recovery_seconds']) for role, e in entries.items()},
        selection=data['selection'], attack_damage=cdo.get_editor_property('attack_damage'),
        attack_range_base_cm=cdo.get_editor_property('attack_range'))
    record()
    for entry in entries.values():
        entry['attack_range_base_cm'] = report['attack_range_base_cm']
        entry['attack_damage'] = report['attack_damage']
    contract['AttackVariants'] = dict(revision=data['revision'], selection=data['selection'], variants=entries)
    (BASE/'animation_contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding='utf-8')
    delivery = json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))
    delivery.update(attack_revision=data['revision'], attack_mode='physical_melee_random_variants',
        attack_variants=report['attack_variants'], attack_selection=data['selection'])
    delivery['saved'] = list(dict.fromkeys(delivery['saved']+report['saved']))
    (BASE/'ue_installation.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
    status = json.loads((BASE/'production_status.json').read_text(encoding='utf-8'))
    status.update(attack_revision=data['revision'], attack_mode='physical_melee_random_variants',
        attack_variants_assets_saved=True, attack_variants_native_build='Succeeded',
        attack_variants_delivery_scope='native_build_and_three_clip_pool_saved', tested=False)
    (BASE/'production_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('SPITTER_ATTACK_VARIANTS_INSTALLED '+json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
