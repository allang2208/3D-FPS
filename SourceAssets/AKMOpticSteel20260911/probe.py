import unreal as u,json
from pathlib import Path
paths={'panoramic_red_dot':'/Game/Weapons/PanoramicRedDot/SM_PanoramicRedDot','prism_scope_2x':'/Game/Weapons/PrismScope2XMachined/SM_PrismScope2X','lpvo_1_6x':'/Game/Weapons/LPVO1to6X/SM_LPVO1to6X','ring':'/Game/Weapons/LPVO1to6X/SM_LPVORing','holographic':'/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/SM_AKM_optic'}
r={}
for k,p in paths.items():
 m=u.load_asset(p);r[k]={'asset':p,'triangles':m.get_num_triangles(0),'materials':[{ 'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in m.static_materials]}
Path(__file__).with_name('slots.json').write_text(json.dumps(r,indent=2));u.log('OPTIC_SLOTS_PASS')
