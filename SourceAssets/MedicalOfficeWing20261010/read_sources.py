"""Read existing art bounds/materials for placement authoring. No map changes."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
paths=set()
for folder in ('HospitalCorridor/Meshes/Objects','Dungeons/StaffLiving20261002/Meshes',
               'Dungeons/IsolationWard20260929/Props','Dungeons/HospitalDoctorOffice20261003/Meshes',
               'Dungeons/StationWorkshop20261003/RefineV2/Meshes',
               'Dungeons/StaffLiving20261002/ScenePolishV4/Meshes',
               'Dungeons/HospitalContainers20261003/Meshes'):
    paths.update('/Game/'+str(p.relative_to(PROJECT/'Content').with_suffix('')).replace('\\','/')
                 for p in (PROJECT/'Content'/folder).glob('*.uasset'))
paths.add('/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_CoffeeMachine_V5')
paths.add('/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_ElectricKettle_V5')
paths.add('/Game/Dungeons/IsolationWard20260929/Meshes/SM_Ward_DoorPaneV5')
paths.add('/Game/Dungeons/IsolationWard20260929/Meshes/SM_Ward_GlassDoorMetalV5')
report={}
for path in sorted(paths):
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):continue
    b=mesh.get_bounding_box()
    report[path]=dict(min=[b.min.x,b.min.y,b.min.z],max=[b.max.x,b.max.y,b.max.z],
        materials=[dict(slot=str(s.material_slot_name),path=s.material_interface.get_path_name().split('.')[0] if s.material_interface else '')
                   for s in mesh.get_editor_property('static_materials')])
(ROOT/'Config/reused-art.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('MEDICAL_OFFICE_EXISTING_ART_READ',len(report),flush=True)
