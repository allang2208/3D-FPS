"""Probe the live editor: PIE state and whether the combat/tool assets are loaded. Read-only."""
import unreal as u

les = u.get_editor_subsystem(u.LevelEditorSubsystem)
print('PIE_ACTIVE', bool(les and les.is_in_play_in_editor()))

paths = [
    '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe',
    '/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle',
    '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe_Skeleton',
    '/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe',
    '/Game/Items/ProductionTools/BattleAxe20260919/M_BattleAxe',
]
for path in paths:
    name = path.rsplit('/', 1)[1]
    obj = u.find_object(None, path + '.' + name)
    print('LOADED' if obj else 'not_loaded', path)

mesh = u.find_object(None, '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe.SK_Harvest_Axe')
if mesh:
    skeleton = mesh.get_editor_property('skeleton')
    print('LIVE_MESH_SKELETON', skeleton.get_path_name() if skeleton else None)
print('PROBE_DONE')