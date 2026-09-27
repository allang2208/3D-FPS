"""Read the authored shrine and breach assets needed for the requested edit."""
import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/Saved/DungeonShrine20260927')
out.mkdir(parents=True,exist_ok=True)
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ue.get_editor_world()
target='/Game/GameMaps/L_Dungeon_Randomized'
if world.get_path_name().split('.')[0]!=target:
    if ue.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve current world; shrine read pending')
    world=u.EditorLoadingAndSavingUtils.load_map(target)
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    if not (label.startswith('DGN_A_') and any(k in label.lower() for k in ('ru_','ruin','ancient','breach','earth'))
            or 'Shrine' in label or 'Statue' in label or isinstance(a,u.SceneTestPortal)):
        continue
    origin,extent=a.get_actor_bounds(False)
    parts=[]
    for c in a.get_components_by_class(u.StaticMeshComponent):
        mesh=c.get_editor_property('static_mesh')
        parts.append(dict(component=c.get_name(),mesh=mesh.get_path_name() if mesh else None,
            materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],
            slots=[str(n) for n in c.get_material_slot_names()],visible=c.get_editor_property('visible')))
    rows.append(dict(label=label,actor=a.get_path_name(),tags=[str(n) for n in a.get_editor_property('tags')],
        position=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),
        scale=list(a.get_actor_scale3d().to_tuple()),bounds_center=list(origin.to_tuple()),
        bounds_extent=list(extent.to_tuple()),hidden=a.get_editor_property('hidden'),parts=parts))
(out/'scene-inputs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('SHRINE_INPUTS',len(rows),str(out/'scene-inputs.json'))
