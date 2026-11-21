"""Update the plaza's original house 03 inside the current saved village."""
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import unreal as u


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE),str(HERE.parent/'VillageBlacksmith'),str(HERE.parent/'AbandonedVillage')]
from author_shop import BENCH, CRATE, KIT, shell_transform
from author_shop03 import SITE_TAG, build_herbalist, is_stateful_shell, set_herbalist_daylight
from layout_geometry import plot_geometry, rotate


def remove_original_contents(current,house,pieces,geometry,frame):
    # These masonry instances are shared with other houses. Compare native
    # package AND world position so another house or a yard wall stays untouched.
    expected = defaultdict(list)
    for part in pieces:
        if is_stateful_shell(part):
            expected[part['mesh'].split('.')[0]].append(shell_transform(part,frame).translation)
    furniture = {KIT+'TimberBed', KIT+'OakTable', KIT+'OakShelf', BENCH, CRATE}
    removals = []
    for actor in current:
        if not re.match(r'^Village_\d{3,}_',actor.get_actor_label()):
            continue
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh = comp.static_mesh
            if not mesh:
                continue
            path = mesh.get_path_name().split('.')[0]
            positions = expected.get(path,[])
            is_furniture = path in furniture
            if not positions and not is_furniture:
                continue
            bounds = mesh.get_bounding_box()
            local_center = (bounds.min+bounds.max)*.5
            matches = []
            for index in range(comp.get_instance_count()-1,-1,-1):
                transform = comp.get_instance_transform(index,True)
                match = next((j for j,p in enumerate(positions)
                              if (p-transform.translation).length() < .65),None)
                if match is not None:
                    positions.pop(match)
                    matches.append((index,'original_shell'))
                elif is_furniture:
                    # This furniture was arranged from the donor footprint;
                    # tolerate hand shifts inside 03 since its original build.
                    center = u.MathLibrary.transform_location(transform,local_center)
                    dx,dy = rotate(center.x/100-geometry['center'][0],
                                   center.y/100-geometry['center'][1],-house[5])
                    if (abs(dx) < geometry['half'][0] and abs(dy) < geometry['half'][1]
                            and -15 < center.z < 315):
                        matches.append((index,'original_furniture'))
            if matches:
                removals.append((actor,comp,matches))
    missing = {path:len(v) for path,v in expected.items() if v}
    if missing:
        raise RuntimeError('Original building 03 masonry differs from the donor: '+str(missing))
    counts = Counter()
    for actor,comp,matches in removals:
        actor.modify()
        comp.modify()
        for index,kind in matches:
            if not comp.remove_instance(index):
                raise RuntimeError('Could not remove instance on '+actor.get_actor_label())
            counts[kind] += 1
    return dict(counts)


source = ROOT/'SourceAssets/TemperateHillsVillage'
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
house = next(h for h in plan['houses'] if h[0] == plan['herbalist']['house'])
pieces = kit[house[2]]
geometry = plot_geometry(house,pieces,plan)
scale = plan['house_scale']
frame = u.Transform(location=[house[3]*100,house[4]*100,4-geometry['floor']*scale],
                    rotation=u.Rotator(yaw=house[5]),scale=[scale]*3)
level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
private_stage = '-HerbalistStage' in u.SystemLibrary.get_command_line().split()
host_root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
relative_map = Path('Content')/(level.removeprefix('/Game/')+'.umap')
map_file = (host_root if private_stage else ROOT)/relative_map
if private_stage and map_file.samefile(ROOT/relative_map):
    raise RuntimeError('Herbalist staging requires an independent copy of the village map')
stamp = map_file.stat().st_mtime_ns
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserving unsaved level changes')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('A play session is using the current world')
u.get_default_object(u.HillsHerbalistWorkshop).get_editor_property('shop_assemblies')
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not load '+level)
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
current = list(actors.get_all_level_actors())
vision = next(a for a in current if a.get_actor_label().startswith('Village_InteriorVision_03_'))
previous = [a for a in current if SITE_TAG in map(str,a.tags)]
if previous:
    for actor in previous:
        if not actors.destroy_actor(actor):
            raise RuntimeError('Could not replace previous herbalist actor')
    removed = dict(previous_shop_actors=len(previous))
else:
    removed = remove_original_contents(current,house,pieces,geometry,frame)

report = build_herbalist(house,pieces,frame)
vision.modify()
vision.set_actor_label('Village_InteriorVision_03_'+house[1])
set_herbalist_daylight(vision)
if map_file.stat().st_mtime_ns != stamp:
    raise RuntimeError('Village changed on disk during assembly. Re-run on its current revision.')
if not private_stage:
    backup = ROOT/'Saved/VillageHerbalist/Before'/str(stamp)/map_file.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2(map_file,backup)
if map_file.stat().st_mtime_ns != stamp:
    raise RuntimeError('Village changed during backup. Re-run on its current revision.')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save '+level)
report.update(level=level,removed=removed,tested=False)
out = host_root/'staged-herbalist.json' if private_stage else ROOT/'SourceAssets/HillsVillageHerbalist/village-saved.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('HERBALIST_VILLAGE_SAVED '+json.dumps(report,ensure_ascii=False))
