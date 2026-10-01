import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/G18AttachmentRepair20260930')
root='/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_'
out={}
for key in ('ext_mag','holographic','panoramic_red_dot'):
    m=u.load_asset(root+key)
    out[key]={'path':m.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in m.static_materials},'sockets':{n:list(m.find_socket(n).relative_location.to_tuple()) for n in ('AimCenter','Muzzle') if m.find_socket(n)}}
(O/'live_bindings.json').write_text(json.dumps(out,indent=2))
print('G18_REPAIR_BINDINGS_WRITTEN')
