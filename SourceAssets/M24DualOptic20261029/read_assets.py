import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x')
result={'mesh':mesh.get_path_name(),'sockets':{},'slots':[str(s.material_slot_name) for s in mesh.static_materials]}
for name in ('SightRear','SightFront','SightUp','TopSightRear','TopSightFront','TopSightUp'):
    s=mesh.find_socket(name)
    if s:
        p=s.relative_location;result['sockets'][name]=[p.x,p.y,p.z]
(O/'inputs.json').write_text(json.dumps(result,indent=2));print('M24_DUAL_OPTIC_INPUTS',json.dumps(result),flush=True)
