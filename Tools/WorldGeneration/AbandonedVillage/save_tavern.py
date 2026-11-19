"""Replace the instances belonging to House 02 in the currently saved village."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import unreal as u


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent/'VillageBlacksmith')]
from author_shop import BENCH, CRATE, KIT, shell_transform
from layout_geometry import house_geometry, plot_geometry, rotate
from tavern_shell import build_tavern, set_tavern_vision, SITE_TAG


source = ROOT/'SourceAssets/TemperateHillsVillage'
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
house = next(h for h in plan['houses'] if h[0]==plan['tavern']['house'])
pieces = kit[house[2]]
scale = plan['house_scale']
original = house_geometry(house,pieces,scale)
shape = plot_geometry(house,pieces,plan)
level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
map_file = ROOT/('Content/'+level.removeprefix('/Game/')+'.umap')
stamp = map_file.stat().st_mtime_ns
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Open level has unsaved changes')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Village is in use by a play session')
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Cannot load '+level)
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
current = list(actors.get_all_level_actors())
vision = next(a for a in current if a.get_actor_label().startswith('Village_InteriorVision_02_'))
previous = [a for a in current if SITE_TAG in map(str,a.tags)]
for a in previous:
    actors.destroy_actor(a)

if not previous:
    positions = defaultdict(list)
    frame = u.Transform(location=[house[3]*100,house[4]*100,4-original['floor']*scale],
                        rotation=u.Rotator(yaw=house[5]),scale=[scale]*3)
    for p in pieces:
        if not p['mesh'].endswith('.SM_Door_00A'):
            positions[p['mesh'].split('.')[0]].append(shell_transform(p,frame).translation)

    # The original home was dressed from a variable subset of this furniture.
    # Use the saved instances within its old walls, including pieces moved since authoring.
    household = {KIT+'TimberBed', KIT+'OakTable', KIT+'OakShelf', BENCH, CRATE}
    for a in current:
        if not re.match(r'^Village_\d{3,}_',a.get_actor_label()):
            continue
        for comp in a.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh = comp.static_mesh
            if not mesh:
                continue
            package = mesh.get_path_name().split('.')[0]
            candidates = positions.get(package,[])
            is_household = package in household
            is_ground_cover = mesh.get_name().startswith(
                ('SM_Grass','SM_Plant','SM_Stone_','SM_SoftWildGrass','flower_','SM_H_RubblePile_'))
            if not candidates and not is_ground_cover and not is_household:
                continue
            changed = False
            for i in range(comp.get_instance_count()-1,-1,-1):
                t = comp.get_instance_transform(i,True)
                pos = t.translation
                match = next((j for j,q in enumerate(candidates) if (q-pos).length()<.7),None)
                if match is not None:
                    candidates.pop(match)
                elif is_household:
                    bounds = mesh.get_bounding_box()
                    center = u.MathLibrary.transform_location(t,(bounds.min+bounds.max)*.5)
                    dx,dy = rotate(center.x/100-original['center'][0],center.y/100-original['center'][1],-house[5])
                    if abs(dx) > original['half'][0] or abs(dy) > original['half'][1] or not -15. < center.z < 315.:
                        continue
                elif is_ground_cover:
                    dx,dy = rotate(pos.x/100-shape['center'][0], pos.y/100-shape['center'][1], -house[5])
                    if abs(dx)>shape['half'][0] or abs(dy)>shape['half'][1]:
                        continue
                else:
                    continue
                if not changed:
                    a.modify()
                    comp.modify()
                    changed = True
                if not comp.remove_instance(i):
                    raise RuntimeError('Cannot remove old instance from '+a.get_actor_label())
    missing = {path:len(v) for path,v in positions.items() if v}
    if missing:
        raise RuntimeError('Existing House 02 differs from its saved assembly: '+str(missing))

report = build_tavern(house,pieces,plan,shape)
vision.modify()
set_tavern_vision(vision,house,shape,plan)
if map_file.stat().st_mtime_ns!=stamp:
    raise RuntimeError('The village map changed on disk during this operation')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Unable to save '+level)
u.log('VILLAGE_TAVERN_SAVED '+json.dumps(report))
