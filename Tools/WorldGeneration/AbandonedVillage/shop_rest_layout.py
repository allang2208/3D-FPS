"""Apply the three fitted gunshop changes and dress the existing smith table."""
import json
import unreal as u
from author_shop import BENCH, require
from BenchWork.layout import fit as dress_smith
from gunshop_furnish import DESK_CUP, LOFT, POTS, PRESS_EWER, WAITING_BENCH_SIZE


def fitted_box(mesh,center,size,yaw,site):
    bounds = mesh.get_bounding_box()
    mid = (bounds.max+bounds.min)*.5
    base = u.Vector(mid.x,mid.y,bounds.min.z)
    frame = u.Transform(location=center,rotation=u.Rotator(yaw=yaw),scale=u.Vector(*size)/(bounds.max-bounds.min))
    local = u.MathLibrary.compose_transforms(u.Transform(location=-base),frame)
    return u.MathLibrary.compose_transforms(local,site.get_actor_transform())


def refit(site,path,old,new):
    mesh = require(path)
    original = fitted_box(mesh,*old,site)
    final = fitted_box(mesh,*new,site)
    matches = []
    for part in site.get_components_by_class(u.StaticMeshComponent):
        if part.static_mesh!=mesh or 'VillageGunshop.Restored' not in map(str,part.component_tags):
            continue
        instances = isinstance(part,u.InstancedStaticMeshComponent)
        poses = [(i,part.get_instance_transform(i,True)) for i in range(part.get_instance_count())] if instances else [(None,part.get_world_transform())]
        for i,at in poses:
            if min((at.translation-t.translation).length() for t in (original,final))<1.:
                matches.append((part,i))
    if len(matches)!=1:
        raise RuntimeError(f'Expected one fitted gunshop prop at {old[0]} for {path}, found {len(matches)}')
    part,i = matches[0]
    site.modify()
    part.modify()
    if i is None:
        part.set_world_transform(final,False,True)
    elif not part.update_instance_transform(i,final,True,True,True):
        raise RuntimeError('Could not move '+path)
    return dict(mesh=path,position_cm=new[0],size_cm=new[1],yaw=new[2])


def apply(project):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    sites = {a.get_actor_label():a for a in actors.get_all_level_actors()}
    plan = json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    smith = next(h for h in plan['houses'] if h[0]=='01')
    gun = sites['Village_09_Gunshop']
    updates = [
        (BENCH,((259,53,0),(133,40,45),180),((259,53,0),WAITING_BENCH_SIZE,0)),
        (POTS+'Tankard',((-227,171,LOFT+42),(10,12,11),17),(DESK_CUP,(10,12,11),17)),
        (POTS+'Pitcher',((-235,726,LOFT+51),(17,21,26),-12),(PRESS_EWER,(17,21,26),-12))
    ]
    return dict(gunshop=[refit(gun,*update) for update in updates],
                smith=dress_smith(smith,sites['Village_Blacksmith_Repaired']))
