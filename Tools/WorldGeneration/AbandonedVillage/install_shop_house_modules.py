"""Replace only repaired architectural components on a furnished shop actor."""
from collections import defaultdict

import unreal as u


def replace_modules(actors, shop, rows, old_paths):
    site = next(a for a in actors.get_all_level_actors() if shop+'.Site' in map(str,a.tags))
    site.modify()
    restored, group = shop+'.Restored', shop+'.Group.'
    components = site.get_components_by_class(u.StaticMeshComponent)
    by_key = {str(tag):c for c in components for tag in c.component_tags if str(tag).startswith(group)}
    poses = defaultdict(list)
    for path,frame,solid in rows:
        poses[path,solid].append(frame)
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib = u.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    counts = {}
    for (path,solid), instances in poses.items():
        key = group+path+(('.Block' if shop=='VillageBakery' else '.Solid') if solid else '.Art')
        mesh = u.load_asset(path)
        if not mesh:
            raise RuntimeError('Missing architectural piece '+path)
        comp = by_key.get(key)
        if not comp:
            handle, error = subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,
                                                    new_class=u.InstancedStaticMeshComponent))
            comp = lib.get_associated_object(lib.get_data(handle))
            if not comp:
                raise RuntimeError(str(error))
        comp.modify()
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_relative_transform(u.Transform(),False,True)
        comp.clear_instances()
        comp.set_static_mesh(mesh)
        comp.set_editor_property('override_materials',[])
        comp.component_tags = [restored,key]+([shop+'.Solid','HillsStaticSupport'] if solid else [])
        comp.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property('receives_decals',False)
        comp.set_editor_property('generate_overlap_events',False)
        comp.set_visibility(False)
        comp.set_hidden_in_game(True)
        comp.add_instances(instances,False,False,False)
        counts[path]=len(instances)
    for c in components:
        if restored not in map(str,c.component_tags) or not c.static_mesh:
            continue
        if c.static_mesh.get_path_name().split('.')[0] not in old_paths:
            continue
        c.modify()
        c.component_tags=[t for t in c.component_tags if str(t).startswith(group)]
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_visibility(False)
        c.set_hidden_in_game(True)
        if isinstance(c,u.InstancedStaticMeshComponent):
            c.clear_instances()
        c.set_static_mesh(None)
        c.set_editor_property('override_materials',[])
    return counts
