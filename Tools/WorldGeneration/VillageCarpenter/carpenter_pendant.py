"""The working lantern suspended from the eastern bay's floor joist."""
from collections import defaultdict

import unreal as u

from author_shop import pose, require, standing

from shop_pendants import HAND, LANTERN, hang

PENDANT = HAND.name


def install_pendant(house,repaired):
    return hang(repaired,pose(house,0,0),HAND)


def replace_hand_lantern(house,repaired):
    """Migrate just the downstairs fixture on the saved Village_Carpenter_Repaired."""
    old_top = -1.06+76.5
    old_x,old_y = 340.,-267.
    old_light = pose(house,old_x,old_y,old_top+20.5).translation
    lantern_mesh = require(LANTERN)
    bounds = lantern_mesh.get_bounding_box()
    span = bounds.max-bounds.min
    old_body = standing(house,LANTERN,old_x,old_y,old_top,-78,28./max(span.x,span.y,span.z)).translation
    previous = []
    instances = defaultdict(list)
    old_lights = 0
    old_lanterns = 0
    already_hanging = False
    for part in repaired.get_components_by_class(u.SceneComponent):
        if PENDANT in map(str,part.component_tags):
            previous.append(part)
            already_hanging = True
        elif isinstance(part,u.PointLightComponent) and (part.get_world_location()-old_light).length()<2.:
            previous.append(part)
            old_lights += 1
        elif isinstance(part,u.StaticMeshComponent) and part.static_mesh==lantern_mesh:
            if isinstance(part,u.InstancedStaticMeshComponent):
                for i in range(part.get_instance_count()):
                    if (part.get_instance_transform(i,True).translation-old_body).length()<2.:
                        instances[part].append(i)
                        old_lanterns += 1
            elif (part.get_world_location()-old_body).length()<2.:
                previous.append(part)
                old_lanterns += 1
    if not already_hanging and (old_lights!=1 or old_lanterns!=1):
        raise RuntimeError(f'Hand table contains {old_lanterns} matching lanterns and {old_lights} matching lights')
    if not previous and not instances:
        raise RuntimeError('The saved hand-table fixture was not found on '+repaired.get_actor_label())
    repaired.modify()
    system = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    root = system.k2_gather_subobject_data_for_instance(repaired)[0]
    if previous:
        handles = [system.find_handle_for_object(root,obj) for obj in previous]
        if system.k2_delete_subobjects_from_instance(root,handles)!=len(handles):
            raise RuntimeError('Could not replace the original carpenter fixture')
    for part,indices in instances.items():
        part.modify()
        for index in reversed(indices):
            if not part.remove_instance(index):
                raise RuntimeError('Could not remove the hand-table lantern instance')
    result = install_pendant(house,repaired)
    result.update(replaced_table_lanterns=old_lanterns,replaced_table_lights=old_lights)
    return result
