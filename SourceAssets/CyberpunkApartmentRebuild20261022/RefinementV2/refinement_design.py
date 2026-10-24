"""Apartment authoring contract. Metres in Blender, +Y inland, -Y toward the bay.

Room boundaries retain the imported plan at 125%. Furniture uses real dimensions.
Only this revision's files and L_CyberpunkApartment are publication targets.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV2'
MAP='/Game/GameMaps/L_CyberpunkApartment'
HEIGHT=3.6875
ROOMS={
 'Master':(.12,.12,3.84,5.40), 'Living':(3.96,.12,11.28,5.40),
 'Bed2':(11.40,.12,15.88,5.40), 'Bed3':(11.40,5.52,15.88,10.88),
 'Kitchen':(4.80,6.84,8.64,10.88), 'Foyer':(8.76,6.84,11.28,10.88),
 'Corridor':(.12,5.52,11.28,6.72), 'Bath2':(.12,8.20,2.72,10.88),
 'Bath1':(2.84,8.20,4.68,10.88), 'Laundry':(.12,6.84,2.72,8.08),
 'Service':(2.84,6.84,4.68,8.08), 'Balcony':(3.98,-2.80,11.30,-.02),
}
ROOMS={k:tuple(v*1.25 for v in b) for k,b in ROOMS.items()}
STAFF='/Game/Dungeons/StaffLiving20261002'
RH='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/'
SUB='/Game/SubstrateMaterials/Materials/'
REUSE={
 'NearTower':'/Game/Props/CyberpunkApartmentPlayable20261021/CyberpunkApartmentPlayable/StaticMeshes/CITY_our_tower',
 'Sofa':RH+'SM_RH2_Sofa','Chair':RH+'SM_Staff_Chair',
 'CoffeeTable':RH+'SM_Staff_CoffeeTable',
 'DiningTable':STAFF+'/Meshes/SM_Staff_DiningTable',
 'OfficeChair':'/Game/Dungeons/MedicalExecutiveOffice20261010/Meshes/SM_MedOffice_ErgonomicChair',
 'Bookcase':STAFF+'/ScenePolishV4/Meshes/SM_Staff_BookcaseBody_V4',
 'TV':STAFF+'/ScenePolishV4/Meshes/SM_Staff_Television_V4',
 'Basin':STAFF+'/ScenePolishV4/Meshes/SM_Staff_WashBasin_V4',
 'Toilet':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_Toilet_V5',
 'Mirror':STAFF+'/RefinementV3/Meshes/SM_Staff_Mirror_V3',
 'Shower':STAFF+'/RefinementV3/Meshes/SM_Staff_ShowerFittings_V3',
 'TowelRack':STAFF+'/RefinementV3/Meshes/SM_Staff_TowelRack_V3',
 'LaundryBasket':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_LaundryBasket_V5',
 'FridgeLowerBody':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_FridgeLowerBody_V5',
 'FridgeUpperBody':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_FridgeUpperBody_V5',
 'FridgeLowerDoor':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_FridgeLowerDoor_V5',
 'FridgeUpperDoor':STAFF+'/RoomDetailsV5/Meshes/SM_Staff_FridgeUpperDoor_V5',
 'CoffeeMachine':STAFF+'/CoffeePolishV7/Meshes/SM_Staff_CoffeeMachine_V7',
 'Kettle':STAFF+'/WallInsetV6/Meshes/SM_Staff_ElectricKettle_V6',
 'Plant':'/Game/PN_tropicalGroundPlants/Meshes/tropicalPlant_01_01',
 'Plant2':'/Game/PN_tropicalGroundPlants/Meshes/tropicalPlant_02_01',
}
# Shared finishes are referenced, never duplicated or edited.
MATERIALS={
 'Oak':SUB+'08_WoodVeneer/1_Veneers/MI_WoodVeneer_RawOak',
 'Steel':SUB+'03_Metals/2_Brushed/MI_BrushedSteel_Horizontal_OPBR',
 'Dark':SUB+'01_Paints/OpenPBR/MI_Paint_Black_SmallGrain_OPBR',
 'Rubber':SUB+'07_Rubbers/1_Base/MI_Rubber_Weatherstrip_OPBR',
 'Fabric':SUB+'02_Upholstery/4_Fabric/MI_Fabric_Charcoal_OPBR',
 'Linen':SUB+'02_Upholstery/4_Fabric/MI_Fabric_Textile_Gray',
 'Carpet':SUB+'02_Upholstery/5_Carpet/MI_Carpet_Gray_OPBR',
 'Stone':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Stone',
 'Floor':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Floor',
 'Ceramic':STAFF+'/Materials/M_Staff_Ceramic',
 'Glass':'/Game/Props/CyberpunkApartmentPlayable20261021/CyberpunkApartmentPlayable/Materials/glass_window',
 'Screen':STAFF+'/Materials/M_Staff_Screen',
}
# Restrained residential palette: graphite metal, warm oak, muted teal, pale plaster.
FINISHES={
 'Wall':([.21,.225,.24],.83,0,0), 'Ceiling':([.33,.345,.36],.86,0,0),
 'Teal':([.014,.017,.021],.52,.18,0), 'Brass':([.26,.28,.31],.36,.78,0),
 'SmokedWood':([.16,.175,.19],.64,0,0), 'CabinetInside':([.045,.05,.06],.72,.12,0),
 'Grout':([.025,.030,.031],.95,0,0), 'Soil':([.020,.014,.009],1,0,0),
 'Paper':([.61,.60,.52],.91,0,0), 'Cyan':([.05,.64,.85],.3,0,3),
 'Warm':([1,.67,.31],.34,0,3), 'Amber':([1,.22,.035],.4,0,2),
}
MATERIALS.update({k:BASE+'/Materials/M_AP_'+k for k in FINISHES})
MATERIALS['Oak']=MATERIALS['SmokedWood']
# Doors have local X thickness / Y width, with native unit actor scale.
DOORS=[
 dict(name='Entry',p=[12.4,13.525,0],yaw=90,width=1.20,height=2.65),
 dict(name='Master',p=[2.4625,6.65,0],yaw=90,width=1.025,height=2.525),
 dict(name='Bed2',p=[14.35,5.6875,0],yaw=0,width=1.025,height=2.525),
 dict(name='Bed3',p=[14.35,10.0375,0],yaw=0,width=1.025,height=2.525),
 dict(name='Bath1',p=[4.625,10.,0],yaw=90,width=1.05,height=2.50),
 dict(name='Bath2',p=[2.025,10.,0],yaw=90,width=1.10,height=2.50),
 dict(name='Balcony',p=[9.4375,.2125,0],yaw=90,width=1.2625,height=2.90),
]
