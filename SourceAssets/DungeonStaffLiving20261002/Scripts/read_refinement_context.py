import json,os
from pathlib import Path
import unreal as u

root=Path(r'D:/FPS3D/FPSGAME/SourceAssets/DungeonStaffLiving20261002')
print('STAFF_CONTEXT_PROCESS '+str(os.getpid()),flush=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
world=editor.get_editor_world()
play=editor.get_game_world()
data=dict(world=world.get_path_name() if world else None,playing=bool(play),game_world=play.get_path_name() if play else None,
    process_id=os.getpid(),
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_staff_assets=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                        if p.get_path_name().startswith('/Game/Dungeons/StaffLiving20261002/')])
cfg=json.loads((root/'Config/room.json').read_text('utf8'))
data['loaded_staff_maps']={}
paths=list(cfg.get('maps',{}).values())
if cfg.get('sample_map'):paths.append(cfg['sample_map'])
if cfg.get('production_map'):paths.append(cfg['production_map'])
for path in paths:
    obj=u.find_object(None,path+'.'+path.rsplit('/',1)[-1])
    data['loaded_staff_maps'][path]=obj.get_path_name() if obj else None
(root/'Receipts/refinement-context.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print('STAFF_REFINEMENT_CONTEXT '+json.dumps(data))
