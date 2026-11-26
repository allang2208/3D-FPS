"""Fit the roof weathering and both chimney heads to House 02's existing cook hearth."""
import unreal as u
from village_chimney import install_plume

DEST = '/Game/WorldGeneration/VillageTavern/KitchenRoof/SM_TavernChimney'
PARTS = (
    ('Flashing', 'Common', (581.,79.,620.)),
    ('Crown', 'Repaired', (581.,79.,662.9)),
    ('BrokenCrown', 'Ruined', (581.,79.,662.9)),
)


def attach_chimney(site):
    if 'VillageTavern.ThreeStoreyInn' in map(str,site.tags):
        return {'repaired_mouth_z_cm':1394.9,'existing_cook_hearth_contact':[615.,79.,-2.1]}
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles = u.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    comps = site.get_components_by_class(u.StaticMeshComponent)
    site.modify()
    for name,state,origin in PARTS:
        owner = 'VillageTavern.Chimney.'+name
        mesh = u.load_asset(DEST+name)
        if not mesh:
            raise RuntimeError('Missing fitted tavern chimney '+name)
        comp = next((c for c in comps if owner in map(str,c.component_tags)), None)
        if not comp:
            handle,error = subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,
                new_class=u.StaticMeshComponent))
            comp = handles.get_associated_object(handles.get_data(handle))
            if not comp:
                raise RuntimeError(str(error))
        comp.modify()
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_relative_transform(u.Transform(location=origin),False,True)
        comp.set_static_mesh(mesh)
        solid = state != 'Common'
        comp.component_tags = [owner,'VillageTavern.'+state,
                               'HillsStaticSupport' if solid else 'VillageTavern.NoCollision']
        comp.set_editor_property('receives_decals',False)
        comp.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        visible = state != 'Repaired'
        comp.set_visibility(visible)
        comp.set_hidden_in_game(not visible)
        comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if solid and visible
                                   else u.CollisionEnabled.NO_COLLISION)
    install_plume(site,(581.,79.,753.9),.36,1.8)
    return {'components': [name for name,_,_ in PARTS], 'roof_opening_cm': [35.,36.],
            'repaired_mouth_z_cm': 752.9, 'existing_cook_hearth_contact': [615.,79.,-2.1]}


def install_chimney(actors, plan, kit):
    site = next(a for a in actors.get_all_level_actors() if 'VillageTavern.Site' in map(str,a.tags))
    return attach_chimney(site)
