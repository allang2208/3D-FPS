"""Replace only the first-house assemblies; retain village seed, other structures and repair state."""
import json,math,runpy,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
SRC=ROOT/'SourceAssets/TemperateHillsVillage'
DEST='/Game/WorldGeneration/TemperateHills/AbandonedVillage'
LEVEL=DEST+'/L_AbandonedVillage'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map changes')
previous=editor.get_editor_world() if editor else None
previous_path=previous.get_path_name().split('.')[0] if previous else None
for relative in ['Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap','Content/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask.uasset']:
    backup=OUT/'Before'/relative
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,backup)
sys.path.insert(0,str(ROOT/'Tools/WorldGeneration/AbandonedVillage'))
sys.path.insert(0,str(ROOT/'Tools/WorldGeneration/VillageBlacksmith'))
from layout_geometry import house_geometry
from room_daylight import SHOP_DAYLIGHT, apply_daylight
from author_shop import build_shop
plan=json.loads((SRC/'layout.json').read_text(encoding='utf-8'))
kit=json.loads((SRC/'house-pieces.json').read_text(encoding='utf-8'))
house=next(h for h in plan['houses'] if h[0]=='01')
if house[2]!='SL_Blacksmith_LoftR3':raise RuntimeError('Prepare R3 source layout first')
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:raise RuntimeError('Load village')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
# Finish the earlier furniture delivery in existing homes without rebuilding their layouts.
old_root='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Meshes/'
if any(c.static_mesh and c.static_mesh.get_path_name().startswith(old_root) for a in actors.get_all_level_actors() for c in a.get_components_by_class(u.StaticMeshComponent)):
    furniture_result=runpy.run_path(str(ROOT/'Tools/WorldGeneration/VillageBlacksmith/ArtPassR2/publish_revision.py'),run_name='__main__')
    world=furniture_result['world']
owned={'Village_Blacksmith_Common','Village_Blacksmith_Ruined','Village_Blacksmith_Repaired','Village_01_Blacksmith_Forge',
       'Village_Blacksmith_Window_1','Village_Blacksmith_Window_2','Village_Blacksmith_Window_3'}
for actor in list(actors.get_all_level_actors()):
    if actor.get_actor_label() in owned:actors.destroy_actor(actor)
parts=kit[house[2]];scale=plan.get('house_scale',1.2);geometry=house_geometry(house,parts,scale)
base=u.Transform(location=[house[3]*100,house[4]*100,4-geometry['floor']*scale],rotation=u.Rotator(yaw=house[5]),scale=[scale]*3)
report=build_shop(house,parts,base,geometry)
for actor in actors.get_all_level_actors():
    if actor.get_actor_label().startswith('Village_InteriorVision_01_'):
        actor.modify();actor.set_actor_transform(base,False,False)
        actor.set_editor_property('room_minimum',u.Vector(*geometry['room_min']))
        actor.set_editor_property('room_maximum',u.Vector(*geometry['room_max']))
        apply_daylight(actor, SHOP_DAYLIGHT['01'])
# Clear only loose ground dressing that overlaps the expanded house, apron or chimney foot.
clearings=[dict(center=geometry['center'],half=geometry['half'],yaw=house[5])]+[r for r in plan['service_clearings'] if r['owner']=='BlacksmithLoftR3']
removed=[]
for actor in actors.get_all_level_actors():
    if actor.get_actor_label() in owned:continue
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=comp.static_mesh
        if not mesh:continue
        name=mesh.get_name()
        if not name.startswith(('SM_Grass','SM_PlantType','SM_SoftWildGrass','flower_','SM_Stone_','SM_H_RubblePile_')):continue
        bounds=mesh.get_bounding_box();deleted=0
        for index in range(comp.get_instance_count()-1,-1,-1):
            t=comp.get_instance_transform(index,True);p=t.translation
            if math.hypot(p.x-house[3]*100,p.y-house[4]*100)>1500:continue
            corners=[u.MathLibrary.transform_location(t,u.Vector(x,y,z)) for x in (bounds.min.x,bounds.max.x) for y in (bounds.min.y,bounds.max.y) for z in (bounds.min.z,bounds.max.z)]
            hit=False
            for area in clearings:
                a=math.radians(area['yaw']);cx,cy=area['center'];hx,hy=area['half']
                xx=[(q.x/100-cx)*math.cos(a)+(q.y/100-cy)*math.sin(a) for q in corners]
                yy=[(q.y/100-cy)*math.cos(a)-(q.x/100-cx)*math.sin(a) for q in corners]
                if max(xx)>-hx and min(xx)<hx and max(yy)>-hy and min(yy)<hy:hit=True;break
            if hit:comp.modify();comp.remove_instance(index);deleted+=1
        if deleted:actor.modify();removed.append(dict(mesh=name,instances=deleted))
task=u.AssetImportTask();task.filename=str(SRC/'RoadMask.png');task.destination_path=DEST;task.destination_name='T_VillageRoadMask';task.automated=True;task.replace_existing=True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mask=u.load_asset(DEST+'/T_VillageRoadMask');mask.srgb=False;mask.compression_settings=u.TextureCompressionSettings.TC_MASKS;mask.address_x=mask.address_y=u.TextureAddress.TA_CLAMP
if not u.EditorAssetLibrary.save_loaded_asset(mask,False):raise RuntimeError('Save road coverage')
if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):raise RuntimeError('Save village')
report.update(level=LEVEL,removed_overlapping_ground_dressing=removed,seed_changed=False,other_houses_repositioned=False,gameplay_started=False,rendered=False)
(OUT/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if previous_path and previous_path!=LEVEL and u.EditorAssetLibrary.does_asset_exist(previous_path):u.EditorLoadingAndSavingUtils.load_map(previous_path)
u.log('BLACKSMITH_LOFT_R3_PUBLISHED')
