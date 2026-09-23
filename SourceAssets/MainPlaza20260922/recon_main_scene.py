"""Read-only recon of the main hub scene before laying out the marble plaza.

No actor spawn, no asset edit, no level save, no PIE. Writes recon.json next to this file
and prints one summary line. Reuses the access conventions proven by
SourceAssets/SquareAltar20260922/place_hub_altar.py.
"""
import json
from pathlib import Path

import unreal

HERE = Path(__file__).parent
PROPS = '/Game/Props/RomanColumn20260915'
FOUNTAIN = '/Game/Props/RomanFountain20260917'
ALTAR = '/Game/Props/SquareAltar20260922'

MESHES = [
    PROPS + '/SM_RomanColumn_Round_20',
    PROPS + '/SM_RomanColumn_Detailed',
    PROPS + '/SM_RomanColumn',
    PROPS + '/SM_Colonnade_Entablature',
    PROPS + '/SM_MarbleFloorTiles',
    PROPS + '/SM_BalustradeSegment_20',
    PROPS + '/SM_Balustrade_Rail',
    PROPS + '/SM_Balustrade_Plinth',
    PROPS + '/SM_RomanBaluster_Small',
    PROPS + '/SM_RomanRail_100',
    PROPS + '/SM_RomanRail_200',
    PROPS + '/SM_RomanRail_300',
    PROPS + '/SM_RomanPavilionFull_20',
    PROPS + '/SM_RomanPavilionBase_20',
    PROPS + '/SM_BronzeTorch',
    FOUNTAIN + '/SM_RomanFountain_20',
    FOUNTAIN + '/SM_FountainPolishedV9',
    FOUNTAIN + '/OverflowV7/SM_FountainOverflowV7',
    ALTAR + '/SM_SquareAltar',
]

KEYS = ('roman', 'fountain', 'altar', 'column', 'pavilion', 'balustrade', 'marble')


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def info(a):
    center, extent = a.get_actor_bounds(False)
    return dict(label=a.get_actor_label(), cls=a.get_class().get_name(),
                loc=vec(a.get_actor_location()), center=vec(center), extent=vec(extent),
                tags=[str(t) for t in a.tags])


def mesh_path(a):
    if not isinstance(a, unreal.StaticMeshActor):
        return ''
    comp = a.static_mesh_component
    mesh = comp.static_mesh if comp else None
    return mesh.get_path_name() if mesh else ''


result = {}
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_editor_world()
result['world'] = world.get_path_name() if world else None
result['pie_active'] = editor.get_game_world() is not None
result['dirty_maps'] = [p.get_path_name()
                        for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
result['actor_count'] = len(actors)

starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
result['playerstarts'] = [info(a) for a in starts]
yaw = starts[0].get_actor_rotation().yaw if starts else None
result['playerstart_yaw'] = yaw

floor = next((a for a in actors if a.get_actor_label() == 'Floor'), None)
result['floor'] = info(floor) if floor else None

result['altar_tagged'] = [info(a) for a in actors
                          if 'ColdSteel.ExpeditionAltar' in [str(t) for t in a.tags]]

props = []
for a in actors:
    label = a.get_actor_label()
    mp = mesh_path(a)
    if any(k in label.lower() for k in KEYS) or any(k in mp for k in KEYS):
        props.append(dict(label=label, cls=a.get_class().get_name(), mesh=mp,
                          loc=vec(a.get_actor_location())))
result['props_in_scene'] = props[:50]

if starts:
    origin = starts[0].get_actor_location()
    near = [info(a) for a in actors
            if not isinstance(a, unreal.PlayerStart) and (a.get_actor_location() - origin).length() < 3000]
    result['near_playerstart_3000'] = near[:60]

bounds = {}
missing = []
for path in MESHES:
    mesh = unreal.load_asset(path)
    if mesh is None:
        missing.append(path)
        continue
    box = mesh.get_bounding_box()
    bounds[path] = dict(min=vec(box.min), max=vec(box.max), size=vec(box.max - box.min))
result['mesh_bounds'] = bounds
result['missing_meshes'] = missing

(HERE / 'recon.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('RECON_OK actors=%d props=%d meshes=%d missing=%d dirty=%s pie=%s'
      % (len(actors), len(props), len(bounds), len(missing),
         result['dirty_maps'], result['pie_active']))
