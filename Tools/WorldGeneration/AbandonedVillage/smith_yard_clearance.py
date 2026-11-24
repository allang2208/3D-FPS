"""Trim baked village verge instances only where the west smith's work yard now stands."""
from collections import Counter
import math
import unreal as u
from smith_apron import overlaps

WALL="SM_H_StoneWall_00A_Piece"
PLANTS=("sm_grass","sm_softwildgrass","sm_planttype","flower_","sm_fern","sm_bush","sm_shrub","sm_deadtree")
FOOT=("SM_Stone_0","SM_DebrisScatter","SM_H_RubblePile","SM_ForestTwig")

def clear_yard(world):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    counts=Counter()
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        label=actor.get_actor_label()
        if not label.startswith('Village_'):
            continue
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if comp.component_has_tag('VillageShop.SmithYardState'):
                continue
            mesh=comp.static_mesh
            if not mesh:
                continue
            name=mesh.get_name()
            if name.startswith(WALL) and label.endswith('_'+name):
                role='wall'
            elif name.lower().startswith(PLANTS):
                role='plants'
            elif name.startswith(FOOT):
                role='wall_foot'
            else:
                continue
            box=mesh.get_bounding_box()
            center=(box.min+box.max)*.5
            span=box.max-box.min
            discard=[]
            for i in range(comp.get_instance_count()):
                tr=comp.get_instance_transform(i,True)
                # Use the separately authored boundary wall pivots; house walls belong to their buildings.
                if role=='wall':
                    pos=tr.translation
                    inside=overlaps(pos.x*.01,pos.y*.01)
                else:
                    pos=u.MathLibrary.transform_location(tr,center)
                    reach=min(.7,.005*math.hypot(span.x*tr.scale3d.x,span.y*tr.scale3d.y))
                    inside=overlaps(pos.x*.01,pos.y*.01,reach,reach)
                if inside:
                    discard.append(i)
            if discard:
                actor.modify()
                comp.modify()
                if not comp.remove_instances(discard):
                    raise RuntimeError('Could not remove yard instances from '+label)
                counts[role]+=len(discard)
    return dict(counts)
