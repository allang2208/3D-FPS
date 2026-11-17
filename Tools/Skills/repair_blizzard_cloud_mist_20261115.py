"""Repair Blizzard's cloud binding and ground repetition after PIE has ended."""
import importlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'SourceAssets/BlizzardCloudMistRepair20261115'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT/'Tools/Skills'))
import blizzard_cloud_visibility_recipe as clouds
import blizzard_cold_mist_recipe as mist
import blizzard_frost_surface_recipe as frost
from build_fireball_assets import API, ref


def run():
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT/'Content').resolve():
        raise RuntimeError('Use the FPSGAME content author host')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        (OUT/'status.json').write_text(json.dumps({'state': 'waiting_for_pie_end', 'assets_saved': False}), encoding='utf8')
        print('BLIZZARD_REPAIR_WAITING_FOR_PIE_END')
        return
    for module in (clouds, mist, frost):
        importlib.reload(module)
    frost_path = '/Game/Skills/Blizzard/IndoorV5/M_BlizzardGroundFrost'
    targets = (clouds.SYSTEM, mist.SYSTEM, frost_path)
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(targets):
        raise RuntimeError('Preserve unsaved Blizzard edits: '+str(sorted(dirty.intersection(targets))))
    for target in targets:
        relative = target.removeprefix('/Game/')+'.uasset'
        source, backup = ROOT/'Content'/relative, OUT/'BeforeAssets'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(source, backup)
    cloud_system, mist_system, frost_material = [u.load_asset(p) for p in targets]
    material = u.load_asset(mist.MATERIAL)
    if not all((cloud_system, mist_system, frost_material, material)):
        raise RuntimeError('Missing installed Blizzard input')
    profiles = {'cloud': clouds.apply(cloud_system), 'mist': mist.apply(mist_system, material),
                'frost': frost.apply(frost_material)}
    if not u.PoisonMaggotMonster.compile_material_assets([frost_material]):
        raise RuntimeError('Blizzard frost material compile failed')
    for system in (cloud_system, mist_system):
        if not u.RainAssetEditor.compile_rain(system, True):
            raise RuntimeError('Blizzard Niagara compile failed: '+system.get_path_name())
    bindings = {}
    for name in clouds.LAYERS:
        data = json.loads(API.call_method('GetRendererData', (ref(cloud_system, name, renderer=0),)).get_editor_property('property_values'))
        row = {}
        for key, expected in [('SpriteAlignmentBinding', 'Particles.SpriteAlignment'), ('UVScaleBinding', 'Particles.SpriteUVScale')]:
            value = data[key]
            row[key] = {'attribute': value['paramMapVariable']['name'], 'exists': value['bBindingExistsOnSource']}
            if row[key]['attribute'] != expected or not row[key]['exists']:
                raise RuntimeError('Unresolved Blizzard renderer binding: '+name+'/'+key)
        bindings[name] = row
    states = {}
    for system in (cloud_system, mist_system):
        state = API.call_method('GetSystemCompileState', (system,)).get_editor_property('value')
        states[system.get_name()] = state.export_text()
        if state.get_editor_property('has_errors') or state.get_editor_property('is_compiling'):
            raise RuntimeError('Incomplete Blizzard compile: '+system.get_name())
    for asset in (frost_material, cloud_system, mist_system):
        if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('Blizzard save failed: '+asset.get_path_name())
    receipt = {'state': 'saved', 'saved_at': datetime.now().isoformat(), 'saved_assets': list(targets),
               'profiles': profiles, 'cloud_bindings': bindings, 'compile_states': states,
               'targeted_asset_checks': True, 'gameplay_tested': False, 'rendered': False,
               'native_source_modified': False, 'new_editor_started': False,
               'preserved': ['cloud artwork and timing', 'snow', 'ice shatter', 'damage', 'range', 'duration', 'network authority']}
    (OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (OUT/'status.json').write_text(json.dumps({'state': 'saved', 'assets_saved': True}), encoding='utf8')
    print('BLIZZARD_CLOUD_MIST_REPAIR_SAVED '+json.dumps(receipt))


if __name__ == '__main__':
    run()
