from pathlib import Path
import unreal as u,json
r=Path(__file__).resolve().parent
result={}
for path,prop in [('/Game/Weapons/M249/SK_M249_V7','materials'),('/Game/Weapons/M249/Assembly/SM_M249_magnifier','static_materials')]:
    mesh=u.load_asset(path)
    result[path]=[dict(index=i,slot=str(s.material_slot_name),imported=str(s.get_editor_property('imported_material_slot_name')),material=s.material_interface.get_path_name()) for i,s in enumerate(mesh.get_editor_property(prop))]
(r/'bindings_before.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('M249_BINDINGS_READ',flush=True)
