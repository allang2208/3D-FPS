import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/G18AttachmentRepair20260930')
assets={'holographic':'/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_holographic','panoramic_red_dot':'/Game/Weapons/M1911/SculptedMount20260913/Meshes/SM_M1911_panoramic_red_dot'}
out={}
for name,path in assets.items():
    mesh=u.load_asset(path)
    out[name]=[{'slot':str(s.material_slot_name),'imported':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]
(P/'optic_materials.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
