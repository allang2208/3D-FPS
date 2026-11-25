"""Place one stablemaster on the streamed village's stable apron, in local centimetres."""
import hashlib
import json
import math
import shutil
from pathlib import Path
import unreal as u

project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=project/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
path=project/'Content'/(level.removeprefix('/Game/')+'.umap')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=digest(path)
batch=source.resolve().parents[3]/'HillsVillageStable/StablemasterMeshyR3'
before_file=batch/'Before'/before/path.name
before_file.parent.mkdir(parents=True,exist_ok=True)
if not before_file.exists():shutil.copy2(path,before_file)
if digest(before_file)!=before:raise RuntimeError('Village changed while preparing its pre-edit copy')
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Unable to open village map')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
published=json.loads((source/'imported.json').read_bytes())
asset=u.load_asset(published['blueprint'])
cls=asset.generated_class()
label='Village_Stable_Stablemaster'
tag='VillageStable.Stablemaster'
found=[a for a in actors.get_all_level_actors() if tag in map(str,a.tags) or a.get_actor_label()==label]
if len(found)>1 or (found and found[0].get_class()!=cls):
    raise RuntimeError('Stablemaster placement conflicts with an existing resident')
# Between bays one and two, looking towards the horse entrance. The streamed
# apron is generated at village-local zero; use the same grade as the stalls.
x,y=3740.,3415.
facing=math.degrees(math.atan2(1600.-y,4625.-x))
rot=u.Rotator(yaw=facing)
cdo=u.get_default_object(cls)
height=cdo.capsule_component.get_unscaled_capsule_half_height()
bounds=cdo.mesh.skeletal_mesh_asset.get_imported_bounds()
ground=.8
origin=u.Vector(x,y,ground-cdo.mesh.relative_location.z-(bounds.origin.z-bounds.box_extent.z))
actor=found[0] if found else actors.spawn_actor_from_class(cls,origin,rot)
if not actor:raise RuntimeError('Unable to place stablemaster')
actor.modify();actor.set_actor_location_and_rotation(origin,rot,False,True)
actor.set_actor_label(label);actor.set_folder_path('Village/EastGateStable')
actor.set_editor_property('tags',list(dict.fromkeys([*map(str,actor.tags),'NPC','Friendly',tag])))
if digest(path)!=before:raise RuntimeError('Village changed while the stablemaster was being placed')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Saving village failed')
after=digest(path)
out=batch/'After'/after/path.name
out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,out)
(source/'placement.json').write_text(json.dumps(dict(level=level,label=label,blueprint=published['blueprint'],local_cm=[origin.x,origin.y,origin.z],facing_degrees=facing,feet_grade_cm=ground,capsule_half_height_cm=height,before_file=str(before_file),before_sha256=before,after_file=str(out),after_sha256=after,play_test=False),indent=2))
