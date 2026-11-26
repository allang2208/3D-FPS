"""Save the original working quarry as a distance-streamed level, in its original survey frame."""
from array import array
from collections import defaultdict
from math import floor
import csv
import json
import os
from pathlib import Path
import unreal as u

src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
folder='/Game/ForestPathStudy/VillageRegion/Quarry'
package=folder+'/L_ForestQuarry'
target='/Game/GameMaps/L_ForestPathVillage'
cx,cy,z=json.loads((src/'quarry.json').read_text())['center_cm']
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
handles=u.SubobjectDataBlueprintFunctionLibrary
def add(actor,klass):
    parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
    handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=klass))
    obj=handles.get_associated_object(handles.get_data(handle))
    if not obj: raise RuntimeError(str(reason))
    return obj

def field(name,kind):
    data=array(kind)
    data.frombytes((src/name).read_bytes())
    return data
def sample(field,stride,x,y):
    i,j=floor(x),floor(y)
    fx,fy=x-i,y-j
    k=j*stride+i
    return ((1.-fx)*field[k]+fx*field[k+1])*(1.-fy)+((1.-fx)*field[k+stride]+fx*field[k+stride+1])*fy

terrain=field('region.i16','h')
survey=field('quarry-ground.f32','f')
clearing=field('quarry-clear.u8','B')
groups=defaultdict(list)
with (src/'quarry.csv').open() as stream:
    for p in csv.DictReader(stream):
        x,y,h=map(float,(p['x'],p['y'],p['z']))
        # Keep the three benches, shed, hoist and approach. The old lake is a separate landform.
        if abs(x)>7300 or not -7400<=y<=7100: continue
        if y<-2900.:
            gx,gy=(cx-y)*.01+624.,(cy+x)*.01+320.
            # Transfer approach props to the new grade. Its carriageway and surrounding forest
            # are owned by the road generator; the historic shed, hoist and cut are farther in.
            if abs(x)<420.: continue
            if any(key in p['mesh'] for key in ('Grass','Hazel')) and sample(clearing,1025,gx,gy)<254.: continue
            h+=sample(terrain,1025,gx,gy)-z-sample(survey,241,x*.01+120.,y*.01+120.)
        rot=u.Rotator(roll=float(p['roll']),pitch=float(p['pitch']),yaw=float(p['yaw']))
        scale=u.Vector(*[float(p[k]) for k in ('sx','sy','sz')])
        groups[p['mesh'],int(p['detail'])].append(u.Transform(location=u.Vector(x,y,h),rotation=rot,scale=scale))
if not groups: raise RuntimeError('Empty fixed quarry layout')
owner=actors.spawn_actor_from_class(u.Actor,u.Vector())
owner.set_actor_label('White Cliffs working quarry')
if not owner.root_component:add(owner,u.SceneComponent)
owner.root_component.set_mobility(u.ComponentMobility.STATIC)
for (path,detail),poses in sorted(groups.items()):
    mesh=u.load_asset(path)
    if not mesh: raise RuntimeError(path)
    comp=add(owner,u.HierarchicalInstancedStaticMeshComponent)
    comp.set_mobility(u.ComponentMobility.STATIC)
    comp.set_static_mesh(mesh)
    comp.set_collision_profile_name('NoCollision' if detail else 'BlockAll')
    comp.set_editor_property('can_ever_affect_navigation',not detail)
    comp.set_editor_property('generate_overlap_events',False)
    comp.set_cull_distances(5000 if detail else 23000,7500 if detail else 28000)
    if detail:
        comp.set_cast_shadow(False)
        for key in ('receives_decals','visible_in_ray_tracing','affect_distance_field_lighting','affect_dynamic_indirect_lighting'):
            comp.set_editor_property(key,False)
    comp.add_instances(poses,False,False,not detail)

u.EditorAssetLibrary.make_directory(folder)
material=u.load_asset('/Game/WorldGeneration/TemperateHills/WhiteCliffs/Materials/Approach/M_QuarryWorkGround')
name='MI_ForestQuarryWorkGround'
mi=u.load_asset(folder+'/'+name) if u.EditorAssetLibrary.does_asset_exist(folder+'/'+name) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
ed=u.MaterialEditingLibrary
ed.set_material_instance_parent(mi,material)
ed.set_material_instance_vector_parameter_value(mi,'Survey',u.LinearColor(cx,cy,0.,1.))
ed.set_material_instance_scalar_parameter_value(mi,'FloorZ',z)
ed.update_material_instance(mi)
if not u.EditorAssetLibrary.save_loaded_asset(mi,False):raise RuntimeError('Quarry finish save')
decal=actors.spawn_actor_from_class(u.DecalActor,u.Vector(0.,600.,760.),u.Rotator(pitch=-90.))
comp=decal.get_component_by_class(u.DecalComponent)
comp.set_editor_property('decal_size',u.Vector(1800.,4780.,4780.))
comp.set_sort_order(-2)
comp.set_decal_material(mi)
if not u.EditorLoadingAndSavingUtils.save_map(world,package):raise RuntimeError('Quarry level save')
world=u.EditorLoadingAndSavingUtils.load_map(target)
region=next(a for a in actors.get_all_level_actors() if isinstance(a,u.ForestVillageRegion))
quarry_world=u.load_object(None,package+'.L_ForestQuarry')
if not isinstance(quarry_world,u.World): raise RuntimeError('Missing saved quarry level '+package)
region.set_editor_property('quarry_level',quarry_world)
region.set_editor_property('quarry_origin',u.Vector(cx,cy,z))
if not u.EditorLoadingAndSavingUtils.save_map(world,target): raise RuntimeError('Quarry level binding')
(batch/'quarry-bake.json').write_text(json.dumps({p:len(poses) for (p,_),poses in groups.items()},indent=2))
