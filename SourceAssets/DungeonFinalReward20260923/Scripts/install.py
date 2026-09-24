"""Save the current live catalog with the reward annex; no preview/play/test generation."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Unexpected Unreal project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active game; installation pending')
if list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
    raise RuntimeError('Preserve unsaved maps; installation pending')
if any(TARGET.lower() in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved dungeon content')
receipt=json.loads((ROOT/'Receipts/import.json').read_text(encoding='utf-8'))
if receipt['stage']!='meshes_saved':raise RuntimeError('Complete asset import before installation')
backup=ROOT/'Sources/L_Dungeon_Randomized-before-final-reward.umap'
if not backup.exists():shutil.copy2(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',backup)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Unable to load dungeon for authoring')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one authored generator')
g=generators[0]
previous=g.get_editor_property('module_catalog_json')
backup=ROOT/'Sources/catalog-before-final-reward.json'
if not backup.exists():backup.write_text(previous,encoding='utf-8')
overlay=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=overlay['extend'](json.loads(previous))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for path in set(overlay['asset_paths'](catalog)):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Final-room dependency missing: '+path)
    assets[asset.get_path_name()]=asset
g.modify()
g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
# BeginPlay generates a fresh layout through the existing staged loader. Saving
# the catalog suffices; an editor preview would be unsolicited runtime validation.
packages=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in packages if TARGET.lower() in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):
    raise RuntimeError('Could not save dungeon-owned packages')
if not u.EditorAssetLibrary.save_loaded_asset(world,False):raise RuntimeError('Could not save dungeon map')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
(ROOT/'Receipts/catalog-candidate.json').write_text(text,encoding='utf-8')
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(text,encoding='utf-8')
receipt=dict(stage='map_saved',map=TARGET,final_reward_rooms=1,door_lift_cm=340,
    chest='animated_open_only',rewards_configured=False,return_map='/Game/GameMaps/DayNight_Lighting',
    preview_generated=False,runtime_tested=False,rendered=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FINAL_REWARD_MAP_SAVED',json.dumps(receipt),flush=True)
