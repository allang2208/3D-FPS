"""Repaired 06 bakery. Local centimetres, +Y inward from the shop threshold."""
import unreal as ue


PACK = '/Game/WorldGeneration/TemperateHills/VillageBakery/Architecture'
SOURCE_MASONRY_SHELL = PACK+'/SM_Bakery_AbandonedHouseMasonry'
MASONRY_SHELL = '/Game/WorldGeneration/TemperateHills/VillageMasonry/ReliefMeshes/SM_Bakery_AbandonedHouseMasonry'
CHIMNEY = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR8/Meshes/SM_SmithLoft_Chimney_R8'
PARTS = ('HouseShell', 'TimberFrame', 'ShopJoinery', 'Roof', 'Floors', 'Stair', 'Oven', 'Flashing')
SMITH_WINDOW = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithLoft_'


def window_fittings():
    """Actor-local +X points outdoors. Unit leaves have Z-centred pivots at Y +/-74 cm."""
    from shell_geometry import WALLS
    for axis,pos,_,_,openings in WALLS:
        for a,b,sill,lintel in openings:
            if sill==0:
                continue
            along=(a+b)*.5
            z=(sill+lintel)*.5
            horizontal=(b-a-1.8)/148.
            vertical=(lintel-sill-2.4)/162.
            # Thin render over the frame is 18 cm from the wall centre. Put
            # the fixed pin outside its surface, independent of opening width.
            if axis=='X':
                yaw=-90 if pos==0 else 90
                center=(along,pos+(-23. if pos==0 else 23.),z)
            else:
                yaw=180 if pos<0 else 0
                center=(pos+(-23. if pos<0 else 23.),along,z)
            service=axis=='X' and pos==0 and sill<300
            yield dict(center=center,yaw=yaw,scale=(horizontal,horizontal,vertical),
                       frame=PACK+'/SM_Bakery_WindowPintles',
                       left=SMITH_WINDOW+'WindowLeft_R7b' if service else PACK+'/SM_Bakery_CasementLeft',
                       right=SMITH_WINDOW+'WindowRight_R7b' if service else PACK+'/SM_Bakery_CasementRight',
                       left_hinge=(0,-74.,0),right_hinge=(0,74.,0),angle=105. if service else 96.)


def build_shell(place):
    for part in PARTS:
        if part == 'HouseShell':
            from shop_house_modules import bakery_modules, place_modules
            place_modules(place,bakery_modules())
            continue
        path = PACK+'/SM_Bakery_'+part
        mesh = ue.load_asset(path)
        if not mesh:
            raise RuntimeError('Bakery architecture must be published first: '+path)
        # Vertices were authored in the doorway frame. Reproduce the identity
        # transform even though the placement API fits about the bounds bottom.
        bounds = mesh.get_bounding_box()
        middle = (bounds.min+bounds.max)*.5
        span = bounds.max-bounds.min
        place(part, path, (middle.x,middle.y,bounds.min.z), (span.x,span.y,span.z),
              solid=part != 'Flashing')
    # Preserve the donor's pivot, including its asymmetric wrought ties. The
    # oven throat and roof curb use the chimney's surveyed axis, not its bounds.
    stack = ue.load_asset(CHIMNEY)
    bounds = stack.get_bounding_box()
    center = (bounds.max+bounds.min)*.5
    span = bounds.max-bounds.min
    scale = (.65,.65,.76)
    place('Chimney',CHIMNEY,(-245+center.x*scale[0],811+center.y*scale[1],bounds.min.z*scale[2]),
          (span.x*scale[0],span.y*scale[1],span.z*scale[2]),solid=True)


def install_bakery_masonry(actors):
    from install_shop_house_modules import replace_modules
    from shop_house_modules import bakery_modules
    return replace_modules(actors,'VillageBakery',bakery_modules(),
                           {PACK+'/SM_Bakery_HouseShell',SOURCE_MASONRY_SHELL,MASONRY_SHELL})
