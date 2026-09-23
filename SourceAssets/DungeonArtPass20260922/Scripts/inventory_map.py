"""Inventory the dungeon map: what assets are actually placed, and where the gaps are.

Read-only. Opens L_Dungeon_AuthoredExpansion and dumps
  * actor counts by class and by folder,
  * every static mesh used with its instance count (aggregated across the map),
  * lights and decals with their key properties,
  * a per-room listing of the three new room shells (which were authored as bare
    architecture with hidden anchors, no props),
  * the hidden content anchors so later dressing knows where the intended slots are.

Run headless:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import unreal as u

TARGET = '/Game/GameMaps/L_Dungeon_AuthoredExpansion'
OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonArtPass20260922/Receipts')
OUT.mkdir(parents=True, exist_ok=True)

UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)
AA = u.get_editor_subsystem(u.EditorActorSubsystem)

world = UE.get_editor_world()
if not world or world.get_path_name().split('.')[0] != TARGET:
    if not ED.load_level(TARGET):
        raise RuntimeError('Cannot open %s' % TARGET)


def vec(v):
    return [round(float(v.x), 1), round(float(v.y), 1), round(float(v.z), 1)]


actors = list(AA.get_all_level_actors())
by_class = Counter()
by_folder = Counter()
meshes = Counter()
mesh_locations = defaultdict(list)
lights = []
decals = []
anchors = []
props = []

for actor in actors:
    cls = actor.get_class().get_name()
    by_class[cls] += 1
    folder = str(actor.get_folder_path()) or '<root>'
    by_folder[folder] += 1
    label = actor.get_actor_label()

    if 'TargetPoint' in cls:
        anchors.append({'label': label, 'folder': folder, 'location': vec(actor.get_actor_location()),
                        'tags': [str(t) for t in actor.get_editor_property('tags')]})
        continue
    if 'Light' in cls and 'StaticMesh' not in cls:
        comp = None
        for candidate in actor.get_components_by_class(u.LightComponentBase):
            comp = candidate
        entry = {'label': label, 'class': cls, 'folder': folder, 'location': vec(actor.get_actor_location())}
        try:
            entry['intensity'] = round(float(actor.get_editor_property('point_light_component').get_intensity()), 1) \
                if 'PointLight' in cls else None
        except Exception:  # noqa: BLE001
            entry['intensity'] = None
        lights.append(entry)
        continue
    if 'Decal' in cls:
        decals.append({'label': label, 'folder': folder, 'location': vec(actor.get_actor_location())})
        continue

    comp = None
    for candidate in actor.get_components_by_class(u.StaticMeshComponent):
        comp = candidate
        break
    if comp and comp.static_mesh:
        path = comp.static_mesh.get_path_name().split('.')[0]
        meshes[path] += 1
        mesh_locations[path].append({'actor': label, 'folder': folder, 'location': vec(actor.get_actor_location()),
                                     'materials': [m.get_path_name().split('.')[0] if m else None
                                                   for m in comp.get_editor_property('override_materials') if True]})
        if folder.startswith('DungeonRoomShells'):
            props.append({'actor': label, 'folder': folder, 'mesh': path,
                          'location': vec(actor.get_actor_location())})

report = {
    'map': TARGET,
    'total_actors': len(actors),
    'by_class': dict(by_class.most_common()),
    'by_folder': dict(by_folder.most_common()),
    'unique_static_meshes': len(meshes),
    'static_mesh_usage': dict(meshes.most_common()),
    'lights': lights,
    'light_count': len(lights),
    'decals': decals,
    'decal_count': len(decals),
    'anchors': anchors,
    'anchor_count': len(anchors),
    'room_shell_actors': props,
    'room_shell_actor_count': len(props),
}
(OUT / 'map-inventory.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

print('MAP_INVENTORY', json.dumps({'total': len(actors), 'unique_meshes': len(meshes),
                                   'lights': len(lights), 'decals': len(decals), 'anchors': len(anchors),
                                   'room_shell_actors': len(props)}))
print('--- by class ---')
for k, v in by_class.most_common(15):
    print('%5d  %s' % (v, k))
print('--- by folder ---')
for k, v in by_folder.most_common(15):
    print('%5d  %s' % (v, k))
print('--- anchors ---')
for a in anchors:
    print('%-42s %s' % (a['label'], a['location']))
print('--- room shell actors (meshes only) ---')
for p in props:
    print('%-40s %-46s %s' % (p['actor'], p['mesh'].split('/')[-1], p['location']))
