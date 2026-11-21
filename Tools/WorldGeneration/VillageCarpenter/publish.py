"""Replace the old 04 cottage in the current village sublevel without rebuilding its neighbours."""
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT/'SourceAssets/TemperateHillsVillage'
DEST = '/Game/WorldGeneration/TemperateHills/AbandonedVillage'
LEVEL = DEST+'/L_AbandonedVillage'
sys.path[:0] = [str(HERE),str(HERE.parent/'VillageBlacksmith'),str(HERE.parent/'AbandonedVillage')]
from author_shop import BENCH, CRATE, KIT, shell_transform
from carpenter_shop import build_workshop, vision_room
from layout_geometry import house_geometry, rotate

plan=json.loads((SOURCE/'layout.json').read_text(encoding='utf-8'))
kit=json.loads((SOURCE/'house-pieces.json').read_text(encoding='utf-8'))
cfg=plan['carpenter']
house=next(row for row in plan['houses'] if row[0]==cfg['house'])
scale=plan['house_scale']
old=list(house)
old[2],old[5]=cfg['original_model'],cfg['original_yaw']
old_parts=kit[old[2]]
old_room=house_geometry(old,old_parts,scale)
room=house_geometry(house,kit[house[2]],scale)

editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Village is in use by an active play session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve unsaved level changes')
u.get_default_object(u.HillsCarpenterWorkshop).get_editor_property('shop_assemblies')
map_file=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
map_timestamp=map_file.stat().st_mtime_ns
weapon_displays='-VillageWeaponDisplays' in u.SystemLibrary.get_command_line().split()
workshop_layout='-VillageWorkshopLayout' in u.SystemLibrary.get_command_line().split()
if weapon_displays or workshop_layout:
    before=ROOT/'Saved/VillageWorkshopDisplays/Before'/str(map_timestamp)
    before.mkdir(parents=True,exist_ok=True)
    if not (before/map_file.name).exists():
        shutil.copy2(map_file,before/map_file.name)
backup=ROOT/'Saved/VillageCarpenter/Before'
backup.mkdir(parents=True,exist_ok=True)
for name in ('L_AbandonedVillage.umap','T_VillageRoadMask.uasset'):
    file=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage'/name
    if not (backup/name).exists(): shutil.copy2(file,backup/name)
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world: raise RuntimeError('Could not load '+LEVEL)
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
all_actors=list(actors.get_all_level_actors())
old_light=next(a for a in all_actors if a.get_actor_label().startswith('Village_InteriorVision_04_'))
old_frame=u.Transform(location=[old[3]*100,old[4]*100,4-old_room['floor']*scale],
                      rotation=u.Rotator(yaw=old[5]),scale=[scale]*3)
expected=defaultdict(list)
for p in old_parts:
    if not p['mesh'].endswith('.SM_Door_00A'):
        expected[p['mesh']].append(shell_transform(p,old_frame).translation)
old_furniture={KIT+suffix for suffix in ('TimberBed','OakTable','OakShelf')} | {BENCH,CRATE}
areas=[dict(center=room['center'],yaw=house[5],half=room['half'])]
areas += [r for r in plan['service_clearings'] if r['owner']=='Carpenter04']
misc_prefix=('SM_Grass','SM_PlantType','SM_SoftWildGrass','flower_','SM_Stone_','SM_H_RubblePile_')


def lies_in_old_room(p):
    x,y=rotate(p.x/100-old_room['center'][0],p.y/100-old_room['center'][1],-old[5])
    return abs(x)<old_room['half'][0] and abs(y)<old_room['half'][1]


def clips_new_plot(transform,bounds):
    if math.hypot(transform.translation.x/100-house[3],transform.translation.y/100-house[4])>14:
        return False
    points=[u.MathLibrary.transform_location(transform,u.Vector(x,y,z)) for x in (bounds.min.x,bounds.max.x)
            for y in (bounds.min.y,bounds.max.y) for z in (bounds.min.z,bounds.max.z)]
    for area in areas:
        cx,cy=area['center']
        hx,hy=area['half']
        coords=[rotate(p.x/100-cx,p.y/100-cy,-area['yaw']) for p in points]
        xs,ys=zip(*coords)
        if min(xs)<hx and max(xs)>-hx and min(ys)<hy and max(ys)>-hy: return True
    return False


counts=defaultdict(int)
previous=any(a.get_actor_label()=='Village_04_Carpenter_Workbench' for a in all_actors)
for actor in all_actors:
    label=actor.get_actor_label()
    if label=='Village_04_Carpenter_Workbench' or 'VillageCarpenter.Assembly' in map(str,actor.tags) or 'VillageCarpenter.Window' in map(str,actor.tags):
        actors.destroy_actor(actor)
        continue
    # A later refit owns only the workshop actors; the original cottage is already gone.
    if previous or not re.match(r'^Village_\d{3,}_',label): continue
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=comp.static_mesh
        if not mesh: continue
        path=mesh.get_path_name()
        furniture=path.split('.')[0] in old_furniture
        loose=mesh.get_name().startswith(misc_prefix)
        positions=expected.get(path,[])
        if not positions and not furniture and not loose: continue
        bounds=mesh.get_bounding_box()
        for index in range(comp.get_instance_count()-1,-1,-1):
            t=comp.get_instance_transform(index,True)
            p=t.translation
            match=next((j for j,v in enumerate(positions) if (v-p).length()<.65),None)
            if match is not None:
                del positions[match]
                kind='old_shell'
            elif furniture and lies_in_old_room(p): kind='old_furniture'
            elif loose and clips_new_plot(t,bounds): kind='yard_dressing'
            else: continue
            actor.modify()
            comp.modify()
            if not comp.remove_instance(index): raise RuntimeError('Could not remove '+label)
            counts[kind]+=1
if not previous:
    missing={k:len(v) for k,v in expected.items() if v}
    if missing: raise RuntimeError('Old cottage placement differs from its source: '+str(missing))

report=build_workshop(house)
if workshop_layout:
    from LoftR3.assemble import move_ruined_timber
    smith_house=next(row for row in plan['houses'] if row[0]==plan['blacksmith']['house'])
    report['smith_stair_timber']=move_ruined_timber(smith_house)
if weapon_displays:
    from forge_weapon_display import install_forge_display
    forge_display=install_forge_display()
old_light.modify()
vision_room(old_light,house)
if map_file.stat().st_mtime_ns!=map_timestamp:
    raise RuntimeError('Village was saved during assembly; rerun on its current version')
mask_path=DEST+'/T_VillageRoadMask'
if not previous:
    task=u.AssetImportTask()
    task.filename=str(SOURCE/'RoadMask.png')
    task.destination_path=DEST
    task.destination_name='T_VillageRoadMask'
    task.automated=True
    task.replace_existing=True
    task.replace_existing_settings=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths: raise RuntimeError('Village road mask import failed')
    texture=u.load_asset(DEST+'/T_VillageRoadMask')
    texture.srgb=False
    texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
    texture.address_x=texture.address_y=u.TextureAddress.TA_CLAMP
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False): raise RuntimeError('Could not save yard mask')
if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL): raise RuntimeError('Could not save village')
report.update(level=LEVEL,removed=dict(counts),road_mask=mask_path+'.T_VillageRoadMask',tested=False)
out=ROOT/'SourceAssets/HillsVillageCarpenter'
out.mkdir(parents=True,exist_ok=True)
(out/'village-saved.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if weapon_displays or workshop_layout:
    display_file=out/'workshop-displays-saved.json'
    display_report=json.loads(display_file.read_text(encoding='utf-8')) if display_file.exists() else {}
    display_report.update(level=LEVEL)
    display_report['04']=report['weapon_display']
    if weapon_displays: display_report['01']=forge_display
    display_file.write_text(json.dumps(display_report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('CARPENTER_VILLAGE_SAVED '+json.dumps(report,ensure_ascii=False))
