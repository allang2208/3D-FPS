"""Apply the smith-only finishes and register workfloor props with the existing repair assembly."""
import sys
from pathlib import Path
import unreal as u
from author_shop import pose, standing, require
from LoftR3.design import HEARTH

ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor'
MAT=ROOT+'/Materials/M_Smith'
BARREL='/Game/Props/CastingStation20260926/SM_CoolingBarrel'
WATER='/Game/Props/CastingStation20260926/SM_CoolingWater'
TAG='VillageShop.SmithWorkfloor'
BARREL_CENTER=(42,190)
STATION_LABEL='Village_01_Blacksmith_Forge'


def apply(house,station):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'AbandonedVillage'))
    from shop_pendants import component,remove_components
    assemblies={a.get_actor_label():a for a in station.get_editor_property('shop_assemblies') if a}
    repaired=assemblies['Village_Blacksmith_Repaired']
    common=assemblies['Village_Blacksmith_Common']
    ruined=assemblies['Village_Blacksmith_Ruined']
    actor_parts=lambda a:a.get_components_by_class(u.StaticMeshComponent)
    barrels=[c for c in actor_parts(repaired) if c.static_mesh and c.static_mesh.get_path_name().split('.')[0]==BARREL]
    barrel,=barrels
    if barrel.get_instance_count()!=1:raise RuntimeError('Expected one standalone quench barrel')
    barrel_frame=standing(house,BARREL,*BARREL_CENTER)
    finishes={key:require(MAT+key) for key in ('QuenchOak','ScaleIron','HearthStone','FiredBrick')}
    station_body,=[c for c in actor_parts(station) if c.static_mesh and c.static_mesh.get_name().startswith('SM_CastingStation')]
    changed=[]
    def bind(c,mapping):
        indices={str(slot.material_slot_name):i for i,slot in enumerate(c.static_mesh.static_materials)}
        for key,finish in mapping.items():
            c.set_material(indices[key],finishes[finish])
        changed.append([c.static_mesh.get_name(),dict(mapping)])
    station.modify()
    station_body.modify()
    bind(station_body,{'BarrelWood':'QuenchOak','DarkSteel':'ScaleIron','Masonry':'HearthStone'})
    common.modify()
    repaired.modify()
    remove_components(repaired,[c for c in actor_parts(repaired) if TAG in map(str,c.component_tags)])
    ruined.modify()
    for actor in (common,repaired,ruined):
        for c in actor_parts(actor):
            mesh=c.static_mesh
            if not mesh:continue
            name=mesh.get_name()
            mapping={}
            if name=='SM_SmithLoft_ForgeHearth':
                mapping={'Stone':'HearthStone','Firebrick':'FiredBrick','Iron':'ScaleIron'}
            elif name=='SM_VillageHearthPad':
                mapping={'Stone':'HearthStone'}
            elif c==barrel:
                mapping={'DarkSteel':'ScaleIron','BarrelWood':'QuenchOak'}
            else:
                for i,slot in enumerate(mesh.static_materials):
                    donor=slot.material_interface
                    if donor and donor.get_name()=='MI_DarkForgedIron':
                        mapping[str(slot.material_slot_name)]='ScaleIron'
            if mapping:
                c.modify()
                bind(c,mapping)
    if not barrel.update_instance_transform(0,barrel_frame,True,True,True):
        raise RuntimeError('Could not relocate the quench barrel')
    water_frame=u.MathLibrary.compose_transforms(u.Transform(location=[0,0,42]),barrel_frame)
    from ForgeR2.refit import BODY,FUEL
    side_blast=any(c.static_mesh and c.static_mesh.get_path_name().split('.')[0]==BODY for c in actor_parts(common))
    placements=[
        (WATER,water_frame,'NoCollision'),
        (ROOT+'/SM_SmithBellows',pose(house,69,294,0),'BlockAll'),
        (ROOT+'/SM_SmithCoalBunker',pose(house,324,318,0,-6),'BlockAll'),
        (FUEL if side_blast else ROOT+'/SM_SmithHearthDressing',pose(house,*HEARTH),'NoCollision')]
    for path,frame,profile in placements:
        part=component(repaired,u.StaticMeshComponent)
        part.set_mobility(u.ComponentMobility.STATIC)
        part.set_static_mesh(require(path))
        if path==WATER:
            water_slot=station_body.static_mesh.get_material_index('Water')
            part.set_material(0,station_body.get_material(water_slot))
        part.set_world_transform(frame,False,True)
        part.component_tags=[TAG,'VillageShop.Repaired']+(['VillageShop.NoCollision'] if profile=='NoCollision' else [])
        part.set_collision_profile_name(profile)
        part.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        part.set_editor_property('generate_overlap_events',False)
        part.set_visibility(False)
        part.set_hidden_in_game(True)
    return dict(revision='SmithWorkfloorR1',bindings=changed,barrel_center_cm=BARREL_CENTER,
                additions=[p for p,_,_ in placements])
