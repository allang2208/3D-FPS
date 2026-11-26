"""Author hillside grass in the saved forest village PCG, using the study's painted ground."""
import json
import math
import os
import struct
import subprocess
from pathlib import Path

import unreal as u

MAP = '/Game/GameMaps/L_ForestPathVillage'
STUDY_LEVEL = '/L_ForestPathForest.'
TOOLS = Path(__file__).resolve().parent


def read_study(scene, directory):
    land = next(a for a in scene if isinstance(a, u.Landscape) and STUDY_LEVEL in a.get_path_name())
    layer = u.load_asset('/Game/Example/Maps/NaniteExample_sharedassets/C_LayerInfo')
    if not layer:
        raise RuntimeError('Missing painted root and dirt layer')
    # Query each component in its own bounds. The real path's paint also accounts for turns.
    side = 253
    dirt = bytearray(side * side)
    for comp in land.get_components_by_class(u.LandscapeComponent):
        center, extent, _ = u.SystemLibrary.get_component_bounds(comp)
        # Landscape component bounds include shared edges. Take the maximum there.
        x0 = max(0, math.ceil((center.x - extent.x + 25200.0) / 200.0 - .001))
        x1 = min(side-1, math.floor((center.x + extent.x + 25200.0) / 200.0 + .001))
        y0 = max(0, math.ceil((center.y - extent.y + 25200.0) / 200.0 - .001))
        y1 = min(side-1, math.floor((center.y + extent.y + 25200.0) / 200.0 + .001))
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                wx = max(-25199.95,min(25199.95,200.0*x-25200.0))
                wy = max(-25199.95,min(25199.95,200.0*y-25200.0))
                w = comp.editor_get_paint_layer_weight_at_location(u.Vector(wx,wy,0),layer)
                idx = y*side+x
                dirt[idx] = max(dirt[idx],round(255*max(0.,min(1.,w))))
    (directory/'study_dirt_2m.u8').write_bytes(dirt)

    obstacles,trees,pond_props = bytearray(),bytearray(),bytearray()
    for actor in scene:
        if STUDY_LEVEL not in actor.get_path_name():
            continue
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = comp.get_editor_property('static_mesh')
            if not mesh:
                continue
            path = mesh.get_path_name().lower()
            tree = 'hornbeam' in path
            shrub = 'commonhazel' in path
            rock = '/scans/' in path and any(key in path for key in (
                'xjiifd1','xjijdiz','rgfoh','rgasy','tlljeeyva','vepkcelqx','vfspfcjaw'))
            prop = '/scans/' in path and not (tree or shrub or rock)
            if not (tree or shrub or rock or prop):
                continue
            box = mesh.get_bounding_box()
            local_center = (box.min+box.max)*.5
            half = (box.max-box.min)*.5
            instanced = isinstance(comp,u.InstancedStaticMeshComponent)
            for i in range(comp.get_instance_count() if instanced else 1):
                t = comp.get_instance_transform(i,world_space=True) if instanced else comp.get_world_transform()
                v = t.translation
                scale = t.scale3d
                if rock or prop:
                    v = u.MathLibrary.transform_location(t,local_center)
                    radius = min(500.,max(25., .86*max(abs(half.x*scale.x),abs(half.y*scale.y))))
                else:
                    radius = (72. if tree else 50.)*min(2.,max(.55,abs(scale.x)))
                target=trees if tree else pond_props if prop else obstacles
                target.extend(struct.pack('<fff',v.x/100.,v.y/100.,radius/100.))
    (directory/'study_trees.f32').write_bytes(trees)
    (directory/'study_pond_props.f32').write_bytes(pond_props)
    (directory/'study_obstacles.f32').write_bytes(obstacles)


def generate_points(current, directory, python, verge_source, *args):
    env = {k:v for k,v in os.environ.items() if k not in ('PYTHONHOME','PYTHONPATH')}
    subprocess.run([python,'-I',str(TOOLS/'generate_slope_grass.py'),str(current),str(directory),str(verge_source),*args],
                   check=True,env=env)
    return directory/'planting.bin'


def grass_materials():
    library=u.MaterialEditingLibrary
    folder='/Game/ForestPathStudy/VillageRegion/GrassCover'
    u.EditorAssetLibrary.make_directory(folder)
    for role,factor,transmission in (('Low',.80,.76),('Spreading',.84,.80),('Tall',.86,.82)):
        mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/WetForest/CarpetGrass/SM_RainforestGrass'+role)
        parent=mesh.get_material(0)
        name='MI_HillsGrass'+role
        target=folder+'/'+name
        mi=(u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else
            u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew()))
        library.set_material_instance_parent(mi,parent)
        params={str(p).lower():p for p in library.get_scalar_parameter_names(parent)}
        for key,multiplier in (('Brightness',factor),('Subsurface Strengh',transmission)):
            if key.lower() not in params:
                raise RuntimeError('Missing grass material parameter '+key+' on '+parent.get_path_name())
            param=params[key.lower()]
            value=library.get_material_instance_scalar_parameter_value(parent,param)
            library.set_material_instance_scalar_parameter_value(mi,param,value*multiplier)
        library.update_material_instance(mi)
        if not u.EditorAssetLibrary.save_loaded_asset(mi,False):
            raise RuntimeError('Cannot save '+target)


def apply(region, templates, scene, current, directory, python, verge_source):
    directory.mkdir(parents=True,exist_ok=True)
    u.EditorAssetLibrary.make_directory('/Game/ForestPathStudy/VillageRegion/GrassCover')
    read_study(scene,directory)
    grass_materials()
    generate_points(current,directory,python,verge_source,'--pool-mask')
    if not region.bake_woodland_pools(str(directory),237855):
        raise RuntimeError('Cannot seed forest pools on the authored ground')
    sites = generate_points(current,directory,python,verge_source)
    if not region.bake_vegetation(str(sites),templates):
        raise RuntimeError('Cannot bake the hillside grass sites')
    if not region.install_grass_cover(str(directory/'near_grass.u8')):
        raise RuntimeError('Cannot install the near-camera grass graph')


def main(use_prepared=False):
    directory = Path(os.environ['FPS_SLOPE_SOURCE'])
    batch = Path(os.environ['FPS_SLOPE_BATCH'])
    current = Path(os.environ['FPS_SLOPE_BASELINE'])
    world = u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:
        raise RuntimeError('Cannot open the forest village')
    scene = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    region = next(a for a in scene if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(MAP+'.'))
    templates = [c for a in scene if isinstance(a,u.PCGVolume) and STUDY_LEVEL in a.get_path_name()
                 for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if use_prepared and (directory/'pond_allowed.u8').exists():
        u.EditorAssetLibrary.make_directory('/Game/ForestPathStudy/VillageRegion/GrassCover')
        grass_materials()
        if not region.bake_woodland_pools(str(directory),237855):
            raise RuntimeError('Cannot restore prepared water sites')
        if not region.bake_vegetation(str(directory/'planting.bin'),templates):
            raise RuntimeError('Cannot bake prepared grass sites')
        if not region.install_grass_cover(str(directory/'near_grass.u8')):
            raise RuntimeError('Cannot install prepared grass cover')
    else:
        verge = Path(os.environ.get('FPS_WILD_GRASS_SOURCE',current.parent/'WildGrass-oilox20'))
        apply(region,templates,scene,current,directory,os.environ['FPS_REGION_PYTHON'],verge)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):
        raise RuntimeError('Cannot save the forest village grass')
    out = json.loads((directory/'generation.json').read_text())
    out.update(map=MAP,graph='/Game/ForestPathStudy/VillageRegion/PCG_ForestVillageSurroundings')
    (batch/'baked.json').write_text(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
