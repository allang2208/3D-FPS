"""Dress the smith's downstairs worktable on the wall side of the stool."""
import unreal as u
from author_shop import pose, require

PACKAGE = '/Game/WorldGeneration/TemperateHills/VillageShopRest/SM_SmithShoeingWork'


def fit(house,repaired):
    from shop_pendants import component
    repaired.modify()
    part = next((p for p in repaired.get_components_by_class(u.StaticMeshComponent)
                 if p.static_mesh and p.static_mesh.get_path_name().split('.')[0]==PACKAGE),None)
    if not part:
        part = component(repaired,u.StaticMeshComponent)
    part.modify()
    part.set_mobility(u.ComponentMobility.STATIC)
    part.set_static_mesh(require(PACKAGE))
    part.set_world_transform(pose(house,-31,-276,76.5,4),False,True)
    part.component_tags = ['VillageShop.Repaired','VillageShop.NoCollision']
    part.set_collision_profile_name('NoCollision')
    part.set_editor_property('generate_overlap_events',False)
    part.set_editor_property('ld_max_draw_distance',2000.)
    part.set_cast_shadow(False)
    part.set_hidden_in_game(True)
    part.set_visibility(False)
    return PACKAGE
