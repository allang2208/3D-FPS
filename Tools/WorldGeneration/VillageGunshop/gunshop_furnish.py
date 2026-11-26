"""Shop fittings in centimetres, relative to the centre of the street door."""
import json
from pathlib import Path

HILLS = '/Game/WorldGeneration/TemperateHills/'
FIX = HILLS + 'VillageGunshop/Fixtures/SM_Gunshop_'
TIMBER = HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_Village'
TAVERN = '/Game/WorldGeneration/VillageTavern/'
POTS = TAVERN + 'StonewareDetail/SM_Tavern'
QUX = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/'
LINEN = QUX + 'FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
BOOK = QUX + 'Book_634f4e59/Meshes/SM_Book_634f4e59'
CHEST = '/Game/Props/GamedevTreasureChestV3_20261004/Meshes/SM_TreasureChest_Closed'
RACK = (-198., 690., 0.)
RACK_MODELS = (('m16a2', (-56., -7., 151.)), ('akm', (57., -7., 152.)),
               ('super90', (-18., -7., 70.)))
COUNTER = (-106., 486., 0.)
COUNTER_TOP = 98.
BOARDS = (315., 456.)
# Inner plaster is at X=-475. The 10 cm standoffs bed half a centimetre into it.
BOARD_X = -465.5
LOFT = 340.
WAITING_BENCH_SIZE = (164,47,57.5)
DESK_CUP = (-103,153,LOFT+76)
# The linen press has posts above its top planks. Use the plank surface.
PRESS_EWER = (-170,839,LOFT+165.5*.9)

def counter_point(dx,dy,dz=0.):
    return COUNTER[0]+dx, COUNTER[1]+dy, COUNTER_TOP+dz


def catalogue():
    root = Path(__file__).resolve().parents[3]
    recipes = json.loads((root / 'Content/ColdSteelData/gun-assembly.json').read_text(encoding='utf-8-sig'))
    return {r['output'].removeprefix('ue_'): r for r in recipes['recipes']}


def assembly(recipe, target, upright, load):
    """Move the complete catalogue display pose as one rigid body. Preserve all part pivots."""
    import unreal as u
    if upright:
        rot = u.MathLibrary.make_rot_from_xz(u.Vector(0, 0, -1), u.Vector(0, 1, 0))
    else:
        rot = u.Rotator(yaw=77.)
    rotation = u.Transform(rotation=rot)
    pieces = [(recipe['body_mesh'], recipe['body_position'])]
    pieces.extend((part['mesh'], part['target']) for part in recipe['parts'])
    # Read actual bounds, including the fitted factory stock and magazine. Catalogue meshes
    # are already laid on their sides and scaled together by the original asset author.
    corners = []
    origins = []
    for path, position in pieces:
        center = u.MathLibrary.transform_location(rotation, u.Vector(*position))
        bounds = load(path).get_bounding_box()
        frame = u.Transform(location=center, rotation=rot)
        origins.append((path, center))
        corners.extend(u.MathLibrary.transform_location(frame, u.Vector(x, y, z))
                       for x in (bounds.min.x, bounds.max.x) for y in (bounds.min.y, bounds.max.y)
                       for z in (bounds.min.z, bounds.max.z))
    lo = [min(getattr(c, a) for c in corners) for a in 'xyz']
    hi = [max(getattr(c, a) for c in corners) for a in 'xyz']
    shift = u.Vector(*target) - u.Vector((lo[0]+hi[0])*.5, (lo[1]+hi[1])*.5, lo[2])
    return [(path, u.Transform(location=center+shift, rotation=rot)) for path, center in origins]


def build_furnishings(place):
    import unreal as u
    from functools import lru_cache
    @lru_cache(None)
    def load(path):
        mesh = u.load_asset(path)
        if not mesh:
            raise RuntimeError('Missing gunshop display mesh ' + path)
        return mesh

    def rigid(role, path, position, rot, solid=False):
        loc = (position.x,position.y,position.z) if isinstance(position,u.Vector) else position
        place.rigid(role, path, loc, (rot.pitch, rot.yaw, rot.roll), 1., solid)

    def authored(role, name, p, yaw=0, solid=False):
        rigid(role, FIX+name, p, u.Rotator(yaw=yaw), solid)

    recipes = catalogue()
    authored('SmithWeaponRack', 'FinishingRack', RACK, solid=True)
    for key, local in RACK_MODELS:
        for path, frame in assembly(recipes[key], local, True, load):
            rigid('Rack_'+key, path, frame.translation+u.Vector(*RACK), frame.rotation.rotator())

    # The finished face of the counter and its foot rail point towards the public entrance.
    # The user can approach the middle section while the keeper stands behind it.
    place('SalesCounter', TAVERN+'Furniture/SM_TavernCounter', COUNTER, (82,254,COUNTER_TOP), -90, True)
    case = counter_point(-71.,-1.)
    authored('GlazedSampleCase', 'CounterCase', case)
    case_origin = u.Vector(*case)
    for path, frame in assembly(recipes['m1911'], (-1.,1.,5.25), False, load):
        rigid('Case_m1911', path, case_origin+frame.translation, frame.rotation.rotator())
    authored('CounterInspectionTray','CounterTray',counter_point(1.,-4.))
    place('AccountRegister', '/Game/Building/PotionWorkbench20261015/RuntimeV2/Meshes/SM_AlchemyBook',
          counter_point(86.,10.), (27,20,4.2), 9)
    place('ChangeBowl', POTS+'Dish', counter_point(63.,-8.), (14,14,2.6), 0)
    place('CounterStool', TIMBER+'OakStool', (-72,579,0), (34,34,48), -17, True)

    # A quiet front bay overlooks the street (broken SM_Mil_Trench_Bench_Wood_01 retired across project).
    for y in BOARDS:
        authored('PerforatedDisplayBoard', 'PerforatedBoard', (BOARD_X,y,114.), 90.)
    authored('OpticsMounts', 'OpticsMounts', (BOARD_X,BOARDS[0],114.), 90.)
    authored('AccessoriesMounts', 'AccessoriesMounts', (BOARD_X,BOARDS[1],114.), 90.)
    # Each asset sits flat on its own enamelled shelf. Keep the scanned geometry at
    # its original aspect ratio, rotating elongated mounts parallel to the shelf.
    shelves = (
        ('PrismOptic','/Game/Weapons/PrismScope2XMachined/SM_PrismScope2X',0,-27,28,1.),
        ('HolographicOptic','/Game/Weapons/M4Holographic/SM_M4_Holographic',0,25,58,1.),
        ('PanoramicOptic','/Game/Weapons/M1911/SculptedMount20260913/Meshes/SM_M1911_panoramic_red_dot',0,-27,58,1.),
        ('AngledGrip','/Game/Weapons/M4AngledForegripFinal/SM_M4_AngledForegrip',1,-27,28,1.),
        ('MagazineSample','/Game/Weapons/M1911/ExtendedMagazine20260927/SM_M1911_ext_mag',1,25,28,1.),
        ('CompactMuzzle','/Game/Weapons/M4MuzzlesV1/SM_M4_titanium_brake',1,25,58,1.),
        ('OpticSample','/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_holographic',1,-27,58,1.))
    for role,path,board,dx,z,scale in shelves:
        bounds = load(path).get_bounding_box()
        span = bounds.max-bounds.min
        yaw = 90. if span.x >= span.y else 0.
        place(role,path,(BOARD_X+16.,BOARDS[board]+dx,114.+z), (span.x*scale,span.y*scale,span.z*scale), yaw)
    for y in BOARDS:
        authored('PartsDrawers', 'MerchantDrawers', (-436.,y,0.), 90., True)
    place('KeeperStockChest', CHEST, (-393,781,0), (95,50,53), -81, True)
    # Wipe-down end of the accessories counter. The shelves above start at Z=142.
    place('KeeperStockCloth', LINEN, (-432,493,90), (30,22,5), 83)
    place('CareOil', '/Game/UndergroundTunnel/Meshes/Props/SM_OilBottle01a',
          (-445,469,90),(8,8,17),18)
    # The stock shelf backs onto the rear wall. Keep transit between the counter
    # and the interactive workbench clear. Heights are the actual shelf plank tops.
    stock_height = 146.
    place('BackStockShelf', TIMBER+'OakShelf', (-236,864,0), (144,51,stock_height), 0, True)
    for x,size,path in [(-263,(47,37,31),'SM_WoodCrate01a'),(-205,(44,34,28),'SM_WoodCrate02a')]:
        place('PackedStock','/Game/UndergroundTunnel/Meshes/Props/'+path,
              (x,863,13.5*stock_height/170.),size,0)
    place('ReserveLinen',LINEN,(-266,863,65.5*stock_height/170.),(36,24,7),5)
    place('StockLedger',BOOK,(-213,864,117.5*stock_height/170.),(20,15,4),-8)

    # The landing and eastern passage lead directly to the small dining table.
    # Sleeping, washing and paperwork have distinct pieces and supporting surfaces.
    place('LoftBed',TIMBER+'TimberBed',(-330,239,LOFT),(124,210,81),180,True)
    place('FootChest',CHEST,(-330,401,LOFT),(101,48,47),3,True)
    place('BedsideStool',TIMBER+'OakStool',(-229,172,LOFT),(35,35,42),10,True)
    place('BedsideCup',POTS+'Tankard',DESK_CUP,(10,12,11),17)
    place('DiningDesk',TIMBER+'OakTable',(-55,173,LOFT),(130,73,76),-4,True)
    place('WritingStool',TIMBER+'OakStool',(-44,244,LOFT),(39,39,45),-9,True)
    place('OpenOrderBook','/Game/Building/PotionWorkbench20261015/RuntimeV2/Meshes/SM_AlchemyBook',
          (-42,173,LOFT+76),(28,20,4.5),-13)
    place('TableCup',POTS+'Tankard',(-15,161,LOFT+76),(11,12,13),13)
    place('DiningPlate',POTS+'Dish',(-91,180,LOFT+76),(22,21,3),-3)
    place('LoftWashStand',TAVERN+'KitchenStations/SM_TavernWashStand',(-326,737,LOFT),(65,108,84),-90,True)
    place('WashEwerStool',TIMBER+'OakStool',(-235,726,LOFT),(39,39,51),6,True)
    place('WashEwer',POTS+'Pitcher',PRESS_EWER,(17,21,26),-12)
    place('LoftLinenPress',TIMBER+'OakShelf',(-134,839,LOFT),(124,46,153),0,True)
    for x, height, turn in ((-166,65.5,4),(-130,65.5,-9),(-159,117.5,-3)):
        place('FoldedHouseholdLinen',LINEN,(x,840,LOFT+height*.9),(29,23,6.8),turn)
    place('SpareBowl',TAVERN+'DiningBowls/SM_TavernEatingBowl',(-98,842,LOFT+117.5*.9),(20,20,6),3)
    place('PackedAccounts',BOOK,(-104,839,LOFT+13.5*.9),(8,21,26),3)
