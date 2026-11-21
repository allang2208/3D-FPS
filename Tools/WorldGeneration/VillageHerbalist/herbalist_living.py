"""The apothecary's furnished loft, in plot 03 floor-local centimetres."""
import unreal as u

from author_shop import KIT, pose, require, standing
from herbalist_loft import LOFT_Z


SCANS = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/'
CASEBOOK = SCANS+'Book_43a26a5c/Meshes/SM_Book_43a26a5c'
LEDGER = SCANS+'Book_634f4e59/Meshes/SM_Book_634f4e59'
LINEN = SCANS+'FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
TAVERN = '/Game/WorldGeneration/VillageTavern/'
POTTERY = TAVERN+'StonewareDetail/SM_Tavern'
SIEVE = '/Game/WorldGeneration/TemperateHills/VillageHerbalist/Props/SM_HerbalistGatheringSieve'
CHEST = '/Game/Props/GamedevTreasureChestV3_20261004/Meshes/SM_TreasureChest_Closed'
LANTERN = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
LIGHTING = '/Game/WorldGeneration/TemperateHills/VillageHerbalist/Lighting'
DESK_WICK = LIGHTING+'/MI_HerbalistDeskWick'

BED_X, BED_Y = 164., 151.
DESK_X, DESK_Y = 103., -273.
# Finished height of the village oak tabletop used by both workshops.
DESK_TOP = LOFT_Z+76.5
LAMP_X, LAMP_Y = DESK_X-44., DESK_Y-13.
LAMP_HEIGHT = 29.


def furnish_living(house, add):
    if not u.EditorAssetLibrary.does_asset_exist(DESK_WICK):
        wick = u.AssetToolsHelpers.get_asset_tools().create_asset(
            DESK_WICK.rsplit('/',1)[1],LIGHTING,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        if not wick:
            raise RuntimeError('Could not create the desk lantern wick')
        edit = u.MaterialEditingLibrary
        edit.set_material_instance_parent(wick,require(LANTERN).get_material(0))
        edit.set_material_instance_scalar_parameter_value(wick,'TS00_Emissive_Multiplier',.8)
        if not u.EditorAssetLibrary.save_loaded_asset(wick,False):
            raise RuntimeError('Could not save the desk lantern wick')

    def furniture(state, path, x, y, yaw=0., scale=1.):
        add(state,path,standing(house,path,x,y,LOFT_Z,yaw,scale))

    def prop(state, path, x, y, surface, size, yaw=0., pitch=0., materials=(), profile='NoCollision'):
        # Measure before rotating. The scanned volumes have different pivots,
        # and books lie flat here although their catalogue orientation is upright.
        bounds = require(path).get_bounding_box()
        span = bounds.max-bounds.min
        scale = size/max(span.x,span.y,span.z)
        local = u.Transform(rotation=u.Rotator(yaw=yaw,pitch=pitch),scale=[scale]*3)
        corners = [u.MathLibrary.transform_location(local,u.Vector(a,b,c))
                   for a in (bounds.min.x,bounds.max.x) for b in (bounds.min.y,bounds.max.y)
                   for c in (bounds.min.z,bounds.max.z)]
        middle_x = (max(p.x for p in corners)+min(p.x for p in corners))*.5
        middle_y = (max(p.y for p in corners)+min(p.y for p in corners))*.5
        bottom = min(p.z for p in corners)
        local.translation = u.Vector(x-middle_x,y-middle_y,surface-bottom)
        add(state,path,u.MathLibrary.compose_transforms(local,pose(house,0,0)),materials,profile=profile)
        return surface+max(p.z for p in corners)-bottom

    # East-side bed, head toward the back wall. Keep both long sides and the
    # foot clear; the west landing opens directly onto the centre of the room.
    furniture('Repaired',KIT+'TimberBed',BED_X,BED_Y)
    shelf_x, shelf_y, shelf_scale = 24.,296.,.82
    furniture('Repaired',KIT+'OakShelf',shelf_x,shelf_y,scale=shelf_scale)
    prop('Repaired',CHEST,117.,290.,LOFT_Z,55.,180.,profile='BlockAll')

    # The low shelf holds the collecting sieve. Clean linen, a wash jug and
    # a small stack of casebooks share the upper shelves at reachable heights.
    low = LOFT_Z+13.5*shelf_scale
    middle = LOFT_Z+65.5*shelf_scale
    high = LOFT_Z+117.5*shelf_scale
    prop('Repaired',SIEVE,shelf_x+14.,shelf_y,low,27.,4.)
    prop('Repaired',LINEN,shelf_x-24.,shelf_y,middle,31.,-4.)
    prop('Repaired',POTTERY+'Pitcher',shelf_x+26.,shelf_y,middle,25.,35.)
    stacked = prop('Repaired',LEDGER,shelf_x-13.,shelf_y,high,24.,-2.,90.)
    prop('Repaired',CASEBOOK,shelf_x-12.,shelf_y,stacked,21.,8.,90.)

    # The window desk doubles as a supper table. Group the writing and
    # eating things at opposite ends so the surface in front of the stool is free.
    furniture('Repaired',KIT+'OakTable',DESK_X,DESK_Y)
    furniture('Repaired',KIT+'OakStool',DESK_X-7.,DESK_Y+75.,-8.)
    prop('Repaired',CASEBOOK,DESK_X-20.,DESK_Y+4.,DESK_TOP,25.,-11.,90.)
    prop('Repaired',POTTERY+'Dish',DESK_X+28.,DESK_Y+12.,DESK_TOP,19.,7.)
    prop('Repaired',POTTERY+'Tankard',DESK_X+49.,DESK_Y+12.,DESK_TOP,13.,-31.)
    prop('Repaired',LANTERN,LAMP_X,LAMP_Y,DESK_TOP,LAMP_HEIGHT,21.,materials=(DESK_WICK,))

    # Remnants stay in their former furniture bays, away from the stair opening.
    furniture('Ruined',TAVERN+'Furniture/SM_TavernBrokenTable',DESK_X,DESK_Y,-4.,.72)
    furniture('Ruined',TAVERN+'Furniture/SM_TavernBrokenStool',DESK_X+11.,DESK_Y+67.,32.,.88)
    furniture('Ruined',KIT+'AbandonedTimber',BED_X,BED_Y,72.,.83)
    prop('Ruined',POTTERY+'Sherd',DESK_X+69.,DESK_Y+46.,LOFT_Z,9.,29.)
    prop('Ruined',SIEVE,shelf_x+15.,shelf_y-8.,LOFT_Z,29.,-31.,180.)


def add_living_light(house, repaired_actor, component):
    lamp = component(repaired_actor,u.SpotLightComponent)
    lamp.set_mobility(u.ComponentMobility.MOVABLE)
    # Just outside the glass on its desk-facing side, below the metal cap.
    position = pose(house,LAMP_X+9.,LAMP_Y+4.,DESK_TOP+LAMP_HEIGHT*.47).translation
    book = pose(house,DESK_X-17.,DESK_Y+5.,DESK_TOP).translation
    lamp.set_world_location_and_rotation(position,u.MathLibrary.find_look_at_rotation(position,book),False,True)
    lamp.set_intensity_units(u.LightUnits.LUMENS)
    lamp.set_editor_property('use_temperature',True)
    lamp.set_temperature(2920.)
    lamp.set_intensity(2.5)
    lamp.set_inner_cone_angle(28.)
    lamp.set_outer_cone_angle(73.)
    lamp.set_attenuation_radius(124.)
    lamp.set_source_radius(2.5)
    lamp.set_specular_scale(.4)
    lamp.set_cast_shadows(True)
    lamp.set_editor_property('max_draw_distance',2100.)
    lamp.set_editor_property('max_distance_fade_range',400.)
    lamp.component_tags=['VillageHerbalist.Repaired']
    lamp.set_visibility(False)
    lamp.set_hidden_in_game(True)
    return 1
