"""Plot 03 shop fittings. All coordinates refer to the finished floor in centimetres."""
from pathlib import Path

import unreal as u

from author_shop import CRATE, KIT, pose, require, standing


# Native potion_workbench is pivoted at the back-left of its L, not in the middle.
# At this transform the tabletop camera and customer approach both face the open centre.
STATION = (37., 302., -1., 0.)
ROOT = '/Game/WorldGeneration/TemperateHills/'
CUSTOM = ROOT+'VillageHerbalist/Props'
TRADING = '/Game/WorldGeneration/VillageTavern/'
SERVICE = TRADING+'Service/SM_Tavern'
COUNTER = TRADING+'Furniture/SM_Tavern'
ALCHEMY = '/Game/Items/AlchemyMaterials20261015/V3/Meshes/SM_Alchemy_'
POTION = '/Game/Items/Consumables/PotionTiersV1/SM_Potion_'
GINGER = ROOT+'WetForest/Underfoot/SM_JungleGinger'
FUNGI = ROOT+'EcologyUpgrade/Fungi/pdvv2_tier_2/StaticMeshes/pdvv2_LOD0_TIER2_'
LINEN = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
LEDGER = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/Book_634f4e59/Meshes/SM_Book_634f4e59'
FLOWERS = '/Game/PN_FoliageCollection/Meshes/flowerMesh/flower_07_01'
SUPPLIES = ('WindowPot','GatheringSieve','DryingStand','DryBunch','FlowerBunch','ShelfLip')
SURFACES = {
    'Clay': TRADING+'Service/MI_TavernClay',
    'Slip': TRADING+'Service/MI_TavernOliveGlaze',
    'Earth': '/Game/Building/PlantingBed20261017/Materials/M_TilledEarth',
    'Oak': ROOT+'VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'Wicker': ROOT+'VillageCarpenter/Props/Surfaces/M_CarpenterCut',
    'Twine': '/Game/Weapons/DarkBow20260925/ModularV13/M_Bow_GripLinen',
    'Leaf': '/Game/Building/PotionWorkbench20261015/V1/Materials/M_PW_Herbs',
}


def custom(role):
    return CUSTOM+'/SM_Herbalist'+role


def prepare_supplies():
    """Import purpose-built fittings with the village's existing PBR surfaces."""
    folder = Path(__file__).resolve().parents[3]/'SourceAssets/HillsVillageHerbalist'
    library = u.EditorAssetLibrary
    for role in SUPPLIES:
        path = custom(role)
        if library.does_asset_exist(path):
            continue
        name = path.rsplit('/',1)[1]
        task = u.AssetImportTask()
        task.filename = str(folder/(name+'.fbx'))
        task.destination_path = CUSTOM
        task.destination_name = name
        task.automated = True
        task.save = False
        task.factory = u.FbxFactory()
        opts = u.FbxImportUI()
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_mesh,opts.import_as_skeletal = True,False
        opts.import_materials,opts.import_textures = False,False
        data = opts.static_mesh_import_data
        data.combine_meshes = True
        data.convert_scene_unit = True
        data.generate_lightmap_u_vs = True
        data.auto_generate_collision = (role == 'DryingStand')
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options = opts
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = require(path)
        for index,slot in enumerate(mesh.static_materials):
            mesh.set_material(index,require(SURFACES[str(slot.material_slot_name)]))
        if not library.save_loaded_asset(mesh,False):
            raise RuntimeError('Could not save '+path)


def furnish(house,add):
    prepare_supplies()
    def floor(state,path,x,y,z=0,yaw=0,scale=1,profile='NoCollision'):
        add(state,path,standing(house,path,x,y,z,yaw,scale),profile=profile)

    def fitted(state,path,x,y,z,yaw,size,profile='NoCollision'):
        # Use the catalogue mesh at a realistic shop-counter size, independent
        # of the inconsistent pivots and export units of the donor collections.
        bounds = require(path).get_bounding_box()
        span = bounds.max-bounds.min
        scale = size/max(span.x,span.y,span.z)
        floor(state,path,x,y,z,yaw,scale,profile)
        return span.z*scale

    def laid_on_side(state,path,x,y,z,yaw,size):
        # Bottles and herb bundles stand along Z; the scanned ledger is on
        # its spine. After a quarter turn their original X span sets the height.
        bounds = require(path).get_bounding_box()
        span = bounds.max-bounds.min
        scale = size/max(span.x,span.y,span.z)
        tilt = u.Transform(rotation=u.Rotator(pitch=90,yaw=yaw),scale=[scale]*3)
        centre = u.MathLibrary.transform_location(tilt,(bounds.max+bounds.min)*.5)
        tilt.translation = u.Vector(x-centre.x,y-centre.y,z+span.x*scale*.5-centre.z)
        add(state,path,u.MathLibrary.compose_transforms(tilt,pose(house,0,0)),profile='NoCollision')

    def pot(x,y,z,scale,plant,yaw,diameter):
        floor('Repaired',custom('WindowPot'),x,y,z,yaw,scale)
        # Align the authored plant root with the actual earth surface. The pivot
        # of these foliage meshes is the stem base, irrespective of crown lean.
        b = require(plant).get_bounding_box()
        s = diameter/max(b.max.x-b.min.x,b.max.y-b.min.y,b.max.z-b.min.z)
        add('Repaired',plant,pose(house,x,y,z+16.8*scale-b.min.z*s,yaw,s),profile='NoCollision')

    repaired = 'Repaired'
    ruined = 'Ruined'
    # The panelled front faces the open customer aisle. Staff enter from the
    # north end into the space between the counter and the east wall shelves.
    floor(repaired,COUNTER+'Counter',125,-167,0,180,.77,'BlockAll')
    floor(ruined,COUNTER+'BrokenCounter',125,-167,0,180,.77,'BlockAll')
    surface = require(COUNTER+'Counter').get_bounding_box()
    top = (surface.max.z-surface.min.z)*.77
    # A specimen dish and two finished tinctures greet the door. The middle
    # stays clear for handing goods across; the ledger and wraps sit at the till.
    floor(repaired,SERVICE+'Dish',120,-236,top,-12,.85)
    fitted(repaired,FUNGI+'001',120,-236,top+1.5,34,13)
    fitted(repaired,POTION+'Common_Closed',141,-219,top,28,15)
    fitted(repaired,POTION+'Medium_Closed',139,-238,top,-37,17)
    laid_on_side(repaired,LEDGER,118,-107,top,7,23)
    fitted(repaired,LINEN,138,-85,top,83,20)
    # The original counter has two open shelves on the staff side.
    floor(repaired,custom('GatheringSieve'),133,-229,16.55*.77,3,.57)
    fitted(repaired,LINEN,135,-167,56.55*.77,87,22)

    # Turn the former west-wall rack into a dispensary behind the counter.
    # Heavy base stock sits lowest and finished remedies are within easy reach.
    shelf = KIT+'OakShelf'
    shelf_x,shelf_y = 291,-165
    floor(repaired,shelf,shelf_x,shelf_y,0,-90,1,'BlockAll')
    for shelf_top in (13.5,65.5,117.5):
        floor(repaired,custom('ShelfLip'),shelf_x-18.8,shelf_y,shelf_top,-90)
    for offset,role,turn,size in (
            (-53,'PureBaseFluid',8,26),(-28,'PureBaseFluid',38,25),
            (12,'CompoundStabilizer',-15,22),(46,'CompoundStabilizer',9,22)):
        fitted(repaired,ALCHEMY+role,shelf_x-1,shelf_y+offset,13.5,turn+180,size)
    for offset,role,turn,size in (
            (-53,'SilverleafEssence',23,17),(-36,'SilverleafEssence',-13,17),
            (-11,'RedveinExtract',36,19),(14,'BluemarrowCrystals',-19,18)):
        fitted(repaired,ALCHEMY+role,shelf_x,shelf_y+offset,65.5,turn+180,size)
    floor(repaired,SERVICE+'Pitcher',shelf_x+3,shelf_y+49,65.5,156,.8)
    for offset,role,turn in ((-53,'Common',25),(-38,'Common',9),(-9,'Medium',36),(12,'Medium',3)):
        fitted(repaired,POTION+role+'_Closed',shelf_x-1,shelf_y+offset,117.5,turn+180,17)
    floor(repaired,custom('GatheringSieve'),shelf_x+1,shelf_y+45,117.5,72,.62)
    fitted(repaired,FUNGI+'002',shelf_x+1,shelf_y+45,118.7,61,11)
    floor(repaired,custom('GatheringSieve'),shelf_x+2,shelf_y-44,165.5,98,.9)
    fitted(repaired,LINEN,shelf_x,shelf_y+12,165.5,95,28)

    # The herb rail occupies the solid pier between the door and street window.
    # Both loops are authored in the YZ plane around a full-size X-axis dowel.
    rail_x,rail_y = 15,-315
    floor(repaired,custom('DryingStand'),rail_x,rail_y,0,0,1,'BlockAll')
    for offset,role,turn in ((-46,'DryBunch',0),(-18,'FlowerBunch',180),
                             (13,'DryBunch',180),(45,'FlowerBunch',0)):
        add(repaired,custom(role),pose(house,rail_x+offset,rail_y,162,turn),profile='NoCollision')
    floor(repaired,custom('GatheringSieve'),rail_x-30,rail_y,20,18,.79)
    fitted(repaired,LINEN,rail_x+30,rail_y,20,4,22)

    # The bottom of the street window frame is 107.4 cm above the floor.
    # Pocket two oak brackets into its solid breast wall and seat a display
    # board on them. The outer sill and shutters stay clear.
    oak = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_01A'
    bounds = require(oak).get_bounding_box()
    span,centre = bounds.max-bounds.min,(bounds.max+bounds.min)*.5
    def sill_timber(start,end,width,height):
        a,b = u.Vector(*start),u.Vector(*end)
        axis = b-a
        fitted_pose = u.Transform(location=(a+b)*.5,rotation=u.MathLibrary.make_rot_from_x(axis),
                                  scale=[axis.length()/span.x,width/span.y,height/span.z])
        local = u.MathLibrary.compose_transforms(u.Transform(location=-centre),fitted_pose)
        add(repaired,oak,u.MathLibrary.compose_transforms(local,pose(house,0,0)),profile='BlockAll')

    for x in (140,223):
        sill_timber((x,-343,80),(x,-304,104),6,7)
    sill_timber((123,-320,106),(244,-320,106),39,4)
    pot(156,-321,108,1.08,GINGER+'D',-37,51)
    floor(repaired,custom('GatheringSieve'),212,-319,108,16,.85)
    laid_on_side(repaired,custom('FlowerBunch'),212,-319,109.2,11,26)

    # Fresh cuttings sit beside the street window and clear of the door.
    pot(-311,-194,0,.94,FLOWERS,23,31)
    pot(260,-387,0,1.06,GINGER+'E',81,46)
    crate_top = fitted(repaired,CRATE,290,-293,0,-4,49,'BlockAll')
    floor(repaired,custom('GatheringSieve'),288,-293,crate_top,33,.84)
    fitted(repaired,FUNGI+'000',288,-293,crate_top+1.6,34,16)

    # Failed trade: stock has been taken and the surviving fragments collect
    # in the empty dispensary and under the street window.
    fitted(ruined,KIT+'AbandonedTimber',303,-165,0,89,128)
    floor(ruined,COUNTER+'BrokenStool',266,-272,0,27,.87)
    floor(ruined,custom('GatheringSieve'),52,-318,0,51,.83)
    floor(ruined,SERVICE+'Sherd',158,-198,0,-23,1.)
    floor(ruined,SERVICE+'Sherd',168,-192,0,68,.6)
    floor(ruined,SERVICE+'Sherd',94,-387,0,149,1.21)

    # The lost alchemy bench left a collapsed timber base and scattered
    # earthenware on its old footprint. Keep the central approach clear.
    fitted(ruined,KIT+'AbandonedTimber',186,262,0,8,121)
    laid_on_side(ruined,SERVICE+'Tankard',243,221,0,-28,17)
    floor(ruined,SERVICE+'Sherd',228,216,0,-51,1.4)
    floor(ruined,SERVICE+'Sherd',249,198,0,36,.93)
