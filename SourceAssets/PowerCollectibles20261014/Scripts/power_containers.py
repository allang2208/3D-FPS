"""Power-area maintenance containers, in module-local UE centimetres."""
import copy

OWNER = 'power_collectibles_20261014'
PREFIX = 'PowerTheme20261004RefineV2.GeneratorHall.MaintenanceToolbox'
BODY = '/Game/Dungeons/IncineratorContainers20261003/Meshes/SM_Treatment_ToolBox_Body'
LID = '/Game/Dungeons/IncineratorContainers20261003/Meshes/SM_Treatment_ToolBox_Lid'
TOOLBOXES = [
    dict(type='scene_container', container_id=PREFIX + '.Ground',
         caption='发电机检修工具箱', position=[850, 990, 0.3], yaw=0,
         body=BODY, door=LID, hinge=[0, 18, 32], opening_motion='Lid',
         opened_roll=108, storage_pages=1, initial_open_fraction=0),
    dict(type='scene_container', container_id=PREFIX + '.Upper',
         caption='高台检修工具箱', position=[650, -990, 241.4], yaw=180,
         body=BODY, door=LID, hinge=[0, 18, 32], opening_motion='Lid',
         opened_roll=108, storage_pages=1, initial_open_fraction=0),
]


def patch_document(document):
    result = copy.deepcopy(document)
    room = next(m for m in result['modules'] if m['id'] == 'GeneratorHall')
    owned = {b['container_id'] for b in TOOLBOXES}
    room['runtime_actors'] = [a for a in room.get('runtime_actors', [])
                              if a.get('container_id') not in owned] + copy.deepcopy(TOOLBOXES)
    room['runtime_assets'] = list(dict.fromkeys(room.get('runtime_assets', []) + [BODY, LID]))
    clear = [box for box in room.get('scene_keep_clear', []) if box.get('owner') != OWNER]
    # The lower hatch is on the opposite side of the room. Upper placement is
    # inside the gallery, between its columns and clear of the stair mouths.
    for box in TOOLBOXES:
        x, y, z = box['position']
        clear.append(dict(min=[x-55, y-80, z-5], max=[x+55, y+80, z+100], owner=OWNER))
    room['scene_keep_clear'] = clear
    room['power_collectibles_revision'] = OWNER
    if 'module_asset_paths' in result:
        result['module_asset_paths'] = sorted(set(result['module_asset_paths']) | {BODY, LID})
    return result
