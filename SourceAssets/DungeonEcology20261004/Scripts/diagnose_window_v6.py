"""Requested window-vault diagnosis in a transient loaded world; never save or play."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/Design/L_EcoNursery_Subject')
aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
panes=[]
for a in aa.get_all_level_actors():
    if isinstance(a,u.WardGlassWindow):
        c=a.get_editor_property('glass_pane');panes.append(dict(label=a.get_actor_label(),collision=str(c.get_collision_enabled())))
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
c=aa.spawn_actor_from_class(u.load_class(None,'/Script/FPSGAME.FPSGAMECharacter'),u.Vector(-1000,-230,98))
c.character_movement.set_movement_mode(u.MovementMode.MOVE_WALKING)
t=c.get_component_by_class(u.FPSTraversalComponent)
rows=[]
for x in (-1160,-1000,-820):
    for y,yaw in ((-235,-90),(-240,-90),(-365,90)):
        c.set_actor_location(u.Vector(x,y,98),False,True)
        c.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),True)
        target=t.find_target(True,True);p=target.probe
        rows.append(dict(x=x,y=y,reason=str(target.reason),action=str(target.action),obstacle=target.obstacle.get_owner().get_actor_label() if target.obstacle else None,
            probe={k:str(p.get_editor_property(k)) for k in ('height','depth','edge_distance','facing_dot','top_grippable','top_standing_space','approach_clear','vault_path_clear','landing_standing_space','mantle_path_clear')}))
(ROOT/'Receipts/window-diagnosis-v6.json').write_text(json.dumps(dict(panes=panes,rows=rows),indent=2),encoding='utf8')
print('WINDOW_DIAGNOSIS '+json.dumps(rows))
