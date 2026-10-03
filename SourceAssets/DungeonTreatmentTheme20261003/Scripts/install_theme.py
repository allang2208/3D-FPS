"""Promote accepted treatment authoring into the saved production generator.

No Generate/PIE/render, and no edits to the retained subject map.
Use the existing bridge, or a mutex-protected Python commandlet.
"""
import hashlib
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Preserve active play session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve unsaved editor maps')

rules = runpy.run_path(str(ROOT / 'Scripts/extend_catalog.py'))
data = rules['release']()
for source, stage in ((data['container_source'], 'maps_saved'),
                      (data['chest_source'], 'maps_saved')):
    receipt = ROOT.parent / source / 'Receipts/install.json'
    if json.loads(receipt.read_text('utf-8'))['stage'] != stage:
        raise RuntimeError('Install and save the dependent assets first: ' + source)

original = editor.get_editor_world()
original = original.get_path_name().split('.')[0] if original else ''
backup = ROOT / 'Backup'
backup.mkdir(parents=True, exist_ok=True)
receipts = ROOT / 'Receipts'
receipts.mkdir(parents=True, exist_ok=True)

try:
    world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
    generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
    if len(generators) != 1:
        raise RuntimeError('Saved production generator unavailable')
    generator = generators[0]
    before = generator.get_editor_property('module_catalog_json')
    catalog = rules['extend'](json.loads(before))
    owned = [m for m in catalog['modules'] if m['id'] in data['sequence']]
    hard = {a.get_path_name(): a for a in generator.get_editor_property('module_assets') if a}
    for path in sorted(set(rules['asset_paths'](owned))):
        obj = u.load_asset(path)
        if not obj:
            raise RuntimeError('Required treatment asset unavailable: ' + path)
        hard[obj.get_path_name()] = obj
    source = PROJECT / 'Content/GameMaps/L_Dungeon_Randomized.umap'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    snapshot = backup / ('L_Dungeon_Randomized-' + digest[:12] + '.umap')
    if not snapshot.exists():
        shutil.copy2(source, snapshot)
    (backup / ('catalog-' + hashlib.sha256(before.encode()).hexdigest()[:12] + '.json')).write_text(before, encoding='utf-8')
    generator.modify()
    generator.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
    generator.set_editor_property('module_assets', list(hard.values()))
    if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
        raise RuntimeError('Production map save failed')
    receipt = dict(stage='map_saved', revision=data['revision'], map=TARGET,
                   route=data['sequence'], retained_subject=data['retained_subject'],
                   previous_sha256=digest, tests_run=False, rendered=False,
                   generated=False, editor_started=False)
    (receipts / 'install.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'Config/accepted-modules.json').write_text(json.dumps(dict(revision=data['revision'], modules=owned), ensure_ascii=False, indent=2), encoding='utf-8')
    print('TREATMENT_THEME_SAVED ' + data['revision'], flush=True)
finally:
    if original and u.EditorAssetLibrary.does_asset_exist(original):
        u.EditorLoadingAndSavingUtils.load_map(original)
