"""Save the forest-village terrain, seeded PCG planting, and meadow silhouette batches."""
import json,math,os,struct
from collections import defaultdict
from pathlib import Path
import unreal as u

src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
levels=u.EditorLevelUtils
save=u.EditorLoadingAndSavingUtils
village='/Game/GameMaps/L_ForestPathVillage'
original='/Game/ForestPathStudy/Maps/L_ForestPathForest'
copy='/Game/ForestPathStudy/VillageRegion/Reference/TrailLandscape/L_ForestPathForest'
tag='ForestVillage.FarGrass'
fine_mesh='/Game/WorldGeneration/TemperateHills/WetForest/CarpetGrass/SM_RainforestGrassLow'
fine_material='/Game/ForestPathStudy/VillageRegion/GrassCover/MI_HillsGrassLow'

def actor_list():return actors.get_all_level_actors()

def forest_copy():
    assets=json.loads((batch/'materials.json').read_text())
    if not u.EditorAssetLibrary.does_asset_exist(copy):
        donor=save.load_map(original)
        if not save.save_map(donor,copy):raise RuntimeError('Could not copy the study Landscape')
    w=save.load_map(copy)
    land=[a for a in actor_list() if isinstance(a,u.LandscapeProxy)]
    if not land or not all(a.get_path_name().startswith(copy+'.') for a in land):raise RuntimeError('Unexpected Landscape ownership')
    for a in land:
        a.set_editor_property('landscape_material',u.load_asset(assets['landscape']))
    if not save.save_map(w,copy):raise RuntimeError('Could not save village Landscape material')

def bind_forest(w):
    for level in levels.get_levels(w):
        if level.get_path_name().startswith(copy+'.'):return
    old=next(l for l in levels.get_levels(w) if l.get_path_name().startswith(original+'.'))
    if not levels.remove_level_from_world(old):raise RuntimeError('Could not detach the old streaming reference')
    if not levels.add_level_to_world(w,copy,u.LevelStreamingAlwaysLoaded):raise RuntimeError('Could not stream the village Landscape')

def place_meadows(w):
    mesh=u.load_asset(fine_mesh)
    material=u.load_asset(fine_material)
    if not mesh or not material:raise RuntimeError('Missing shared fine grass or its hills material')
    poses_file=src/'meadow-fine.f32'
    if not poses_file.is_file():raise FileNotFoundError(poses_file)
    collar=mesh.get_bounding_box().min.z+mesh.get_editor_property('negative_bounds_extension').z
    # Keep the waterside sedge ring and replace all three former hill-grass silhouettes.
    for a in actor_list():
        if not a.get_path_name().startswith(village+'.') or tag not in map(str,a.tags):continue
        comps=a.get_components_by_class(u.InstancedStaticMeshComponent)
        sedge=[c for c in comps if c.static_mesh and c.static_mesh.get_name()=='SM_RiverDense_grass_04_03_mesh']
        if not sedge:actors.destroy_actor(a)
        else:
            for c in comps:
                if c not in sedge:
                    c.clear_instances()
                    c.set_visibility(False)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib=u.SubobjectDataBlueprintFunctionLibrary
    def add(actor,cls):
        parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
        handle,error=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls))
        obj=lib.get_associated_object(lib.get_data(handle))
        if not obj:raise RuntimeError(str(error))
        return obj
    groups=defaultdict(list)
    for x,y,z,yaw,gx,gy,spread,ht in struct.iter_unpack('<8f',poses_file.read_bytes()):
        rot=math.radians(yaw)
        direction=u.Vector(math.cos(rot),math.sin(rot),gx*math.cos(rot)+gy*math.sin(rot))
        up=u.Vector(-gx,-gy,1)
        rotation=u.MathLibrary.make_rot_from_zx(up,direction)
        root=u.Vector(x,y,z)-up*(collar*ht/math.sqrt(1.+gx*gx+gy*gy))
        groups[math.floor(x/12800),math.floor(y/12800)].append(u.Transform(location=root,rotation=rotation,scale=u.Vector(spread,spread,ht)))
    for (i,j),poses in groups.items():
        center=u.Vector((i+.5)*12800,(j+.5)*12800,0)
        a=actors.spawn_actor_from_class(u.Actor,center)
        if not a.get_path_name().startswith(village+'.'):raise RuntimeError('Unexpected meadow owner')
        a.set_actor_label(f'Forest meadow {i} {j}');a.set_editor_property('tags',[tag])
        if not a.root_component:add(a,u.SceneComponent)
        a.root_component.set_mobility(u.ComponentMobility.STATIC);a.set_actor_location(center,False,True)
        c=add(a,u.HierarchicalInstancedStaticMeshComponent);c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(mesh)
        for slot in range(len(mesh.get_editor_property('static_materials'))):c.set_material(slot,material)
        # Nearby dense PCG already provides the fine high-LOD silhouette. Share its source mesh
        # and shade, and spend only its two lighter authored LODs on the supplementary layer.
        c.set_editor_property('override_min_lod',True)
        c.set_editor_property('min_lod',2)
        c.set_editor_property('evaluate_world_position_offset',False)
        c.set_editor_property('instance_min_draw_distance',0);c.set_cull_distances(0,0)
        c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_cast_shadow(False)
        for key in ('cast_static_shadow','cast_dynamic_shadow','cast_contact_shadow','cast_far_shadow','visible_in_ray_tracing',
                    'affect_distance_field_lighting','affect_dynamic_indirect_lighting','receives_decals','generate_overlap_events','can_ever_affect_navigation'):
            c.set_editor_property(key,False)
        c.add_instances(poses,False,True,False)
    return sum(map(len,groups.values())),len(groups)

def build():
    if (src/'cliff-exposure.json').is_file():
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from author_cliff_exposure import install
        install()
        return
    if (src/'loess-foothills.json').is_file():
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from author_village_loess_foothills import install
        install()
        return
    if (src/'relief.json').is_file() and (src/'Grass/pond_allowed.u8').is_file():
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from author_hill_relief_pools import build_all
        build_all()
        return
    forest_copy()
    w=save.load_map(village)
    bind_forest(w)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Could not select the persistent PCG level')
    root=next(a for a in actor_list() if isinstance(a,u.ForestVillageRegion))
    if not root.bake_reference_surface(str(src),u.load_asset('/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference')):
        raise RuntimeError('Terrain and collision bake failed')
    scene=actor_list()
    templates=[c for a in scene if isinstance(a,u.PCGVolume) and a.get_path_name().startswith(copy+'.')
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates:raise RuntimeError('Forest templates missing')
    if not root.bake_vegetation(str(src.parent/'VillageFlora-R20/Grass/planting.bin'),templates):raise RuntimeError('PCG re-projection failed')
    total,cells=place_meadows(w)
    if not save.save_map(w,village):raise RuntimeError('Could not save village')
    (batch/'baked.json').write_text(json.dumps(dict(patches=total,components=cells,landscape=copy,terrain=json.loads((src/'generation.json').read_text())),indent=2))
if __name__=="__main__":build()
