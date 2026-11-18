"""Shared centimetre layout for the rebuilt two-storey blacksmith; no engine dependency."""
import math
AREA_FACTOR=1.25
XY_FACTOR=math.sqrt(AREA_FACTOR)
SOURCE_SCALE=1.2
LOFT_Z=360.0
HALF=390.0
OPENING=(-352.,-90.,-101.,312.) # xmin,xmax,ymin,ymax; the stair exits directly onto the front landing
STATION=(120.,40.,6.)
HEARTH=(200.,300.,0.)
CHIMNEY=(200.,500.,0.)
BED=(245.,50.,360.)
STAIR={'width':110.,'first_x':-285.,'second_x':-157.,'start_y':-100.,'turn_y':180.,'landing_end_y':300.,'rise':18.,'tread':28.,'steps_per_flight':10}
ASSET_ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3'
FURNITURE='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_Village'
DESCRIPTION={
 'revision':3,'footprint_area_multiplier':AREA_FACTOR,'horizontal_dimension_multiplier':XY_FACTOR,
 'original_nominal_floor_cm':[720,720],'nominal_floor_cm':[720*XY_FACTOR]*2,
 'ground_floor':'front and west-front open workshop, structural posts and beams, existing anvil/quench station, rear hearth',
 'upper_floor':'stair opening, guarded landing, blacksmith bed, storage and reused Normandy window assemblies',
 'floor_height_cm':LOFT_Z,'stair':STAIR,'opening_cm':OPENING,
 'station_cm':STATION,'hearth_cm':HEARTH,'chimney_cm':CHIMNEY,'bed_cm':BED,
 'chimney':'MasonryR5: 146 cm bonded house fieldstone shaft outside rear eave, hollow flue and extended side duct',
 'default_state':'ruined','runtime_cloth':False,'new_active_fire_or_smoke_system':False}
