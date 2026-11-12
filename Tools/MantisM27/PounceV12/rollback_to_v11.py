"""Restore only the pounce slots replaced by V12 after user feedback."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV12')
prior = json.loads((ROOT / 'ue_receipt.json').read_text(encoding='utf-8'))
report = {'reason': 'User prefers V11; V12 rejected', 'blueprints': {}, 'runtime_tested': False}
L = u.EditorAssetLibrary

def path(obj):
    return obj.get_path_name() if obj else None

def receipt():
    (ROOT / 'rollback_to_v11_receipt.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        conflicts = dirty.intersection(prior['blueprints'])
        if conflicts:
            raise RuntimeError('Preserve unsaved target packages: ' + ', '.join(sorted(conflicts)))
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Preserve running PIE; defer asset update')
    targets = []
    for bp_path, recorded in prior['blueprints'].items():
        bp = u.load_asset(bp_path)
        if not bp:
            raise RuntimeError('Missing Blueprint: ' + bp_path)
        cdo = u.get_default_object(bp.generated_class())
        restored = {}
        current = {}
        for prop, old_path in recorded['previous'].items():
            current[prop] = path(cdo.get_editor_property(prop))
            if current[prop] not in (recorded['assigned'][prop], old_path):
                raise RuntimeError('Pounce changed since V12; preserve ' + bp_path + ':' + prop)
            clip = u.load_asset(old_path)
            if not clip:
                raise RuntimeError('Missing V11 clip: ' + old_path)
            restored[prop] = clip
        report['blueprints'][bp_path] = {
            'saved': False, 'previous': current,
            'restored': {prop: path(clip) for prop, clip in restored.items()},
            'retained_clips': {prop: path(cdo.get_editor_property(prop)) for prop in
                ['attack_clip', 'left_slash_clip', 'right_slash_clip', 'idle_clip', 'walk_clip', 'death_clip']}}
        targets.append((bp_path, bp, cdo, restored))
    receipt()
    for bp_path, bp, cdo, restored in targets:
        for prop, clip in restored.items():
            cdo.set_editor_property(prop, clip)
        L.set_metadata_tag(bp, 'PounceRevision', 'PounceV11 restored: user rejected V12; other clips retained')
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        if not L.save_loaded_asset(bp, False):
            raise RuntimeError('Blueprint save failed: ' + bp_path)
        report['blueprints'][bp_path]['saved'] = True
        receipt()
        print('M27_POUNCE_V11_RESTORED ' + bp_path, flush=True)
    report['rollback_saved'] = True
    receipt()
except Exception as error:
    report['error'] = str(error)
    receipt()
    raise
