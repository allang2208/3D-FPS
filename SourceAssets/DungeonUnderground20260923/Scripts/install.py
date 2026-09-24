"""Save the new catalog and its authored preview; no play or regression run."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[1]
target='/Game/GameMaps/L_Dungeon_Randomized'
receipt_path=root/'Receipts/install.json'
receipt={'stage':'pending','map':target,'runtime_tested':False}
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active game; dungeon installation pending')
dirty_maps=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
if dirty_maps:raise RuntimeError('Preserve unsaved maps; dungeon installation pending')
if any(target.lower() in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved dungeon packages')
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Unable to load dungeon map for authoring')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(actors)!=1:raise RuntimeError('Expected one authored generator')
g=actors[0]
previous=g.get_editor_property('module_catalog_json');previous_assets=list(g.get_editor_property('module_assets'))
backup=root/'Sources/catalog-before-v2.json'
if not backup.exists():backup.write_text(previous,encoding='utf-8')
catalog=json.loads(previous)
stairs=json.loads((root/'Config/modules.json').read_text(encoding='utf-8'))['modules']
assets={a.get_path_name():a for a in previous_assets if a}
for module in stairs:
    for part in module['parts']:
        mesh=u.load_asset(part['mesh'])
        if not mesh:raise RuntimeError('Stair import incomplete: '+part['mesh'])
        assets[mesh.get_path_name()]=mesh
ids={m['id'] for m in stairs}
catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+stairs
catalog.update(compact_underground_boss=True,generator_version=2,branch_links=1,group_links=1)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
g.call_method('GeneratePreview')
if not g.actor_has_tag('DungeonAssembly.Ready') or g.actor_has_tag('DungeonAssembly.Failed'):
    g.set_editor_property('module_catalog_json',previous);g.set_editor_property('module_assets',previous_assets)
    raise RuntimeError('V2 authoring did not produce a complete layout; original catalog restored, map not saved')
manifest=json.loads(g.get_editor_property('layout_manifest_json'))
if manifest.get('generator_version')!=2:
    g.set_editor_property('module_catalog_json',previous);g.set_editor_property('module_assets',previous_assets)
    raise RuntimeError('Loaded binary predates V2; map not saved')
packages=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in packages if target.lower() in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Dungeon packages not saved')
if not u.EditorAssetLibrary.save_loaded_asset(world,False):raise RuntimeError('Dungeon map not saved')
routes=root.parent/'DungeonRoutes20260922'
(routes/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
registry=routes/'Config/room-extensions.json';entries=json.loads(registry.read_text(encoding='utf-8'))
entry='DungeonUnderground20260923/Config/modules.json'
if entry not in entries:entries.append(entry)
registry.write_text(json.dumps(entries,indent=2),encoding='utf-8')
receipt.update(stage='map_saved',description=g.get_editor_property('layout_description'),
               terminal_walk_cm=manifest.get('terminal_walk_cm'),boss_depth_cm=manifest.get('boss_depth_cm'),
               generator_version=manifest.get('generator_version'))
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('UNDERGROUND_DUNGEON_SAVED',json.dumps(receipt,ensure_ascii=False),flush=True)
