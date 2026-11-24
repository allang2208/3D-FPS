"""Place dormant furnace smoke and a separate wood/charcoal fire at their own openings."""
import unreal as ue
from shop_staff_light import HEARTH_FIRE

FLUE_TAG = 'VillageShop.FlueSmoke'
FUEL_TAG = 'VillageShop.HearthFire'
SMITH_FIRE_AT_STATION = (53.,256.,79.)
FURNACE = '/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke'
WOOD_FIRE = HEARTH_FIRE


def effect(site, tag, asset, pos, scale, distance):
    site.modify()
    component = next((c for c in site.get_components_by_class(ue.NiagaraComponent)
                      if tag in map(str, c.component_tags)), None)
    if not component:
        subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        parent = subs.k2_gather_subobject_data_for_instance(site)[0]
        handle, reason = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent,
                                                                       new_class=ue.NiagaraComponent))
        helpers = ue.SubobjectDataBlueprintFunctionLibrary
        component = helpers.get_associated_object(helpers.get_data(handle))
        if not component:
            raise RuntimeError(str(reason))
    system = ue.load_asset(asset)
    if not system:
        raise RuntimeError('Missing village hearth effect ' + asset)
    component.modify()
    component.component_tags = [tag]
    component.set_mobility(ue.ComponentMobility.MOVABLE)
    component.set_auto_activate(False)
    component.set_visibility(False)
    component.set_hidden_in_game(True)
    component.set_asset(system)
    component.set_relative_transform(ue.Transform(location=pos, scale=scale), False, True)
    component.set_cast_shadow(False)
    component.set_cull_distance(distance)
    return component


def hearth(site, outlet, smoke_scale, rate, heat, fuel, fire_size):
    smoke = effect(site, FLUE_TAG, FURNACE, outlet, smoke_scale, 7100.)
    # Mature, low-draught household fire: no pale ignition steam or smelting batch puff.
    smoke.set_variable_float('User.Heat', heat)
    smoke.set_variable_float('User.SpawnRate', rate)
    smoke.set_variable_float('User.Ignition', 1.)
    smoke.set_variable_float('User.Puff', 0.)
    # The repair handler enables just the fuel's Fire and Sparks emitters.
    effect(site, FUEL_TAG, WOOD_FIRE, fuel, (fire_size,)*3, 2850.)


def install_plume(site, outlet, *_legacy_preview_settings):
    # Retain the existing bakehouse and tavern installer interface. Both once pointed
    # at the larger example chimney sprite. The furnace donor uses a 36.8 cm throat.
    if 'VillageBakery.Site' in map(str, site.tags):
        # The lower fuel bay opens south; its back wall starts at y=705, and its
        # ceiling is z=74. Keep the flame seated between the front ends of the logs.
        hearth(site, outlet, (.92,.92,.61), 9., .63, (-245.,663.,30.), .39)
    else:
        # Restored cook hearth: mesh +46 in X is west of the rear pivot after its 180° turn.
        hearth(site, outlet, (.86,.86,.58), 8., .58, (569.,79.,30.), .49)


def install_smith_hearth(station):
    hearth(station, (80.,460.,1145.), (1.16,1.16,.72), 11., .81, SMITH_FIRE_AT_STATION, .71)


def install_village_hearths(actors, plan, kit):
    # Bakehouse and tavern already attach both effects while assembling their shells.
    # The smith's authored forge meshes live on shared scenery actors; carry its
    # emitters on the repairable station itself so the heat follows its state.
    smith = next(a for a in actors.get_all_level_actors() if isinstance(a, ue.HillsBlacksmith))
    install_smith_hearth(smith)
    return {'blacksmith': 'forge grate', 'tavern': 'cook hearth', 'bakery': 'lower firebox',
            'fire_and_sparks': WOOD_FIRE, 'plumes': FURNACE}
