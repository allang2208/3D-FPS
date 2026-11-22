"""Shop floor and baker's lodging. Local cm; the public door is at (0, 0)."""
import math

HILLS = '/Game/WorldGeneration/TemperateHills/'
TAVERN = '/Game/WorldGeneration/VillageTavern/'
TABLEWARE = TAVERN+'StonewareDetail/SM_Tavern'
TIMBER = HILLS+'VillageBlacksmith/ArtPassR2/Meshes/SM_Village'
BAKERY = HILLS+'VillageBakery/Furnishings/SM_Bakery'
QUX = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/'
LINEN = QUX+'FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
BOOK = QUX+'Book_634f4e59/Meshes/SM_Book_634f4e59'
SIEVE = HILLS+'VillageHerbalist/Props/SM_HerbalistGatheringSieve'
CHEST = '/Game/Props/GamedevTreasureChestV3_20261004/Meshes/SM_TreasureChest_Closed'
LANTERN = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
COUNTER_X, COUNTER_Y = -39, 565
COUNTER_YAW = -90
COUNTER_HEIGHT = 98


def build_furnishings(place):
    # The donor counter's working top fills the long axis and its foot rail
    # projects forward; the front/centre strip is reserved for serving a customer.
    place('SalesCounter', TAVERN+'Furniture/SM_TavernCounter', (COUNTER_X,COUNTER_Y,0),
          (86,252,COUNTER_HEIGHT), COUNTER_YAW, True)
    place('KneadingBench', TAVERN+'KitchenStations/SM_TavernPrepBench',
          (-318,468,0), (75,157,101), 0, True)
    place('WashStand', TAVERN+'KitchenStations/SM_TavernWashStand',
          (55,814,0), (73,113,92), -90, True)
    place('FlourBin', TAVERN+'Service/SM_TavernAleCask', (-48,823,0), (53,53,69), -13, True)
    place('SmallFlourBin', TAVERN+'Service/SM_TavernAleCask', (-53,762,0), (41,41,53), 24, True)
    place('SplitFuel', HILLS+'VillageCarpenter/Props/SM_CarpenterLogStack',
          (-29,867,0), (89,29,38), 0, True)
    # The mounting cleat enters the west timber; both hooks bear the baker's
    # peel above the prep bench while its lip and handle clear the benchtop.
    place('PeelAndWallHooks', BAKERY+'PeelHanger', (-360,459,116), (14,42,164), 0)
    place('CoolingShelf', TIMBER+'OakShelf', (-335,316,0), (142,48,158), 90, True)

    def board(x, y, surface, heading, pieces, scale=1.):
        # The 7 cm bound includes the finger holes. The eating surface is
        # 4 cm above the runners, on top of 13 separate planed cooling slats.
        place('SlattedBoard', BAKERY+'CoolingBoard', (x,y,surface),
              (66.45*scale,36.5*scale,7*scale),heading)
        c,s = math.cos(math.radians(heading)), math.sin(math.radians(heading))
        for kind,dx,dy,length,twist in pieces:
            center = (x+scale*(c*dx-s*dy), y+scale*(s*dx+c*dy), surface+4.*scale)
            # These are the two existing Megascans food meshes turned onto
            # their natural bases. Retain the proportions of each original.
            if kind == 'round':
                place('RoundLoaf',BAKERY+'CounterBread',center,(length,length*.623,length*.399),heading+twist)
            else:
                place('LongLoaf',BAKERY+'CounterBaguette',center,(length,length*.190,length*.145),heading+twist)

    def on_counter(dx,dy):
        return COUNTER_X+dx, COUNTER_Y+dy, COUNTER_HEIGHT

    board(*on_counter(-76,3),-4, [('round',-15,-5,20,-8),('round',6,3,18,35),('round',19,-7,15,-19)])
    board(*on_counter(4,1),4, [('long',-7,-6,39,3),('long',5,5,42,-7)])
    place('WrappingLinen', LINEN, on_counter(75,8), (27,18,5), -14)
    place('ChangeBowl', TABLEWARE+'Dish', on_counter(108,-12), (17,17,2.7), 9)

    # A second batch cools by the prep bench, above the shelf's housed bearers.
    # The rack is 158 cm against a 170 cm original. Its plank tops are 13.5,
    # 65.5 and 117.5 cm on the original. Keep the near end of one shelf empty.
    shelf_scale = 158./170.
    board(-335,292,117.5*shelf_scale,90,
          [('long',-6,-7,34,-1),('long',1,2,37,-5),('long',6,11,32,6)],.92)
    board(-335,341,65.5*shelf_scale,89,
          [('round',-11,0,19,14),('round',11,-4,17,-23)],.78)
    place('CleanShelfLinen', LINEN, (-334,277,65.5*shelf_scale), (29,20,5.6), 93)
    place('FlourSieve', SIEVE, (-334,347,13.5*shelf_scale), (30,28,7), 69)

    # Small parties share the west table; a pair can sit by the east windows.
    # The tables and stools use the taproom's working heights and oak finishes.
    for x,y,yaw in [(-215,143,12),(216,131,-17)]:
        place('WindowTable', TAVERN+'Furniture/SM_TavernTable', (x,y,0), (116,116,76), yaw, True)
    for x,y,yaw in [(-292,151,-7),(-200,221,75),(-164,83,-43),(146,165,148),(282,89,-28)]:
        place('DiningStool', TAVERN+'Furniture/SM_TavernStool', (x,y,0), (40,40,46), yaw, True)
    place('ServiceJug', TABLEWARE+'Pitcher', (-216,139,76), (16,19,24), 34)
    place('WestCup', TABLEWARE+'Tankard', (-244,151,76), (11,13,11), 154)
    place('WestCup', TABLEWARE+'Tankard', (-205,173,76), (11,13,11), 72)
    place('BreadDish', TABLEWARE+'Dish', (-190,121,76), (25,25,3), -13)
    place('TableLoaf', BAKERY+'CounterBread', (-190,121,77.25), (17,10.6,6.8), -25)
    board(221,139,76,-12,[('round',-12,0,18,21),('long',11,0,25,84)],.74)
    place('EastCup', TABLEWARE+'Tankard', (192,151,76), (11,13,11), 139)
    place('EastCup', TABLEWARE+'Tankard', (244,110,76), (11,13,11), -35)

    loft = 315
    place('BakersBed', TIMBER+'TimberBed', (-236,248,loft), (110,210,80), 0, True)
    place('LinenChest', CHEST, (-226,422,loft), (87,51,48), 5, True)
    place('RestTable', TIMBER+'OakTable', (17,116,loft), (117,68,75), 0, True)
    place('RestStool', TIMBER+'OakStool', (22,188,loft), (37,37,43), -19, True)
    place('WaterPitcher', TABLEWARE+'Pitcher', (-21,110,loft+75), (19,21,28), -12)
    place('DrinkingCup', TABLEWARE+'Tankard', (0,119,loft+75), (12,14,12), 27)
    place('Lamp', LANTERN, (58,104,loft+75), (15,15,28), 30)
    place('LoftWashStand', TAVERN+'KitchenStations/SM_TavernWashStand',
          (-12,822,loft), (66,91,82), -90, True)
    place('LodgingShelf', TIMBER+'OakShelf', (-331,101,loft), (101,38,136), 90, True)
    place('CleanLinen', LINEN, (-331,108,loft+65.5*.8), (37,26,8), 84)
    place('SpareCrockery', TAVERN+'DiningBowls/SM_TavernEatingBowl',
          (-331,94,loft+13.5*.8), (24,23,8), 76)
    # The bound volume is stored upright between a decanter and a shelf post.
    place('Accounts', BOOK, (-329,64,loft+117.5*.8), (5.2,17,22), 2)
    place('SmallEwer', TABLEWARE+'Pitcher', (-330,77,loft+117.5*.8), (13,15,18), -31)
