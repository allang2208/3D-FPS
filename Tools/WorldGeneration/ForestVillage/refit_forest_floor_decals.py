"""Refit saved floor-layer point rotations and their existing decal actors to the hillside."""
import math
import unreal as u

BASE='/Game/ForestPathStudy/VillageRegion/'
WORLD='/Game/GameMaps/L_ForestPathVillage'
PAGES={'HillsLandscape':'Ecology/DA_ForestFloor_01','RoadLandscape':'Themes/Road/DA_RoadFloor_01'}
MATERIALS={'MossPatch':'M_EastRoad_MossPatch','ForestSoil':'M_EastRoad_SoilPatch'}

def refit(world,region,theme_ids):
    positions={}
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.DecalActor):
        if not actor.get_path_name().startswith(WORLD+'.'):continue
        decal=actor.get_components_by_class(u.DecalComponent)[0]
        mat=decal.get_decal_material()
        if mat and mat.get_name() in MATERIALS.values():
            p=actor.get_actor_location()
            positions[mat.get_name(),round(p.x,1),round(p.y,1)]=actor
    counts={}
    for theme in theme_ids:
        page=u.load_asset(BASE+PAGES[theme])
        count=0
        collection=page.get_editor_property('data')
        for pin,material in MATERIALS.items():
            arrays,tags=collection.get_typed_inputs_by_pin_label(pin,u.PCGBasePointData)
            if not arrays:continue
            data,=arrays
            old=[data.get_transform(i) for i in range(data.get_num_points())]
            adjusted=[]
            for t in old:
                p=t.translation
                actor=positions[material,round(p.x,1),round(p.y,1)]
                yaw=math.degrees(2.*math.atan2(t.rotation.z,t.rotation.w))
                new=region.fit_floor_decal(p.x,p.y,yaw,t.scale3d.y)
                # Retain the actor template's own projection rotation relative to the PCG point.
                relative=u.MathLibrary.make_relative_transform(actor.get_actor_transform(),t)
                after=u.MathLibrary.compose_transforms(relative,new)
                actor.modify()
                actor.set_actor_transform(after,False,True)
                adjusted.append(new)
            if adjusted:
                page.modify();data.modify()
                bounds=u.PCGPointOutputRange(point_data=data,range_start_index=0,range_size=len(old))
                u.PCGBasePointData.set_transform_values_on_range(bounds,adjusted)
                first=data.get_transform(0).rotation;expected=adjusted[0].rotation
                if abs(first.x*expected.x+first.y*expected.y+first.z*expected.z+first.w*expected.w)<.999999:
                    raise RuntimeError('Point rotation write failed')
            count+=len(old)
        if not u.EditorAssetLibrary.save_loaded_asset(page,False):raise RuntimeError('Could not save '+PAGES[theme])
        counts[theme]=count
    if not u.EditorLoadingAndSavingUtils.save_map(world,WORLD):raise RuntimeError('Could not save refitted floor decals')
    return counts
