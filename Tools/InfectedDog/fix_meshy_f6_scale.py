"""Repair and save the 21 MeshyV2 animations responsible for invisible F6 dogs."""
import gc
import json
import shutil
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meshy_animation_units import match_bind_root_scale


def main():
    project = Path('D:/FPS3D/FPSGAME')
    root = project/'SourceAssets/InfectedDogMeshy20260924/CompletionV2'
    dest = '/Game/Monsters/InfectedDog/MeshyV2'
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('End PIE before saving repaired animation assets')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(dest + '/Animations/') for p in dirty):
        raise RuntimeError('Preserving unsaved animation edits')
    mesh = u.load_asset(dest+'/SK_InfectedDog_MeshyV2')
    authoring = json.loads((root/'animation_authoring.json').read_text(encoding='utf-8'))
    report = {'cause': 'FBX animation root scale 1 versus bind root scale 100',
              'state': 'repairing', 'clips': {}, 'spawn_code_changed': False,
              'gameplay_regression_run': False}
    report_path = root/'f6_scale_repair.json'
    def record():
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    record()
    for role in authoring['clips']:
        name = 'A_InfectedDogMeshy_' + role
        path = dest+'/Animations/'+name
        clip = u.load_asset(path)
        before = root/'BeforeF6RootScale'/f'{name}.uasset'
        if not before.exists():
            before.parent.mkdir(exist_ok=True)
            shutil.copy2(project/'Content/Monsters/InfectedDog/MeshyV2/Animations'/f'{name}.uasset', before)
        result = match_bind_root_scale(clip, mesh)
        if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
            raise RuntimeError('Failed to save ' + path)
        result['asset'] = path
        result['saved'] = True
        report['clips'][role] = result
        record()
    report['state'] = 'all_21_animation_roots_corrected_and_saved'
    record()
    print('MESHY_F6_SCALE_REPAIR_SAVED ' + str(len(report['clips'])))


main()
gc.collect()
