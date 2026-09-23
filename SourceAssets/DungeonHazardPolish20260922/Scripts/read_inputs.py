import unreal as u,json
import gc
from pathlib import Path
root=Path(__file__).resolve().parents[1];(root/'Sources').mkdir(parents=True,exist_ok=True)
world=None;gc.collect()
target='/Game/GameMaps/L_Dungeon_AuthoredExpansion'
ed=u.get_editor_subsystem(u.LevelEditorSubsystem);ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve running game while preparing scene authoring')
if ue.get_editor_world().get_path_name().split('.')[0]!=target:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map before switching to dungeon')
    if not ed.load_level(target):raise RuntimeError('Dungeon map load failed')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
result={'world':world.get_path_name(),'play':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'actors':[]}
result['native_hazard_ready']=bool(u.load_class(None,'/Script/FPSGAME.DungeonPusChannel'))
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    p=a.get_actor_location();label=a.get_actor_label()
    comps=a.get_components_by_class(u.StaticMeshComponent)
    if not comps:continue
    statue_hint=any(word in label.lower() for word in ('statue','goddess','神像')) or any(c.static_mesh and any(word in c.static_mesh.get_name().lower() for word in ('statue','goddess')) for c in comps)
    if not (label.startswith(('DGN_RS_ShoredBreach','DGN_RS_Drainage')) or (4480<p.x<4950 and -4520<p.y<-3900) or statue_hint):continue
    rot=a.get_actor_rotation()
    rec={'label':label,'path':a.get_path_name(),'class':a.get_class().get_path_name(),'location':list(p.to_tuple()),'rotation':dict(pitch=rot.pitch,yaw=rot.yaw,roll=rot.roll),'scale':list(a.get_actor_scale3d().to_tuple()),'components':[]}
    for c in comps:
        mesh=c.static_mesh
        if mesh:rec['components'].append({'name':c.get_name(),'mesh':mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],'bounds':str(mesh.get_bounds())})
    result['actors'].append(rec)
(root/'Sources/scene.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('DUNGEON_INPUTS_SAVED',result['world'],len(result['actors']))
world=None;a=None;comps=None;c=None;mesh=None;gc.collect()
