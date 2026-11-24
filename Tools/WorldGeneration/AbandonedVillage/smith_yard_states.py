"""Attach original scenery and repaired gravel to the blacksmith's existing repair-state assemblies."""
import json
import math
from pathlib import Path
import unreal as u
from smith_apron import ORIGIN,YARD_GRAVEL

TAG='VillageShop.SmithYardState'

def build(world):
    prefix=world.get_path_name()+':PersistentLevel.'
    shop=next((a for a in u.ObjectIterator(u.HillsBlacksmith) if a.get_path_name().startswith(prefix)),None)
    if not shop: raise RuntimeError('Expected the level-owned blacksmith for the furnace yard')
    anchor=next(a for a in shop.get_editor_property('shop_assemblies') if a.get_actor_label()=='Village_Blacksmith_Common')
    if any(TAG in map(str,c.component_tags) for c in anchor.get_components_by_class(u.InstancedStaticMeshComponent)):
        return False
    anchor.modify()
    subs=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles=u.SubobjectDataBlueprintFunctionLibrary
    parent=subs.k2_gather_subobject_data_for_instance(anchor)[0]
    if not anchor.root_component:
        subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.SceneComponent))
    anchor.root_component.set_mobility(u.ComponentMobility.STATIC)
    def batch(mesh,transforms,state,profile,collides,shadow,cull,decals,materials=()):
        h,reason=subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.HierarchicalInstancedStaticMeshComponent))
        c=handles.get_associated_object(handles.get_data(h))
        if not c: raise RuntimeError(str(reason))
        c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(mesh)
        for i,path in enumerate(materials):
            if path:
                mat=u.load_asset(path)
                if not mat: raise RuntimeError(path)
                c.set_material(i,mat)
        c.set_collision_profile_name(profile)
        c.set_cast_shadow(shadow)
        c.set_editor_property('receives_decals',decals)
        c.set_cull_distances(*cull)
        c.component_tags=[TAG,'VillageShop.'+state]+([] if collides else ['VillageShop.NoCollision'])
        if not collides or state=='Repaired':
            c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_visibility(state=='Ruined')
        c.set_hidden_in_game(state!='Ruined')
        c.add_instances(transforms,False,True,False)

    root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
    source=root/'SourceAssets/HillsVillageBlacksmith20261117/SmeltingYard'
    for group in json.loads((source/'ruined_yard.json').read_text(encoding='utf-8')):
        mesh=u.load_asset(group['mesh'])
        if not mesh: raise RuntimeError(group['mesh'])
        transforms=[u.Transform(location=p,rotation=u.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),scale=s)
                    for p,r,s in group['rows']]
        batch(mesh,transforms,'Ruined',group['collision'],group['collide'],group['shadow'],group['cull'],group['decals'],group['materials'])
    rock_paths=['VillageWindmill/Yard/Meshes/SM_MillFieldstoneB','WhiteCliffs/Meshes/Fractures/SM_QuarryChip01',
               'WhiteCliffs/Meshes/Fractures/SM_QuarryChip04']
    # Sample the calibrated repair height lattice at the eight previously procedural chip positions.
    import re
    native=(root/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl').read_text(encoding='utf8')
    data=native.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    grid=[list(map(int,row.split(','))) for row in re.findall(r'\{([-0-9,]+)\}',data)]
    for variant,path in enumerate(rock_paths):
        mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/'+path)
        bounds=mesh.get_bounding_box()
        span=bounds.max-bounds.min
        points=[]
        for i,(u0,v0,size) in enumerate(YARD_GRAVEL):
            if i%3!=variant: continue
            x,y=ORIGIN[0]+u0,ORIGIN[1]+v0
            ix,iy=math.floor(x),math.floor(y)
            fx,fy=x-ix,y-iy
            ix+=(len(grid[0])-1)//2
            iy+=(len(grid)-1)//2
            z=(1-fy)*((1-fx)*grid[iy][ix]+fx*grid[iy][ix+1])+fy*((1-fx)*grid[iy+1][ix]+fx*grid[iy+1][ix+1])
            scale=size/max(span.x,span.y)
            height=.36*size
            t=u.Transform(rotation=u.Rotator(yaw=((57*i+11)%256)*360./256.),scale=[scale,.87*scale,height/max(1.,span.z)])
            offset=u.MathLibrary.transform_location(t,u.Vector((bounds.min.x+bounds.max.x)/2,(bounds.min.y+bounds.max.y)/2,bounds.min.z))
            t.translation=u.Vector(100*x,100*y,z-.25*height)-offset
            points.append(t)
        batch(mesh,points,'Repaired','NoCollision',False,False,[3800,6200],False)
    return True
