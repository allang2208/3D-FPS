"""Read the user's current failed-trigger state without changing it."""
import json
from pathlib import Path
import unreal as u

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
player = u.GameplayStatics.get_player_pawn(world, 0) if world else None
report = {'world': world.get_path_name() if world else None,
          'player': player.get_path_name() if player else None}
if player:
    report['weapon_state'] = str(player.get_weapon_state())
    report['reload'] = player.is_reloading()
    for component in player.get_components_by_class(u.ActorComponent):
        name = component.get_class().get_name()
        if name == 'PistolDualWieldComponent':
            report['hands'] = []
            try:
                hands = component.get_editor_property('hands')
            except Exception as error:
                report['hands_unavailable'] = str(error)
                hands = []
            for hand in hands:
                row = {}
                for field in ('action', 'reloading', 'action_time', 'action_rate', 'rounds', 'held', 'pending', 'reload_queued'):
                    value = hand.get_editor_property(field)
                    row[field] = value.get_path_name() if isinstance(value, u.Object) else value
                report['hands'].append(row)
        elif name == 'FPSQuickCombatComponent':
            report['quick_phase'] = str(component.get_phase())
            report['quick_age'] = component.get_action_age()
        elif name == 'FPSGunplayAnimInstance':
            pass
    report['meshes'] = []
    for c in player.get_components_by_class(u.MeshComponent):
        if not c.is_visible():
            continue
        row = {'name': c.get_name(), 'class': c.get_class().get_name(),
               'parent': c.get_attach_parent().get_name() if c.get_attach_parent() else None,
               'socket': str(c.get_attach_socket_name()),
               'location': str(c.get_world_location()), 'scale': str(c.get_world_scale())}
        if isinstance(c, u.StaticMeshComponent):
            asset = c.get_editor_property('static_mesh')
            row['asset'] = asset.get_path_name() if asset else None
        elif isinstance(c, u.SkeletalMeshComponent):
            asset = c.get_skeletal_mesh_asset()
            row['asset'] = asset.get_path_name() if asset else None
        report['meshes'].append(row)
out = Path(__file__).parents[2] / 'Saved/DualPistolQuickCombat20260920/live-failed-trigger.json'
out.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
u.log('DUAL_LIVE_TRIGGER_STATE ' + json.dumps(report, default=str))
