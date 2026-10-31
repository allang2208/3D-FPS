"""Frozen Kitchen Detail V1 contract; Blender metres, +Z up, front is -Y.
The apartment's latest saved layout supplies the anchors, not a guessed rebuild.
Interactive storage is generated as separate body/front meshes; doors hinge left.
"""
from pathlib import Path
R = Path(__file__).resolve().parent
PROJECT = R.parents[2]
ROOT = R.parent
SOURCE = ROOT / 'CyberpunkApartment_Rebuild.blend'
ROOM = dict(xmin=6.0, ymin=8.55, xmax=10.8, ymax=13.60, ceiling=3.6875)
COUNTER = dict(x=8.9, y=13.12, width=3.60, depth=.65, top=.947)
FRIDGE = dict(x=6.52, y=13.10, width=.71, depth=.68)
BASE_X = [7.4, 8.0, 8.6, 9.2, 9.8, 10.4]
UPPER_X = [7.4, 8.0, 8.6, 9.2, 10.4]
BASE_MODULES = [
    dict(key='Base_0', x=7.4, sink=True), dict(key='Base_1', x=8.0, sink=True),
    dict(key='Base_2', x=8.6), dict(key='Base_3', x=9.2),
    dict(key='Base_4', x=9.8), dict(key='Base_5', x=10.4),
]
UPPER_MODULES = [dict(key='Upper_'+str(i), x=x) for i, x in enumerate(UPPER_X)]
REUSE = dict(
    coffee=PROJECT / 'SourceAssets/DungeonStaffLiving20261002/CoffeePolishV7/Authored/StaffLivingTheme_CoffeePolishV7.blend',
    kettle=PROJECT / 'SourceAssets/DungeonStaffLiving20261002/WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend',
    dining=PROJECT / 'SourceAssets/DungeonStaffLiving20261002/Authored/StaffLivingTheme.blend',
)
REUSE_OBJECTS = dict(coffee='SM_Staff_CoffeeMachine_V7', kettle='SM_Staff_ElectricKettle_V6',
                     dining='SM_Staff_DiningTable', chair='SM_Staff_Chair')
COLLECTION = 'KITCHEN_DETAIL_20261024'
PREFIX = 'KIT_'
MATERIAL_PREFIX = 'KP_'
PBR = dict(
    # Neutral apartment black/grey hierarchy. Textures are already tinted;
    # these multipliers only grade the material once, never double green tint.
    Enamel=dict(period=.38, strength=.30, tint=(1.,1.,1.), roughness=.42, metal=.12),
    Stone=dict(period=.55, strength=.28, tint=(1.,1.,1.), roughness=.46, metal=0),
    Tile=dict(period=.60, strength=.42, tint=(1.,1.,1.), roughness=.34, metal=0),
    Steel=dict(period=.36, strength=.30, tint=(.90,.92,.94), roughness=.32, metal=1),
    Wood=dict(period=.80, strength=.38, tint=(1.,1.,1.), roughness=.48, metal=0),
    Linen=dict(period=.22, strength=.42, tint=(1.,1.,1.), roughness=.88, metal=0),
    Porcelain=dict(period=.25, strength=.16, tint=(1.,1.,1.), roughness=.26, metal=0),
)
# This is a coordinate-calibrated *kitchen source*, not a substitute apartment.
# Source geometry is local to its component; placements are absolute apartment metres.
PLACEMENTS = dict(
    Counter=(8.9,13.12,0),
    BackSplash=(8.9,13.474,1.225),
    FridgeLowerBody=(6.52,13.10,0),
    FridgeLowerDoor=(0,0,0),
    FridgeUpperBody=(6.52,13.10,0),
    FridgeUpperDoor=(0,0,0),
    Coffee=(10.33,13.06,.947),
    Kettle=(8.73,13.16,.947),
    Sink=(7.83,13.12,.947),
    Cooking=(9.82,13.12,.947),
    OvenFront=(9.82,13.12,.947),
    # Origin is the tile front; rail and brackets extend toward -Y.
    UtilityRail=(8.30,13.465,1.650),
    Prep=(9.13,13.025,.947),
    Dishes=(8.16,12.975,.947),
    # Local tabletop authoring datum; installer uses the measured formal table.
    DiningDressing=(0,0,.7825),
)
INTERFACES = dict(
    counter_support_top_m=.947, module_gap_m=.016,
    cabinet_body_front_overlap_m=.006, door_hinge='left; mesh origin at hinge',
    fridge_clearance_m=.10, backsplash_offset_from_wall_m=.006,
    fridge_trim_front_y_m=-.0365, fridge_native_face_y_m=-.0325,
    fridge_trim_surface_gap_m=.001, fridge_handle_keepout_x_m=(.585,.670),
    dining_support_top_m=.7825, plate_section='closed outer-foot-rim-inner-floor',
    plate_support_z_m=.024, plate_side_support_z_m=.104, mug_shelf_z_m=.018,
    support_contact_tolerance_mm=.05, separate_prop_clearance_mm=2.0,
    vessel_support_gap_mm=.02, rack_foot_support_gap_mm=.02,
    # Only structural attachment volumes, never arbitrary overlapping decorations.
    cabinet_hinge_overlap_mm=1.0, handle_standoff_overlap_mm=2.0,
    refrigerator_body_rail_overlap_mm=3.0, rack_post_seat_overlap_mm=1.5, plate_foot_ring_contact_mm=.25,
    utensil_in_block_insertion_mm=12.0, herb_stem_in_soil_mm=6.0,
    fixed_decor_collision='none; does not alter room/player collision',
    assembly_allow_list=['fastener-to-plate', 'handle-to-standoff', 'basin-to-counter',
                         'coffee-to-tray', 'kettle-to-base', 'props-to-surface',
                         'plate-foot-to-rack', 'knife-in-block', 'soil-in-pot'],
)
INTEGRATION = dict(
    asset_base='/Game/Props/CyberpunkApartmentKitchen20261024',
    map='/Game/GameMaps/L_CyberpunkApartment',
    preserve=['bedroom','bay','atmosphere','clock','portal_ids','door_ids','unrelated_materials'],
    modify=['kitchen fixtures','targeted kitchen material overrides','fixed decor'],
    background_first=True, no_new_UE_process_if_open=True,
)
# Counter items are support anchors, not loose physics props.
# The authoritative UE apartment is not at the Blender room's world origin.
# Measured AP_Kitchen_Run=(1335,-1985,0) cm versus COUNTER=(8.9,13.12,0) m.
# All 12 native kitchen/fridge containers agree with this single translation.
UE_KITCHEN_ORIGIN_CM = (445., -673., 0.)
def source_to_ue_cm(position):
    x,y,z=position
    return (x*100+UE_KITCHEN_ORIGIN_CM[0],
            -y*100+UE_KITCHEN_ORIGIN_CM[1],
            z*100+UE_KITCHEN_ORIGIN_CM[2])
SOURCE_CONTAINER_ANCHORS = dict(
    Fridge_Lower=(6.52,13.10,0),Fridge_Upper=(6.52,13.10,0),
    Kitchen_Sink_0=(7.4,13.12,0),Kitchen_Sink_1=(8.,13.12,0),
    Kitchen_Base_2=(8.6,13.12,0),Kitchen_Base_3=(9.2,13.12,0),
    Kitchen_Base_4=(9.8,13.12,0),Kitchen_Base_5=(10.4,13.12,0),
    Kitchen_Upper_0=(7.4,13.31,1.66),Kitchen_Upper_1=(8.,13.31,1.66),
    Kitchen_Upper_2=(8.6,13.31,1.66),Kitchen_Upper_3=(9.2,13.31,1.66),
    Kitchen_Upper_5=(10.4,13.31,1.66))
COFFEE = (10.33, 13.06, .947)
KETTLE = (8.73, 13.16, .947)
DINING = (8.35, 10.28, 0)
CHAIRS = [(7.85,9.47,0,180),(8.85,9.47,0,180),(7.85,11.09,0,0),(8.85,11.09,0,0)]
CAMERAS = [
    dict(name='Kitchen_Hero', position=(9.72,8.84,2.08), target=(8.43,13.04,1.25), lens=22),
    dict(name='Counter_Detail', position=(9.48,11.76,1.70), target=(9.16,13.10,1.10), lens=38),
    dict(name='Sink_Detail', position=(7.64,11.93,1.79), target=(7.85,13.12,1.13), lens=39),
]
PRESERVE = ['apartment room shell', 'other rooms', 'bay scenery', 'existing storage IDs',
            'apartment ceiling fixture direction', 'existing UE gameplay contracts']
