"""Read the saved village's wall transforms, preserving the current editor map."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out=root/'SourceAssets/TemperateHillsVillage/WallSupport20261114'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world(): raise RuntimeError('Active game: do not change maps')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages(): raise RuntimeError('Unsaved maps: preserve editor state')
previous=editor.get_editor_world().get_path_name().split('.')[0]
camera=editor.get_level_viewport_camera_info()
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world: raise RuntimeError('Cannot load village')
rows=[]
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=comp.static_mesh
        if not mesh or 'StoneWall' not in mesh.get_name(): continue
        ts=([comp.get_instance_transform(i,True) for i in range(comp.get_instance_count())]
            if isinstance(comp,u.InstancedStaticMeshComponent) else [comp.get_world_transform()])
        for index,t in enumerate(ts):
            r=t.rotation.rotator()
            rows.append(dict(actor=actor.get_actor_label(),component=comp.get_name(),index=index,
                mesh=mesh.get_name(),pos=[t.translation.x,t.translation.y,t.translation.z],
                rot=[r.pitch,r.yaw,r.roll],scale=[t.scale3d.x,t.scale3d.y,t.scale3d.z]))
(out/'saved-walls-before.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
if previous!=level:
    if not u.EditorLoadingAndSavingUtils.load_map(previous):raise RuntimeError('Restore map failed')
    if camera:editor.set_level_viewport_camera_info(*camera)
print('SAVED_WALLS_READ',len(rows),'restored',previous)
