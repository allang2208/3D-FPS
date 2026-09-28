"""Hide only the lower cloud component; retain the sky, ocean and cloud assets."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

root=Path(__file__).parent
project=root.parents[2]
map_path='/Game/GameMaps/DayNight_Lighting'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world() if editor else None
game=editor.get_game_world() if editor else None
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if not world or world.get_path_name().split('.')[0]!=map_path:
    if game or dirty:raise RuntimeError('Preserve the current world; the hub map is not available for this edit')
    world=u.EditorLoadingAndSavingUtils.load_map(map_path)
if not world:raise RuntimeError('Cannot access the hub map')
report={'worlds':{},'saved':False,'was_dirty':map_path in dirty,'runtime_tested':False}
src=project/'Content/GameMaps/DayNight_Lighting.umap'
dst=project/'trash/godspace-cloud-hidden-20260928'/datetime.now().strftime('%H%M%S-%f')/src.name
dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
report['backup']=str(dst)
for title,target_world in [('editor',world),('game',game)]:
    if not target_world:continue
    changed=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(target_world,u.Actor):
        if 'GodSpace.CloudSea' not in [str(t) for t in actor.tags]:continue
        key='volumetric Cloud Settings'
        values=json.loads(u.ToolsetLibrary.get_object_properties(actor,[key]))
        values[key]['add Volumetric Cloud']=False
        if not u.ToolsetLibrary.set_object_properties(actor,json.dumps(values)):
            raise RuntimeError('Cannot disable the owning cloud-sea setting')
        for cloud in actor.get_components_by_class(u.VolumetricCloudComponent):
            cloud.set_visibility(False)
            cloud.set_hidden_in_game(True)
            changed.append(cloud.get_path_name())
    report['worlds'][title]=changed
if not report['worlds'].get('editor'):raise RuntimeError('No tagged lower cloud layer was found')
if not game and map_path not in dirty:
    if not u.EditorLoadingAndSavingUtils.save_map(world,map_path):raise RuntimeError('Cloud visibility map save failed')
    report['saved']=True
else:
    report['pending_save_reason']='PIE is active' if game else 'Preserve pre-existing unsaved map edits'
(root/'Receipts/cloud-sea-hidden.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_CLOUD_SEA_HIDDEN '+json.dumps(report))
