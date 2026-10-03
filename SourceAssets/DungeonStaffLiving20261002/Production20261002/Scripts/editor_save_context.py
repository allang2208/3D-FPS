"""Read the existing editor state needed to save the authorized production map."""
import json,os
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world();game=editor.get_game_world()
data=dict(process_id=os.getpid(),world=world.get_path_name() if world else None,
    playing=bool(game),game_world=game.get_path_name() if game else None,
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
cfg=json.loads((ROOT.parent/'Config/room.json').read_text('utf8'))
targets=list(cfg.get('maps',{}).values())+[cfg.get('sample_map'),'/Game/GameMaps/L_Dungeon_Randomized']
data['loaded_target_maps']={}
for path in targets:
    if not path:continue
    obj=u.find_object(None,path+'.'+path.rsplit('/',1)[-1])
    if obj:data['loaded_target_maps'][path]=obj.get_path_name()
(ROOT/'Receipts/editor-save-context.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_PRODUCTION_SAVE_CONTEXT '+json.dumps(data),flush=True)
