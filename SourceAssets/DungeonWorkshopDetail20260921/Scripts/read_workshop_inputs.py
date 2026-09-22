import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopDetail20260921')
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ue.get_editor_world()
if not w or w.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':
    raise RuntimeError('Dungeon map is not current')
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if '_WS_' not in label and 'Workshop' not in label:continue
    c=a.get_component_by_class(u.StaticMeshComponent)
    origin,extent=a.get_actor_bounds(False)
    row={'label':label,'path':a.get_path_name(),'location':list(a.get_actor_location().to_tuple()),
         'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),
         'bounds_center':list(origin.to_tuple()),'bounds_extent':list(extent.to_tuple()),
         'hidden':a.get_editor_property('hidden')}
    if c:
        row.update(mesh=c.static_mesh.get_path_name() if c.static_mesh else None,
                   materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],
                   collision=str(c.get_collision_profile_name()),visible=c.get_editor_property('visible'))
    rows.append(row)
state={'map':w.get_path_name(),'gameplay_active':bool(ue.get_game_world()),
       'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()], 'actors':rows}
(ROOT/'Receipts/workshop-inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps({'actors':len(rows),'gameplay_active':state['gameplay_active'],'dirty_maps':state['dirty_maps'],
                  'targets':[r for r in rows if any(x in r['label'] for x in ('Electrical','Bypass','ToolCart','CartDetail','PartsRack','RackContents'))]}))
