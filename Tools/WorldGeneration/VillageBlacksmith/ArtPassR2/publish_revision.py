"""Rebind only the nine owned furnishings; keep village layout, seed and repair-state tags."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
LEVEL='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
OLD='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Meshes/'
NEW='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/'
names=[row['name'] for row in json.loads((OUT/'model-manifest.json').read_text())['assets']]
E=u.EditorAssetLibrary
def required(path):
    o=u.load_asset(path)
    if not o:raise RuntimeError('Missing '+path)
    return o
assets={name:required(NEW+name) for name in names}
level_file=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
before=OUT/'Before/L_AbandonedVillage.pre-art-r2.umap'
before.parent.mkdir(parents=True,exist_ok=True)
if not before.exists():shutil.copy2(level_file,before)
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:raise RuntimeError('Load village')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
changes=[]
for actor in actors.get_all_level_actors():
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        old=comp.static_mesh
        if not old or not old.get_path_name().startswith(OLD):continue
        name=old.get_name()
        if name not in assets:continue
        new=assets[name];ob,nb=old.get_bounding_box(),new.get_bounding_box()
        # standing() places bounds, not arbitrary mesh pivots. Preserve the same centre and floor contact.
        delta=u.Vector((ob.min.x+ob.max.x-nb.min.x-nb.max.x)*.5,
                       (ob.min.y+ob.max.y-nb.min.y-nb.max.y)*.5,ob.min.z-nb.min.z)
        if name.endswith(('BlacksmithSign','ClosedPlaque')):delta=u.Vector()
        instanced=isinstance(comp,u.InstancedStaticMeshComponent)
        count=comp.get_instance_count() if instanced else 1
        transforms=[]
        for index in range(count):
            t=comp.get_instance_transform(index,world_space=True) if instanced else comp.get_world_transform()
            adjusted=u.MathLibrary.transform_location(t,delta)
            # Stock is staged on two rack tops; old assembly left a 0.5 cm visual gap.
            tags=[str(tag) for tag in comp.component_tags]
            if name.endswith('IronStock') and 'VillageShop.Repaired' in tags:adjusted.z-=.5
            t.translation=adjusted;transforms.append(t)
        comp.modify();comp.set_static_mesh(new)
        for index,t in enumerate(transforms):
            if instanced:comp.update_instance_transform(index,t,True,index==count-1,True)
            else:comp.set_world_transform(t,False,True)
        actor.modify()
        changes.append(dict(actor=actor.get_actor_label(),component=comp.get_name(),mesh=new.get_path_name(),instances=count,collision_profile=str(comp.get_collision_profile_name()),tags=[str(t) for t in comp.component_tags]))
if not changes:raise RuntimeError('No old furniture bindings found; no map save performed')
if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):raise RuntimeError('Save village map')
report={'level':LEVEL,'changes':changes,'components':len(changes),'instances':sum(c['instances'] for c in changes),
 'seed_changed':False,'layout_regenerated':False,'repair_logic_changed':False,'gameplay_started':False,
 'backup':str(before),'saved_sha256':hashlib.sha256(level_file.read_bytes()).hexdigest()}
(OUT/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VILLAGE_ART_R2_PUBLISHED '+str(report['instances']))
