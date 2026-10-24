"""Read dimensions/material slots needed for apartment authoring. Writes no UE packages."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
P=ROOT.parents[1]
NAMES={
 'SM_RH2_Sofa','SM_Staff_Chair','SM_Staff_CoffeeTable','SM_MedOffice_ErgonomicChair',
 'SM_Staff_Toilet_V5','SM_Staff_WashBasin_V4','SM_Staff_BookcaseBody_V4',
 'SM_Staff_FridgeLowerDoor_V5','SM_Staff_FridgeLowerBody_V5',
 'SM_Staff_FridgeUpperDoor_V5','SM_Staff_FridgeUpperBody_V5',
 'SM_Staff_CoffeeMachine_V7','SM_Staff_Television_V4','SM_Staff_DiningTable',
 'SM_Staff_ShowerFittings_V3','SM_Staff_TowelRack_V3','SM_Staff_ElectricKettle_V6',
 'SM_Staff_LaundryBasket_V5','SM_Staff_Mirror_V3','SM_Staff_KettlePower_V6',
 'SM_Staff_BookshelfBody_V4','SM_Staff_BookshelfDrawer_V4',
 'tropicalPlant_01_01','tropicalPlant_02_01',
}
roots=['Dungeons/StaffLiving20261002','Dungeons/ReceptionHall20261006/Refine20261007',
       'Dungeons/MedicalExecutiveOffice20261010','PN_tropicalGroundPlants/Meshes']
records=[]
for root in roots:
 for f in (P/'Content'/root).rglob('*.uasset'):
  if f.stem not in NAMES:continue
  path='/Game/'+f.relative_to(P/'Content').with_suffix('').as_posix()
  a=u.load_asset(path)
  if not isinstance(a,u.StaticMesh):continue
  b=a.get_bounding_box()
  v=lambda p:[round(p.x,4),round(p.y,4),round(p.z,4)]
  records.append(dict(name=a.get_name(),path=path,min=v(b.min),max=v(b.max),
    slots=[dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None)
           for s in a.get_editor_property('static_materials')]))
(ROOT/'reuse_catalog.json').write_text(json.dumps(records,indent=2),encoding='utf8')
u.log('APARTMENT_SOURCE_CATALOG_SAVED '+str(len(records)))
