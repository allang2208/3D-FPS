"""Read the second-floor prop transforms and geometry bounds; no asset writes."""
import json, itertools
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
old=editor.get_editor_world();old=old.get_path_name().split('.')[0] if old else None
rows=[]
def vec(v):return [v.x,v.y,v.z]
try:
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/Design/L_ReceptionHall_Subject')
    if not world:raise RuntimeError('Cannot read reception hall')
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if not a.get_actor_label().startswith('Reception_'):continue
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh:continue
            b=c.static_mesh.get_bounds()
            transforms=[(i,c.get_instance_transform(i,True)) for i in range(c.get_instance_count())] if isinstance(c,u.InstancedStaticMeshComponent) else [(None,c.get_world_transform())]
            for index,t in transforms:
                corners=[u.MathLibrary.transform_location(t,u.Vector(b.origin.x+sx*b.box_extent.x,b.origin.y+sy*b.box_extent.y,b.origin.z+sz*b.box_extent.z)) for sx,sy,sz in itertools.product((-1,1),repeat=3)]
                lo=[min(getattr(p,k) for p in corners) for k in ('x','y','z')]
                hi=[max(getattr(p,k) for p in corners) for k in ('x','y','z')]
                if hi[2]<440 or lo[2]>750:continue
                rows.append(dict(label=a.get_actor_label(),class_name=a.get_class().get_name(),component=c.get_name(),instance=index,
                    mesh=c.static_mesh.get_path_name().split('.')[0],location=vec(t.translation),rotation=str(t.rotation.rotator()),scale=vec(t.scale3d),
                    minimum=lo,maximum=hi,collision=str(c.get_collision_enabled()),materials=[m.get_path_name() if m else None for m in c.get_materials()]))
finally:
    if not commandlet and old:u.EditorLoadingAndSavingUtils.load_map(old)
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/upper-before.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('UPPER_PROPS_READ',len(rows))
