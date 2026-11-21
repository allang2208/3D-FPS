"""Move the ground-floor lantern in the saved workshop without replacing the building."""
import json
import shutil
import sys
from pathlib import Path

import unreal as u

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path[:0] = [str(here), str(here.parent/'VillageBlacksmith'), str(here.parent/'AbandonedVillage')]
from carpenter_pendant import replace_hand_lantern

level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
map_file = root/('Content/'+level.removeprefix('/Game/')+'.umap')
stamp = map_file.stat().st_mtime_ns
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if (editor and editor.get_game_world()) or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserving the active play session or unsaved map')
plan = json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
house = next(h for h in plan['houses'] if h[0] == plan['carpenter']['house'])
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not load '+level)
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
assembly = next(a for a in actors.get_all_level_actors()
                if a.get_actor_label()=='Village_Carpenter_Repaired' and 'VillageCarpenter.Assembly' in map(str,a.tags))
report = replace_hand_lantern(house,assembly)

backup = root/'Saved/VillageCarpenter/Before'/str(stamp)/map_file.name
backup.parent.mkdir(parents=True,exist_ok=True)
if map_file.stat().st_mtime_ns != stamp:
    raise RuntimeError('Village changed on disk during the lantern refit')
if not backup.exists():
    shutil.copy2(map_file,backup)
if map_file.stat().st_mtime_ns != stamp or not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save the current village revision')
receipt = root/'SourceAssets/HillsVillageCarpenter/village-saved.json'
saved = json.loads(receipt.read_text(encoding='utf-8'))
saved['ground_floor_lantern'] = report
receipt.write_text(json.dumps(saved, ensure_ascii=False, indent=2),encoding='utf-8')
u.log('CARPENTER_CEILING_LANTERN_SAVED '+json.dumps(report))
